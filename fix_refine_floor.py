# -*- coding: utf-8 -*-
"""Re-derive refined bounds with a flooring tolerance and a validity guard.

Two defects in the raw refinement output:

1. Flooring a float. L(mu) is real-valued and flooring is sound in exact
   arithmetic (profits are integral, so P* <= floor(L)). But L is a sum of many
   floating-point terms, and ~1e-13 of accumulated error can place the computed
   value just below an integer, after which floor() discards a whole profit
   unit. The trigger is systematic: as the subgradient converges, L -> P* from
   ABOVE, so it sits adjacent to an integer exactly when convergence occurs.
   Observed on 5 of the 9 converged instances.

2. No validity guard. A bound below the incumbent is invalid, and because the
   gap was clamped at zero it surfaced as a *proven optimum* -- the most
   dangerous possible presentation of the error.

Fix: floor(L + 1e-9), then never report a bound below the incumbent. Both are
applied to the stored lag_raw, so nothing is recomputed.
"""
import csv, glob, io, math, os, statistics as st

os.chdir(os.path.dirname(os.path.abspath(__file__)))
TOL = 1e-9
STUDY = {"B", "C", "D", "EB", "EC", "ED"}


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


am = {r["instance"]: r for r in csv.DictReader(
    io.open("results/adaptive_master.csv", encoding="utf-8-sig")) if r["family"] in STUDY}

rows = {}
for p in sorted(glob.glob("results/bound_refine_*.csv")):
    for r in csv.DictReader(io.open(p, encoding="utf-8-sig")):
        if not r.get("error"):
            rows[r["instance"]] = r
print("refined rows: %d" % len(rows))

out = []
moved = invalid = 0
for k, r in sorted(rows.items()):
    z = f(am[k]["alns_obj"])
    pub_ub = f(r["published_ub"])
    pub_gap = f(r["published_gap_pct"])
    raw = f(r["lag_raw"])
    if None in (z, pub_ub, raw):
        continue

    old_lag = math.floor(raw)
    new_lag = math.floor(raw + TOL)
    if new_lag != old_lag:
        moved += 1

    ub = min(pub_ub, new_lag)
    guard = ""
    if ub < z - 1e-9:                     # still invalid -> discard refinement
        invalid += 1
        guard = "discarded_below_incumbent"
        ub = pub_ub
    gap = (ub - z) / ub * 100 if ub else pub_gap

    out.append({
        "instance": k, "family": am[k]["family"], "obj": z,
        "published_ub": pub_ub, "published_gap_pct": pub_gap,
        "lag_raw": raw, "lag_ub": new_lag, "new_ub": ub,
        "new_gap_pct": round(max(0.0, gap), 6),
        "improved": int(ub < pub_ub),
        "iterations": r["iterations"], "converged": r["converged"],
        "refine_s": r["refine_s"], "guard": guard,
    })

print("rows whose floor changed under tolerance : %d" % moved)
print("rows still invalid, refinement discarded : %d" % invalid)

dst = "results/bound_refine_corrected.csv"
with io.open(dst, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    for r in out:
        w.writerow(r)
print("wrote %s (%d rows)" % (dst, len(out)))

ref = {r["instance"]: r for r in out}
old = [f(r["final_cert_gap_pct"]) for r in am.values()]
new = [ref[k]["new_gap_pct"] if k in ref else f(r["final_cert_gap_pct"])
       for k, r in am.items()]
old = [x for x in old if x is not None]
new = [x for x in new if x is not None]
print("\n%-24s %11s %11s" % ("", "published", "refined"))
print("%-24s %10.4f%% %10.4f%%" % ("mean certified gap", st.mean(old), st.mean(new)))
print("%-24s %10.4f%% %10.4f%%" % ("median", st.median(old), st.median(new)))
print("%-24s %10.4f%% %10.4f%%" % ("maximum", max(old), max(new)))
po_o = sum(1 for g in old if g < 1e-12)
po_n = sum(1 for g in new if g < 1e-12)
print("%-24s %8d    %8d   (%.1f%% -> %.1f%%)"
      % ("proven optimal", po_o, po_n, 100 * po_o / len(old), 100 * po_n / len(new)))
bad = [r for r in out if r["new_ub"] < r["obj"] - 1e-9]
print("\nvalidity check -- bounds below incumbent: %d" % len(bad))
