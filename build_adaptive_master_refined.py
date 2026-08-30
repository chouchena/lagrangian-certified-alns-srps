# -*- coding: utf-8 -*-
"""Build results/adaptive_master_refined.csv.

Deliberately a SEPARATE file rather than an overwrite of adaptive_master.csv.
The paper reports both series: the baseline is the reference ground on which
the trade-off discussion rests, and destroying it would make the paper's own
comparison unreproducible.

Refined rows differ from baseline only in the bound and the gap. Incumbents,
runtimes-before-refinement, BPC columns and instance metadata are copied
through unchanged, so any analysis keyed on the primal is unaffected.

Three corrections are applied:
  * refined bound      ub* = min(baseline_ub, floor(L + 1e-9))
  * the four flooring-induced false optimality claims get their true bounds
  * refine_s is added to the runtime column, and also kept separately

Usage:  python build_adaptive_master_refined.py
"""
import csv, io, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
STUDY = {"B", "C", "D", "EB", "EC", "ED"}

# bounds re-derived by verify_optimality_claims.py; all four converged, so
# these are the Lagrangian dual optima and cannot be tightened further
FALSE_OPTIMA = {
    "C_n080_034_a75_102": 3426,
    "D_n065_028_a75_084": 2147,
    "D_n070_035_a75_105": 2530,
    "ED_n045_008_a75_024": 1472,
}


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


src = "results/adaptive_master.csv"
ref_path = "results/bound_refine_corrected.csv"
for p in (src, ref_path):
    if not os.path.exists(p):
        sys.exit("missing %s" % p)

rows = list(csv.DictReader(io.open(src, encoding="utf-8-sig")))
ref = {r["instance"]: r for r in csv.DictReader(io.open(ref_path, encoding="utf-8-sig"))}

fields = list(rows[0].keys())
for extra in ("baseline_ub", "baseline_cert_gap_pct", "refine_s", "refined_source"):
    if extra not in fields:
        fields.append(extra)

n_ref = n_false = 0
out = []
for r in rows:
    k, fam = r["instance"], r["family"]
    row = dict(r)
    z = f(r["alns_obj"])
    row["baseline_ub"] = r["best_ub"]
    row["baseline_cert_gap_pct"] = r["final_cert_gap_pct"]
    row["refine_s"] = ""
    row["refined_source"] = "baseline"

    if fam in STUDY and k in FALSE_OPTIMA and z is not None:
        ub = float(FALSE_OPTIMA[k])
        row["best_ub"] = "%g" % ub
        row["final_cert_gap_pct"] = "%.4f" % ((ub - z) / ub * 100)
        row["alns_lag_proven_optimal"] = "0"
        row["refined_source"] = "reverified"
        n_false += 1
    elif fam in STUDY and k in ref and z is not None:
        rr = ref[k]
        ub = f(rr["new_ub"])
        gap = f(rr["new_gap_pct"])
        row["best_ub"] = "%g" % ub
        row["final_cert_gap_pct"] = "%.4f" % gap
        row["alns_lag_proven_optimal"] = "1" if gap < 1e-12 else "0"
        row["refine_s"] = rr["refine_s"]
        row["refined_source"] = "refined"
        t = f(r["alns_runtime_s"])
        s = f(rr["refine_s"])
        if t is not None and s is not None:
            row["alns_runtime_s"] = "%.1f" % (t + s)
        n_ref += 1
    out.append(row)

dst = "results/adaptive_master_refined.csv"
with io.open(dst, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for row in out:
        w.writerow({k: row.get(k, "") for k in fields})

study = [r for r in out if r["family"] in STUDY]
gaps = [f(r["final_cert_gap_pct"]) for r in study]
gaps = [g for g in gaps if g is not None]
import statistics as st
print("wrote %s  (%d rows)" % (dst, len(out)))
print("  refined rows      : %d" % n_ref)
print("  re-verified rows  : %d" % n_false)
print("  study instances   : %d" % len(study))
print("  mean %.4f%%  median %.4f%%  max %.4f%%"
      % (st.mean(gaps), st.median(gaps), max(gaps)))
print("  proven optimal    : %d (%.1f%%)"
      % (sum(1 for g in gaps if g < 1e-12),
         100 * sum(1 for g in gaps if g < 1e-12) / len(gaps)))
bad = [r for r in study
       if f(r["best_ub"]) is not None and f(r["alns_obj"]) is not None
       and f(r["best_ub"]) < f(r["alns_obj"]) - 1e-9]
print("  validity (ub < z) : %d  (must be 0)" % len(bad))
