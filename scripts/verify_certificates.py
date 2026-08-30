"""
verify_certificates.py — End-to-end certificate verifier (primal + dual).

The primal half (run_validate_adaptive.py) already proves every reported
incumbent is SRPS-feasible and that its objective recomputes. This script adds
the *dual* half the certified primal--dual claim rests on: it independently
reconstructs the Lagrangian upper bound and checks that it dominates the
incumbent, so each reported certified gap is reproducible from committed
artifacts rather than trusted from the run log.

For every study instance it:
  1. PRIMAL  — loads the incumbent PKL and runs the 7 feasibility checks
               (reused from validators.validate) + objective recompute.
  2. DUAL    — reconstructs L(mu):
                 * stored mode    — if results/beta_certificates/<inst>.pkl exists,
                   load the saved multipliers mu and evaluate L(mu) exactly
                   (core.evaluate_lagrangian). This checks THE certificate the
                   run reported.
                 * rederive mode  — otherwise run sub-gradient descent fresh
                   (lower_bound = incumbent) to obtain an *independent* valid
                   bound. Weaker (not the same mu) but still certifies obj <= UB.
  3. CHECK   — asserts incumbent_obj <= L(mu) (+tol); recomputes the certified
               gap and diffs it against final_cert_gap_pct in adaptive_master.csv.

Emits results/verification_report.csv (one row per instance, with pass flags)
and exits non-zero if any certificate fails to reproduce.

Usage:
    python scripts/verify_certificates.py                       # all study instances, rederive
    python scripts/verify_certificates.py --limit 5             # smoke test (first 5)
    python scripts/verify_certificates.py --instances results/hard_tail_70.csv
    python scripts/verify_certificates.py --max-iter 200 --max-time 60
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from adapters.ops_adapter import OPSInstance, OPSSolution
from core.ops_bounds import evaluate_lagrangian, lagrangian_bound
from validators.validate_ops_solution import validate as primal_validate

BENCH          = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
INCUMBENTS_DIR = os.path.join("results", "beta_incumbents")
CERTS_DIR      = os.path.join("results", "beta_certificates")
MASTER_CSV     = os.path.join("results", "adaptive_master.csv")
REPORT_CSV     = os.path.join("results", "verification_report.csv")
STUDY_FAMILIES = {"B", "C", "D", "EB", "EC", "ED"}

TOL_BOUND = 1e-6   # incumbent must not exceed L(mu) by more than this
TOL_GAP   = 0.01   # recomputed cert gap may differ from CSV by this many pp


def _instance_path(family: str, label: str) -> str:
    return os.path.join(BENCH, family, "instances", label + ".txt")


def _load_incumbent(label: str, inst: OPSInstance):
    path = os.path.join(INCUMBENTS_DIR, label + ".pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = pickle.load(f)
    sol = OPSSolution(inst)
    sol.routes   = [list(r) for r in data["routes"]]
    sol.selected = set(data["selected"])
    return sol


def _load_certificate(label: str):
    """Return the saved certificate dict with mu re-keyed to (j, k) int tuples."""
    path = os.path.join(CERTS_DIR, label + ".pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        cert = pickle.load(f)
    mu = cert.get("best_mu")
    if mu is not None:
        cert["best_mu"] = {
            tuple(int(x) for x in key.split(",")): v for key, v in mu.items()
        }
    return cert


def _cert_gap(ub: float, obj: float) -> float:
    return (ub - obj) / ub * 100.0 if ub > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=MASTER_CSV,
                    help="Canonical results CSV to cross-check (default adaptive_master.csv).")
    ap.add_argument("--instances", default=None,
                    help="Optional CSV with an 'instance' column to restrict the set.")
    ap.add_argument("--limit", type=int, default=None, help="Verify only the first N (smoke test).")
    ap.add_argument("--max-iter", type=int, default=300, help="Sub-gradient iters in rederive mode.")
    ap.add_argument("--max-time", type=float, default=60.0, help="Per-instance time cap in rederive mode.")
    ap.add_argument("--rederive-only", action="store_true",
                    help="Ignore stored certificates and always re-derive the bound "
                         "independently. Use this to avoid contamination when a "
                         "separate run is concurrently writing beta_certificates/ "
                         "(stored mu from a different run would mismatch the CSV gap).")
    ap.add_argument("--out", default=REPORT_CSV, help="Verification report CSV path.")
    args = ap.parse_args()

    # Canonical CSV: family, reported obj, ub, gap per instance
    ref = {}
    with open(args.csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fam = r.get("family", "").strip()
            if fam not in STUDY_FAMILIES:
                continue
            inst_name = r["instance"].strip()
            def _num(key):
                v = r.get(key, "").strip()
                try:
                    return float(v)
                except ValueError:
                    return None
            ref[inst_name] = {
                "family":  fam,
                "obj":     _num("alns_obj"),
                "ub":      _num("best_ub"),
                "gap_pct": _num("final_cert_gap_pct"),
            }

    targets = sorted(ref)
    if args.instances and os.path.exists(args.instances):
        with open(args.instances, encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            col = "instance" if "instance" in rdr.fieldnames else "instance_id"
            keep = {r[col].strip() for r in rdr}
        targets = [t for t in targets if t in keep]
    if args.limit is not None:
        targets = targets[:args.limit]

    print("=" * 78)
    print("Certificate verification — primal feasibility + dual bound reconstruction")
    print(f"Instances : {len(targets)}   |   cross-check: {args.csv}")
    print(f"Certs dir : {CERTS_DIR}  ({'present' if os.path.isdir(CERTS_DIR) else 'ABSENT → rederive mode'})")
    print("=" * 78)

    fields = [
        "instance", "family", "mode",
        "csv_obj", "primal_obj", "csv_obj_match", "csv_ub", "recomputed_ub", "lagrangian_value",
        "csv_gap_pct", "recomputed_gap_pct",
        "pass_primal", "pass_bound", "pass_ub_match", "pass_gap", "pass_all", "note",
    ]
    rows = []
    n_pass = n_fail = 0
    n_stored = n_rederived = 0
    t0 = time.time()

    for i, label in enumerate(targets, 1):
        meta = ref[label]
        family = meta["family"]
        ipath = _instance_path(family, label)
        row = {k: "" for k in fields}
        row.update({"instance": label, "family": family,
                    "csv_obj": meta["obj"], "csv_ub": meta["ub"], "csv_gap_pct": meta["gap_pct"]})

        if not os.path.exists(ipath):
            row.update({"mode": "skip", "pass_all": False, "note": "instance file not found"})
            rows.append(row); n_fail += 1
            print(f"  [{i}/{len(targets)}] SKIP {label}: instance file missing")
            continue

        try:
            inst = OPSInstance.from_instance_file(ipath)
            sol = _load_incumbent(label, inst)
            if sol is None:
                row.update({"mode": "skip", "pass_all": False, "note": "incumbent PKL missing"})
                rows.append(row); n_fail += 1
                print(f"  [{i}/{len(targets)}] SKIP {label}: incumbent PKL missing")
                continue

            primal_obj = sol.objective()
            row["primal_obj"] = primal_obj

            # ---- PRIMAL: 7 feasibility checks + self-obj recompute -----------
            pass_primal = True
            try:
                primal_validate(inst, sol, claimed_obj=primal_obj)
            except AssertionError as e:
                pass_primal = False
                row["note"] = f"primal: {e}"
            row["pass_primal"] = pass_primal
            # CSV-objective provenance (informational, directional): an on-disk
            # incumbent that *exceeds* the cited value is an improvement, not a
            # failure; only a *worse* incumbent is a genuine provenance concern.
            if meta["obj"] is not None:
                d = primal_obj - meta["obj"]
                row["csv_obj_match"] = ("match" if abs(d) <= 0.5
                                        else ("better" if d > 0 else "worse"))
            else:
                row["csv_obj_match"] = "na"

            # ---- DUAL: reconstruct L(mu) -------------------------------------
            cert = None if args.rederive_only else _load_certificate(label)
            if cert is not None and cert.get("best_mu"):
                mode = "stored"; n_stored += 1
                ev = evaluate_lagrangian(inst, cert["best_mu"])
                lag_val = ev["lagrangian_value"]
                recomputed_ub = ev["upper_bound"]
                # stored mu should reproduce the reported UB
                cert_ub = cert.get("reported_ub")
                pass_ub_match = (cert_ub is None) or abs(recomputed_ub - cert_ub) <= 1.0
                row["pass_ub_match"] = pass_ub_match
            else:
                mode = "rederive"; n_rederived += 1
                lag = lagrangian_bound(inst, max_iter=args.max_iter,
                                       lower_bound=primal_obj, max_time=args.max_time)
                lag_val = lag["upper_bound"]
                recomputed_ub = math.floor(lag_val)
                row["pass_ub_match"] = ""   # not applicable (independent derivation)
            row["mode"] = mode
            row["lagrangian_value"] = round(lag_val, 4)
            row["recomputed_ub"] = recomputed_ub

            # ---- CHECK: bound dominates incumbent, gap reproduces ------------
            pass_bound = primal_obj <= lag_val + TOL_BOUND
            row["pass_bound"] = pass_bound

            recomputed_gap = _cert_gap(recomputed_ub, primal_obj)
            row["recomputed_gap_pct"] = round(recomputed_gap, 4)
            if mode == "stored" and meta["gap_pct"] is not None:
                pass_gap = abs(recomputed_gap - meta["gap_pct"]) <= TOL_GAP
            else:
                pass_gap = ""   # informational only in rederive mode
            row["pass_gap"] = pass_gap

            pass_all = bool(pass_primal and pass_bound
                            and (row["pass_ub_match"] in (True, ""))
                            and (pass_gap in (True, "")))
            row["pass_all"] = pass_all
            rows.append(row)

            if pass_all:
                n_pass += 1
            else:
                n_fail += 1
                print(f"  [{i}/{len(targets)}] FAIL {label} ({mode}): "
                      f"primal={pass_primal} bound={pass_bound} "
                      f"ub_match={row['pass_ub_match']} gap={pass_gap} {row['note']}")
            if i % 25 == 0:
                print(f"  ... {i}/{len(targets)} done ({time.time()-t0:.0f}s), "
                      f"{n_pass} pass / {n_fail} fail")

        except Exception as e:  # noqa: BLE001 — report, don't abort the sweep
            row.update({"mode": "error", "pass_all": False, "note": f"EXCEPTION: {e}"})
            rows.append(row); n_fail += 1
            print(f"  [{i}/{len(targets)}] ERROR {label}: {e}")

    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print("=" * 78)
    print(f"VERIFIED: {n_pass} pass  |  {n_fail} fail   "
          f"(stored mu: {n_stored}, rederived: {n_rederived})")
    print(f"Elapsed : {time.time()-t0:.0f}s   |   report → {args.out}")
    print("=" * 78)
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
