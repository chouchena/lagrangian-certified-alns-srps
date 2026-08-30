# -*- coding: utf-8 -*-
"""How much did BKS-seeding the Polyak reference actually buy?

The initial upper bounds in results/master_results.csv were produced with

    lb_for_lag = float(bks) if bks else 0.0
    lagrangian_bound(inst, max_iter=..., lower_bound=lb_for_lag)

(archive/run_scripts/run_ops_bounds.py:186-187), i.e. the published benchmark
solution calibrated the subgradient's step size. run_adaptive_full.py reads
that bound in rather than computing one, so the manuscript's claim that "no
benchmark solution enters the algorithm" is false as an account of provenance.

Validity is not in question -- Proposition 2 holds for every mu. The open
question is MAGNITUDE: would a self-seeded run have reached a comparable
bound? A Polyak reference only helps insofar as it is close to the optimum
from below, and our own incumbent equals or beats BKS on 449 of 461 instances,
so the head start may be small.

This recomputes the initial bound both ways on a stratified sample and reports
the distribution of the difference, plus how many currently-reported optimality
proofs would survive a self-seeded bound.

    python checks/measure_bks_seeding.py --n 40 --iters 200 --workers 6
"""
from __future__ import annotations
import argparse
import csv
import io
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adapters.ops_adapter import OPSInstance, OPSSolution   # noqa: E402
from core.ops_bounds import lagrangian_bound                # noqa: E402
from run_adaptive_full import _repair_profit                # noqa: E402

BENCH = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
EXCLUDED = ("A", "EA")


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None", "?", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def instance_path(family, label):
    return os.path.join(BENCH, family, "instances", label + ".txt")


def one(task):
    label, family, bks, iters = task
    p = instance_path(family, label)
    if not os.path.exists(p):
        return None
    inst = OPSInstance.from_instance_file(p)

    # greedy incumbent: what a cold run actually has when the initial bound
    # is computed, with no access to any external value
    sol = OPSSolution(inst)
    _repair_profit(sol)
    greedy = sol.objective()

    out = {"instance": label, "family": family, "bks": bks, "greedy": greedy}
    for tag, lb in (("bks", float(bks) if bks else 0.0), ("greedy", float(greedy))):
        t0 = time.perf_counter()
        r = lagrangian_bound(inst, max_iter=iters, lower_bound=lb)
        out["ub_" + tag] = r["upper_bound"]
        out["s_" + tag] = round(time.perf_counter() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--affected-only", action="store_true",
                    help="only instances whose FINAL bound is the inherited one "
                         "-- the population where BKS-seeding still shows through")
    cli = ap.parse_args()

    rows = [r for r in csv.DictReader(
        io.open("results/adaptive_master_refined.csv", encoding="utf-8-sig"))
        if r["family"] not in EXCLUDED and f(r, "bks") is not None]

    if cli.affected_only:
        old = {r["instance"]: r for r in csv.DictReader(
            io.open("results/master_results.csv", encoding="utf-8-sig"))}
        rows = [r for r in rows
                if r["instance"] in old
                and f(r, "best_ub") is not None
                and f(old[r["instance"]], "best_ub") == f(r, "best_ub")]
        print("restricted to %d instances whose final bound is the inherited one"
              % len(rows))
        cli.n = len(rows)

    # stratify across family x alpha so the sample is not concentrated
    buckets = {}
    for r in rows:
        buckets.setdefault((r["family"], r["alpha"]), []).append(r)
    rnd = random.Random(cli.seed)
    picked, keys = [], sorted(buckets)
    while len(picked) < min(cli.n, len(rows)):
        progressed = False
        for k in keys:
            b = buckets[k]
            if b and len(picked) < cli.n:
                picked.append(b.pop(rnd.randrange(len(b))))
                progressed = True
        if not progressed:
            break

    print("sample: %d instances, %d subgradient iterations, %d workers\n"
          % (len(picked), cli.iters, cli.workers))
    tasks = [(r["instance"], r["family"], f(r, "bks"), cli.iters) for r in picked]

    res = []
    with ProcessPoolExecutor(max_workers=cli.workers) as ex:
        for i, out in enumerate(ex.map(one, tasks), 1):
            if out:
                res.append(out)
                print("  [%2d/%2d] %-22s ub_bks=%9.2f ub_greedy=%9.2f  delta=%+8.2f"
                      % (i, len(tasks), out["instance"], out["ub_bks"],
                         out["ub_greedy"], out["ub_greedy"] - out["ub_bks"]))

    if not res:
        print("no results")
        return 1

    import math
    import statistics as st
    cur = {r["instance"]: r for r in rows}
    d = [x["ub_greedy"] - x["ub_bks"] for x in res]
    print("\n" + "=" * 62)
    print("BOUND DIFFERENCE (greedy-seeded minus BKS-seeded; >0 means looser)")
    print("=" * 62)
    print("  mean %+0.3f   median %+0.3f   min %+0.3f   max %+0.3f"
          % (st.mean(d), st.median(d), min(d), max(d)))
    ident = sum(1 for x in d if abs(x) < 1e-6)
    print("  identical: %d/%d    looser: %d    tighter: %d"
          % (ident, len(d), sum(1 for x in d if x > 1e-6),
             sum(1 for x in d if x < -1e-6)))

    # relative, and the consequence that matters: surviving optimality proofs
    rel = [(x["ub_greedy"] - x["ub_bks"]) / x["ub_bks"] * 100 for x in res if x["ub_bks"]]
    print("  as %% of bound: mean %+0.4f%%  max %+0.4f%%" % (st.mean(rel), max(rel)))

    proven = [x for x in res
              if cur.get(x["instance"]) and f(cur[x["instance"]], "final_cert_gap_pct") == 0.0]
    survive = 0
    for x in proven:
        obj = f(cur[x["instance"]], "alns_obj")
        if obj is not None and math.floor(x["ub_greedy"] + 1e-9) <= obj:
            survive += 1
    print("\n  currently-proven instances in sample : %d" % len(proven))
    print("  still proven with a greedy-seeded bound: %d" % survive)
    if proven:
        print("  survival rate: %.0f%%" % (survive / len(proven) * 100))

    dst = "results/analysis/bks_seeding_effect.csv"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with io.open(dst, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0].keys()))
        w.writeheader()
        for x in res:
            w.writerow(x)
    print("\nwritten: %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
