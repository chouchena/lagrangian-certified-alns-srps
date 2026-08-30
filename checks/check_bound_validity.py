# -*- coding: utf-8 -*-
"""Falsification tests for the reported Lagrangian upper bounds.

A valid upper bound can never fall below a value that some feasible solution
attains, so every independently known feasible value is a test of it. These
checks cannot PROVE validity -- that rests on Proposition 2 (valid for every
mu >= 0) together with exact solution of the per-processor subproblems. What
they establish is whether any independent opportunity to expose an invalid
bound actually finds one.

This matters because the failure mode is real and has occurred: floating-point
evaluation of L(mu) can land marginally below the exact value, and flooring
then removes a whole profit unit, producing a bound that is too TIGHT and a
false claim of optimality. It struck four instances, all at alpha=75. See
Appendix A of the manuscript and docs/known_issues.md.

    python checks/check_bound_validity.py

Exit code 1 if any violation is found.
"""
from __future__ import annotations
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SRC = "results/adaptive_master_refined.csv"
EXCLUDED_FAMILIES = ("A", "EA")
EPS = 1e-9


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> int:
    if not os.path.exists(SRC):
        print("missing %s" % SRC)
        return 1

    rows = [r for r in csv.DictReader(io.open(SRC, encoding="utf-8-sig"))
            if r["family"] not in EXCLUDED_FAMILIES]
    print("study instances: %d\n" % len(rows))

    violations = []

    # 1. never below our own incumbent
    pool = [r for r in rows if f(r, "best_ub") is not None and f(r, "alns_obj") is not None]
    v1 = [r for r in pool if f(r, "best_ub") < f(r, "alns_obj") - EPS]
    print("1  bound below its own incumbent          : %d / %d" % (len(v1), len(pool)))

    # 2. never below an external best-known value.
    # bks holds ORIGINAL external values -- verified by the presence of
    # instances where our objective exceeds it (the improved incumbents).
    wb = [r for r in rows if f(r, "bks") is not None]
    better = sum(1 for r in wb if f(r, "alns_obj") > f(r, "bks"))
    v2 = [r for r in wb if f(r, "best_ub") is not None
          and f(r, "best_ub") < f(r, "bks") - EPS]
    print("2  bound below an external BKS            : %d / %d" % (len(v2), len(wb)))
    print("     (external, not circular: ours exceeds bks on %d instances)" % better)

    # 3. never below an optimum proved by the exact method
    opt = [r for r in wb if (r.get("bpc_class") or "").strip() in ("A", "1")
           or (r.get("bpc_class_label") or "").strip().lower().startswith("opt")]
    v3 = [r for r in opt if f(r, "best_ub") is not None
          and f(r, "best_ub") < f(r, "bks") - EPS]
    print("3  bound below a BPC-proved optimum       : %d / %d" % (len(v3), len(opt)))

    # 4. refinement may only tighten. 'reverified' instances are excluded:
    # those corrected an INVALID baseline upward, which is the intended
    # direction and the whole point of the tolerance.
    ref = [r for r in rows if r.get("refined_source") == "refined"]
    v4 = [r for r in ref if f(r, "baseline_ub") is not None
          and f(r, "best_ub") is not None
          and f(r, "best_ub") > f(r, "baseline_ub") + EPS]
    print("4  refinement loosened a bound            : %d / %d" % (len(v4), len(ref)))

    # positive evidence
    newproof = [r for r in rows if (f(r, "baseline_cert_gap_pct") or 0) > 0
                and f(r, "final_cert_gap_pct") == 0.0]
    corrob = [r for r in newproof if f(r, "bks") is not None
              and f(r, "alns_obj") == f(r, "bks")]
    print("\n   new proofs from refinement            : %d" % len(newproof))
    print("   of which meet an independent BKS      : %d" % len(corrob))
    print("   (a bound converging onto a value reached by another method is")
    print("    corroboration an unsound bound has no reason to produce)")

    violations = v1 + v2 + v3 + v4
    print("\nTOTAL VIOLATIONS: %d" % len(violations))
    for r in violations[:10]:
        print("   %-24s ub=%s obj=%s bks=%s"
              % (r["instance"], r.get("best_ub"), r.get("alns_obj"), r.get("bks")))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
