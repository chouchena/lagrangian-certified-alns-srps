# -*- coding: utf-8 -*-
"""Ablation arm B5 (no ejection chain), computed exactly rather than run.

ejection_chain is called once at run_adaptive_full.py:406, AFTER the search
loop has exited, and its result feeds nothing back: final_obj is read
immediately afterwards. Removing it therefore yields exactly

    obj_without_EC = obj - ec_gain

so the arm's marginal effect on the certified gap is the identity

    marginal = gap(without EC) - gap(with EC) = ec_gain / ub * 100

This is not an approximation of an experiment. It is the experiment, evaluated
in closed form over all 660 instances -- a census rather than the 40-instance
sample a run would have given, at no compute cost.

Gaps are taken against the certified bounds in results/bounds_certified.csv,
which carry deposited multipliers.

    python checks/compute_ec_ablation.py
"""
from __future__ import annotations
import csv
import io
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

EXCLUDED = ("A", "EA")


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None", "?", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> int:
    master = {r["instance"]: r for r in csv.DictReader(
        io.open("results/adaptive_master_refined.csv", encoding="utf-8-sig"))
        if r["family"] not in EXCLUDED}
    bounds = {r["instance"]: r for r in csv.DictReader(
        io.open("results/bounds_certified.csv", encoding="utf-8-sig"))}

    strata = {"hard tail (TIERS_EXHAUSTED)": [],
              "multi-phase, closes": [],
              "single phase": []}

    for inst, r in master.items():
        b = bounds.get(inst)
        if not b:
            continue
        ub = f(b, "final_ub")
        obj = f(r, "alns_obj")
        ec = f(r, "beta_ec_gain") or 0.0
        if ub is None or obj is None or ub <= 0:
            continue
        marginal = ec / ub * 100.0          # pp added to the gap without EC
        stop = (r.get("beta_stop_reason") or "").strip()
        phases = f(r, "beta_phases") or 0
        key = ("hard tail (TIERS_EXHAUSTED)" if stop == "TIERS_EXHAUSTED"
               else "multi-phase, closes" if phases > 1
               else "single phase")
        strata[key].append((inst, marginal, ec))

    print("B5 — no ejection chain: exact marginal effect on the certified gap")
    print("computed in closed form over all %d study instances\n"
          % sum(len(v) for v in strata.values()))
    print("%-28s %5s %10s %10s %10s %8s"
          % ("stratum", "n", "mean pp", "median", "max pp", "nonzero"))
    print("-" * 76)

    allm = []
    for name, rows in strata.items():
        if not rows:
            continue
        m = [x[1] for x in rows]
        allm += m
        nz = sum(1 for x in m if x > 1e-12)
        print("%-28s %5d %10.4f %10.4f %10.4f %5d/%d"
              % (name, len(m), st.mean(m), st.median(m), max(m), nz, len(m)))

    nz_all = sum(1 for x in allm if x > 1e-12)
    print("-" * 76)
    print("%-28s %5d %10.4f %10.4f %10.4f %5d/%d"
          % ("ALL", len(allm), st.mean(allm), st.median(allm), max(allm),
             nz_all, len(allm)))

    print("\ninstances where the ejection chain changed the objective:")
    hits = sorted([x for v in strata.values() for x in v if x[2] > 0],
                  key=lambda t: -t[1])
    for inst, marg, ec in hits:
        print("   %-24s +%d profit unit(s)   %.4f pp" % (inst, int(ec), marg))
    if not hits:
        print("   none")

    print("\nInterpretation: removing the ejection chain costs %.4f pp of mean"
          % st.mean(allm))
    print("certified gap over the study set, on %d of %d instances."
          % (nz_all, len(allm)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
