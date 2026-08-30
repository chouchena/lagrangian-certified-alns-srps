# -*- coding: utf-8 -*-
"""Where does the refinement bound stop improving?

run_bound_refine.py ran a fixed 3000 iterations because lagrangian_bound has no
plateau stop: its only exits are the iteration cap, the wall-clock cap, and a
vanishing subgradient. 365 of 376 refinements exhausted the iteration cap, so we
do not know how many were still descending.

This retains bound_history and reports, per instance, the iteration at which the
running best bound last improved. That distribution determines whether a plateau
stop would save time, and what threshold it would need -- noting the subgradient
is non-monotone and switches to a diminishing step after 30 stalls, so a
too-eager threshold would cut off the recovery phase.

Stratified across families and gap magnitude. Analysis only; changes nothing.
"""
from __future__ import annotations
import csv, io, json, math, multiprocessing as mp, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from adapters.ops_adapter import OPSInstance          # noqa: E402
from core.ops_bounds import lagrangian_bound          # noqa: E402

BENCH = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
STUDY = {"B", "C", "D", "EB", "EC", "ED"}
ITERS = 3000


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run(task):
    label, family, z = task
    try:
        inst = OPSInstance.from_instance_file(
            os.path.join(BENCH, family, "instances", label + ".txt"))
        t0 = time.perf_counter()
        res = lagrangian_bound(inst, max_iter=ITERS, lower_bound=z, max_time=1200.0)
        secs = time.perf_counter() - t0
    except Exception as exc:
        return {"instance": label, "error": str(exc)[:100]}

    hist = res.get("bound_history") or []
    best, last_imp, marks = float("inf"), 0, {}
    for i, v in enumerate(hist, 1):
        if v < best - 1e-9:
            best = v
            last_imp = i
        marks[i] = best
    final = math.floor(best + 1e-9) if hist else None
    # iteration at which the FLOORED bound reached its final value
    floor_reached = 0
    for i in sorted(marks):
        if math.floor(marks[i] + 1e-9) <= final:
            floor_reached = i
            break
    return {"instance": label, "family": family, "z": z,
            "iterations_run": len(hist), "last_improvement_iter": last_imp,
            "floor_final_at_iter": floor_reached, "final_floor": final,
            "converged": int(bool(res.get("converged"))),
            "secs": round(secs, 1), "error": ""}


def main():
    os.chdir(ROOT)
    rows = [r for r in csv.DictReader(
        io.open("results/adaptive_master.csv", encoding="utf-8-sig"))
        if r["family"] in STUDY and (_f(r["final_cert_gap_pct"]) or 0) > 1e-12]

    # stratify: per family, take the loosest, a median-ish, and a tight one
    byfam = {}
    for r in rows:
        byfam.setdefault(r["family"], []).append(r)
    tasks = []
    for fam, rs in sorted(byfam.items()):
        rs.sort(key=lambda r: -(_f(r["final_cert_gap_pct"]) or 0))
        n = len(rs)
        for idx in (0, n // 4, n // 2, (3 * n) // 4, n - 1):
            r = rs[idx]
            t = (r["instance"], fam, _f(r["alns_obj"]))
            if t not in tasks:
                tasks.append(t)

    stamp = time.strftime("%Y%m%d_%H%M")
    out = os.path.join("results", f"plateau_{stamp}.csv")
    fields = ["instance", "family", "z", "iterations_run", "last_improvement_iter",
              "floor_final_at_iter", "final_floor", "converged", "secs", "error"]
    print("=" * 72)
    print(f"Plateau measurement -- {len(tasks)} instances, {ITERS} iterations")
    print(f"Output: {out}")
    print("=" * 72, flush=True)

    done = 0
    with io.open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        with mp.Pool(processes=6) as pool:
            for res in pool.imap_unordered(run, tasks, chunksize=1):
                done += 1
                for k in fields:
                    res.setdefault(k, "")
                w.writerow({k: res[k] for k in fields})
                fh.flush()
                if done % 5 == 0 or done == len(tasks):
                    print(f"  {done}/{len(tasks)}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
