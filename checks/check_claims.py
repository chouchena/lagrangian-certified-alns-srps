# -*- coding: utf-8 -*-
"""Recompute every headline number in the manuscript from the data.

Prints MANUSCRIPT vs COMPUTED side by side. This exists because the same
column-confusion trap produced wrong figures twice: master_obj instead of
alns_obj (giving 0.147% for a 0.133% result), and master_rt_s instead of
alns_runtime_s (giving a 91.4-minute maximum under a 60-minute cap). The
master_* columns belong to an earlier campaign and are NOT this method's
output. See the project notes for the full list of data traps.

    python checks/check_claims.py

Exit code 1 if any claim fails to reproduce.
"""
from __future__ import annotations
import csv
import io
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SRC = "results/adaptive_master_refined.csv"

# Families A and EA are the |K_j|=1 cases, excluded from the study set.
EXCLUDED_FAMILIES = ("A", "EA")

# gap columns: baseline = before refinement, final = after (the headline series)
GAP_FINAL = "final_cert_gap_pct"
GAP_BASE = "baseline_cert_gap_pct"
OBJ = "alns_obj"          # NOT master_obj
RT = "alns_runtime_s"     # NOT master_rt_s


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
    g = [f(r, GAP_FINAL) for r in rows]
    g = [x for x in g if x is not None]
    gb = [f(r, GAP_BASE) for r in rows]
    gb = [x for x in gb if x is not None]

    n_exact = sum(1 for x in g if x == 0.0)
    mean = st.mean(g)
    half = 1.96 * st.stdev(g) / (len(g) ** 0.5)
    within = lambda t: sum(1 for x in g if x <= t)

    rt = [f(r, RT) for r in rows]
    rt = [x for x in rt if x is not None]

    # pre-refinement proven count, EXCLUDING the four instances whose baseline
    # bound was invalid (flooring defect) and was corrected upward. Counting
    # them gives 284 and breaks the arithmetic 280 + 166 = 446.
    base_exact_valid = sum(1 for r in rows
                           if f(r, GAP_BASE) == 0.0
                           and r.get("refined_source") != "reverified")
    newproofs = sum(1 for r in rows
                    if (f(r, GAP_BASE) or 0) > 0 and f(r, GAP_FINAL) == 0.0)

    CLAIMS = [
        ("study instances", 660, len(rows)),
        ("proven optimal", 446, n_exact),
        ("proven optimal %", 67.6, round(n_exact / len(g) * 100, 1)),
        ("mean certified gap %", 0.066, round(mean, 3)),
        ("median certified gap %", 0.000, round(st.median(g), 3)),
        ("max certified gap %", 1.613, round(max(g), 3)),
        ("CI low %", 0.051, round(mean - half, 3)),
        ("CI high %", 0.081, round(mean + half, 3)),
        ("within 0.5%", 639, within(0.5)),
        ("within 0.5% (pct)", 96.8, round(within(0.5) / len(g) * 100, 1)),
        ("in 0.5-1%", 12, within(1.0) - within(0.5)),
        ("in 1-2%", 9, within(2.0) - within(1.0)),
        ("above 2%", 0, len(g) - within(2.0)),
        ("pre-refinement proven", 280, base_exact_valid),
        ("pre-refinement proven %", 42.4, round(base_exact_valid / len(g) * 100, 1)),
        ("new proofs from refinement", 166, newproofs),
        ("median runtime (min)", 6.2, round(st.median(rt) / 60, 1)),
        ("max runtime (min)", 46.9, round(max(rt) / 60, 1)),
    ]

    print("source: %s   study set: %d\n" % (SRC, len(rows)))
    print("%-30s %10s %10s" % ("claim", "MANUSCRIPT", "COMPUTED"))
    print("-" * 54)
    bad = 0
    for name, paper, comp in CLAIMS:
        ok = (paper == comp if isinstance(paper, int)
              else abs(paper - comp) <= 0.0501 if paper > 10
              else abs(paper - comp) <= 0.0015)
        bad += not ok
        print("%-30s %10s %10s  %s" % (name, paper, comp, "" if ok else "<<< MISMATCH"))

    print("\narithmetic: %d pre-refinement + %d new = %d (must equal %d)"
          % (base_exact_valid, newproofs, base_exact_valid + newproofs, n_exact))
    if base_exact_valid + newproofs != n_exact:
        bad += 1

    print("\n%d mismatch(es)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
