# -*- coding: utf-8 -*-
"""Independently verify the published proven-optimal claims.

An instance is reported proven optimal when the certified gap is zero, i.e.
ub == z. Where BPC independently proves the same optimum, the claim is
cross-validated. Where it does not, the claim rests entirely on one floored
Lagrangian value -- and the flooring defect found on 2026-08-26 can drive that
value one profit unit too low, which manufactures a false optimality proof.

This recomputes a fresh Lagrangian bound for those instances, with the
flooring tolerance applied, and classifies each claim:

    CONFIRMED    fresh bound == z          the optimum is re-derived
    UNCONFIRMED  fresh bound  > z          published bound is tighter than a
                                           3000-iteration fresh run achieves,
                                           consistent with a floored artifact
    INVALID      fresh bound  < z          impossible for a valid bound

Also re-runs any instance passed via --extra, used for rows whose refinement
hit a wall-clock cap.
"""
from __future__ import annotations
import argparse, csv, io, math, multiprocessing as mp, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from adapters.ops_adapter import OPSInstance          # noqa: E402
from core.ops_bounds import lagrangian_bound          # noqa: E402

BENCH = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
STUDY = {"B", "C", "D", "EB", "EC", "ED"}
TOL = 1e-9


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def work(task):
    label, family, z, pub_ub, iters, budget = task
    t0 = time.perf_counter()
    try:
        inst = OPSInstance.from_instance_file(
            os.path.join(BENCH, family, "instances", label + ".txt"))
        res = lagrangian_bound(inst, max_iter=iters, lower_bound=z, max_time=budget)
    except Exception as exc:
        return {"instance": label, "verdict": "ERROR", "error": str(exc)[:100]}
    raw = res["upper_bound"]
    fresh = math.floor(raw + TOL)
    verdict = ("CONFIRMED" if abs(fresh - z) < 1e-9
               else ("INVALID" if fresh < z - 1e-9 else "UNCONFIRMED"))
    return {"instance": label, "family": family, "z": z, "published_ub": pub_ub,
            "fresh_raw": raw, "fresh_ub": fresh, "verdict": verdict,
            "iterations": res.get("iterations"),
            "converged": int(bool(res.get("converged"))),
            "secs": round(time.perf_counter() - t0, 1), "error": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--extra", default="", help="comma-separated extra instances")
    cli = ap.parse_args()
    os.chdir(ROOT)

    am = {r["instance"]: r for r in csv.DictReader(
        io.open("results/adaptive_master.csv", encoding="utf-8-sig"))
        if r["family"] in STUDY}

    tasks, kinds = [], {}
    for k, r in am.items():
        g = _f(r["final_cert_gap_pct"])
        z = _f(r["alns_obj"])
        ub = _f(r["best_ub"])
        if g is None or z is None or ub is None or g >= 1e-12:
            continue
        lbl = (r.get("bpc_class_label") or "").lower()
        bks = _f(r.get("bks"))
        bpc_confirms = ("optim" in lbl and bks is not None and abs(bks - z) < 1e-9)
        if bpc_confirms:
            continue                      # cross-validated already
        budget = max(60.0, 3600.0 - (_f(r["alns_runtime_s"]) or 0.0))
        tasks.append((k, r["family"], z, ub, cli.iters, budget))
        kinds[k] = "optimality_claim"

    for k in [x.strip() for x in cli.extra.split(",") if x.strip()]:
        if k in am and k not in kinds:
            r = am[k]
            budget = max(60.0, 3600.0 - (_f(r["alns_runtime_s"]) or 0.0))
            tasks.append((k, r["family"], _f(r["alns_obj"]), _f(r["best_ub"]),
                          cli.iters, budget))
            kinds[k] = "recap"

    stamp = time.strftime("%Y%m%d_%H%M")
    out = os.path.join("results", f"optimality_verification_{stamp}.csv")
    fields = ["instance", "family", "z", "published_ub", "fresh_raw", "fresh_ub",
              "verdict", "iterations", "converged", "secs", "error"]
    print("=" * 74)
    print(f"Verifying {len(tasks)} claims  ({sum(1 for v in kinds.values() if v=='optimality_claim')} "
          f"Lagrangian-only optima, {sum(1 for v in kinds.values() if v=='recap')} re-caps)")
    print(f"Budget per instance: {cli.iters} iters / (3600 - solve time)")
    print(f"Output: {out}")
    print("=" * 74, flush=True)

    tally = {}
    with io.open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        with mp.Pool(processes=cli.workers) as pool:
            for i, res in enumerate(pool.imap_unordered(work, tasks, chunksize=1), 1):
                for k in fields:
                    res.setdefault(k, "")
                w.writerow({k: res[k] for k in fields})
                fh.flush()
                tally[res["verdict"]] = tally.get(res["verdict"], 0) + 1
                if i % 20 == 0 or i == len(tasks):
                    print("  %d/%d  %s" % (i, len(tasks), tally), flush=True)
    print("\nfinal:", tally)


if __name__ == "__main__":
    main()
