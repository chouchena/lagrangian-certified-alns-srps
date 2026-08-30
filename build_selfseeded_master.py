# -*- coding: utf-8 -*-
"""Rebuild the master with no external value anywhere in the bound chain.

The initial upper bounds in results/master_results.csv were produced with the
published BKS as the subgradient's Polyak reference
(archive/run_scripts/run_ops_bounds.py:186-187), and run_adaptive_full.py reads
those bounds in rather than computing its own. On 117 study instances that
inherited bound is still the binding one in the reported results, so the
manuscript's claim that no benchmark solution enters the algorithm is false for
them.

checks/measure_bks_seeding.py recomputed those bounds with the GREEDY
construction value as the Polyak reference -- what a run with no external
information actually holds at that point. This script substitutes them.

One step is easy to miss. Those instances had a zero certified gap, so the
refinement stage SKIPPED them (it skips zero-gap instances, since no valid
bound can fall below an attained value). Once a looser self-seeded bound opens
a nonzero gap, refinement would have run. Substituting without refining would
therefore understate what the self-seeded method actually achieves. Every
instance whose gap reopens is refined here, against its own incumbent.

    python build_selfseeded_master.py --iters 3000 --max-time 600 --workers 6

Writes results/adaptive_master_selfseeded.csv and prints the new headline.
"""
from __future__ import annotations
import argparse
import csv
import io
import math
import os
import statistics as st
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adapters.ops_adapter import OPSInstance      # noqa: E402
from core.ops_bounds import lagrangian_bound      # noqa: E402

BENCH = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
EXCLUDED = ("A", "EA")
EPS = 1e-9          # flooring tolerance; see Appendix A / docs/known_issues.md


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None", "?", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def refine_one(task):
    label, family, obj, cur_ub, iters, max_time = task
    path = os.path.join(BENCH, family, "instances", label + ".txt")
    t0 = time.perf_counter()
    try:
        inst = OPSInstance.from_instance_file(path)
        res = lagrangian_bound(inst, max_iter=iters, lower_bound=obj,
                               max_time=max_time)
    except Exception as exc:
        return {"instance": label, "error": str(exc)[:120]}
    lag_ub = math.floor(res["upper_bound"] + EPS)
    return {"instance": label,
            "refined_ub": min(cur_ub, lag_ub),
            "refine_s": round(time.perf_counter() - t0, 1),
            "error": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--max-time", type=float, default=600.0)
    ap.add_argument("--workers", type=int, default=6)
    cli = ap.parse_args()

    rows = [r for r in csv.DictReader(
        io.open("results/adaptive_master_refined.csv", encoding="utf-8-sig"))
        if r["family"] not in EXCLUDED]
    seed = {r["instance"]: r for r in csv.DictReader(
        io.open("results/analysis/bks_seeding_effect.csv", encoding="utf-8-sig"))}
    print("study set %d   self-seeded bounds available for %d\n" % (len(rows), len(seed)))

    # substitute, then collect those whose gap reopens
    todo, n_sub = [], 0
    for r in rows:
        s = seed.get(r["instance"])
        if not s:
            continue
        new_ub = math.floor(f(s, "ub_greedy") + EPS)
        obj = f(r, "alns_obj")
        r["_selfseed_ub"] = new_ub
        n_sub += 1
        if new_ub > obj:                       # gap reopened -> refinement applies
            todo.append((r["instance"], r["family"], obj, new_ub,
                         cli.iters, cli.max_time))

    print("substituted on %d instances; %d reopen a gap and are refined\n"
          % (n_sub, len(todo)))

    refined = {}
    if todo:
        with ProcessPoolExecutor(max_workers=cli.workers) as ex:
            for i, out in enumerate(ex.map(refine_one, todo), 1):
                if out.get("error"):
                    print("  ERROR %s: %s" % (out["instance"], out["error"]))
                    continue
                refined[out["instance"]] = out
                print("  [%2d/%2d] %-22s ub -> %d  (%.0fs)"
                      % (i, len(todo), out["instance"], out["refined_ub"],
                         out["refine_s"]))

    # final assembly
    for r in rows:
        ub = r.pop("_selfseed_ub", None)
        if ub is None:
            r["selfseed_ub"] = r["best_ub"]
            r["selfseed_gap_pct"] = r["final_cert_gap_pct"]
            r["selfseed_refine_s"] = ""
            continue
        rr = refined.get(r["instance"])
        if rr:
            ub = rr["refined_ub"]
            r["selfseed_refine_s"] = rr["refine_s"]
        else:
            r["selfseed_refine_s"] = ""
        obj = f(r, "alns_obj")
        r["selfseed_ub"] = ub
        r["selfseed_gap_pct"] = max(0.0, (ub - obj) / ub * 100) if ub else ""

    dst = "results/adaptive_master_selfseeded.csv"
    with io.open(dst, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    g = [float(r["selfseed_gap_pct"]) for r in rows if r["selfseed_gap_pct"] != ""]
    old = [f(r, "final_cert_gap_pct") for r in rows]
    old = [x for x in old if x is not None]
    ex0 = sum(1 for x in g if x == 0.0)
    within = lambda t: sum(1 for x in g if x <= t)
    half = 1.96 * st.stdev(g) / (len(g) ** 0.5)

    print("\n" + "=" * 60)
    print("SELF-SEEDED HEADLINE  (no external value in the bound chain)")
    print("=" * 60)
    print("  %-26s %12s %12s" % ("", "as reported", "self-seeded"))
    print("  %-26s %12d %12d" % ("proven optimal",
                                 sum(1 for x in old if x == 0.0), ex0))
    print("  %-26s %11.1f%% %11.1f%%" % ("proven optimal %",
                                         sum(1 for x in old if x == 0.0) / len(old) * 100,
                                         ex0 / len(g) * 100))
    print("  %-26s %12.4f %12.4f" % ("mean gap %", st.mean(old), st.mean(g)))
    print("  %-26s %12.4f %12.4f" % ("median gap %", st.median(old), st.median(g)))
    print("  %-26s %12.4f %12.4f" % ("max gap %", max(old), max(g)))
    print("  %-26s %12s %12s" % ("95%% CI",
                                 "", "[%.4f, %.4f]" % (st.mean(g) - half, st.mean(g) + half)))
    print("  %-26s %12d %12d" % ("within 0.5%",
                                 sum(1 for x in old if x <= 0.5), within(0.5)))
    print("  %-26s %12d %12d" % ("in 0.5-1%",
                                 sum(1 for x in old if 0.5 < x <= 1.0), within(1.0) - within(0.5)))
    print("  %-26s %12d %12d" % ("in 1-2%",
                                 sum(1 for x in old if 1.0 < x <= 2.0), within(2.0) - within(1.0)))
    print("  %-26s %12d %12d" % ("above 2%",
                                 sum(1 for x in old if x > 2.0), len(g) - within(2.0)))
    print("\nwritten: %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
