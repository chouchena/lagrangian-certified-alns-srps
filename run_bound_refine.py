# -*- coding: utf-8 -*-
"""Post-hoc Lagrangian certificate refinement.

An upper bound does not depend on the search that produced the incumbent, so a
tighter valid bound can be computed after the fact and combined with the
published one:

    ub* = min(published_ub, floor(L(mu)))

Both are valid upper bounds on the same instance, so the minimum is valid, and
the certified gap for the SAME incumbent can only shrink. Nothing about the
primal solution changes, so this introduces no stochastic variation.

This is why it succeeds where raising the in-loop dual budget failed: run
in-loop, extra subgradient time is taken from the primal search inside the
3600 s per-instance cap; run offline, it competes with nothing. The Polyak
reference is the published incumbent, which is the tightest lower reference
available and better than anything the solver had mid-search.

Only instances with a nonzero published gap are processed; a gap of zero
cannot improve.

    python run_bound_refine.py --iters 1000 --max-time 300
"""
from __future__ import annotations
import argparse, csv, io, math, multiprocessing as mp, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from adapters.ops_adapter import OPSInstance          # noqa: E402
from core.ops_bounds import lagrangian_bound          # noqa: E402

BENCH = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
MASTER = os.path.join("results", "adaptive_master.csv")
STUDY = {"B", "C", "D", "EB", "EC", "ED"}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def refine(task):
    label, family, obj, pub_ub, pub_gap, iters, max_time = task
    path = os.path.join(BENCH, family, "instances", label + ".txt")
    t0 = time.perf_counter()
    try:
        inst = OPSInstance.from_instance_file(path)
        res = lagrangian_bound(inst, max_iter=iters, lower_bound=obj, max_time=max_time)
    except Exception as exc:                                   # pragma: no cover
        return {"instance": label, "family": family, "error": str(exc)[:120]}
    raw = res["upper_bound"]
    lag_ub = math.floor(raw)
    new_ub = min(pub_ub, lag_ub)
    new_gap = (new_ub - obj) / new_ub * 100 if new_ub else pub_gap
    return {
        "instance": label, "family": family, "obj": obj,
        "published_ub": pub_ub, "published_gap_pct": pub_gap,
        "lag_raw": raw, "lag_ub": lag_ub, "new_ub": new_ub,
        "new_gap_pct": max(0.0, new_gap),
        "improved": int(new_ub < pub_ub),
        "iterations": res.get("iterations"),
        "converged": int(bool(res.get("converged"))),
        "refine_s": round(time.perf_counter() - t0, 1),
        "error": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--max-time", type=float, default=300.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="process at most N instances")
    ap.add_argument("--from-run", default="",
                    help="Refine against a regime run's own output "
                         "(adaptive_full_*.csv, beta_* columns) instead of "
                         "the master. Required when comparing regimes, so "
                         "each is refined against its own incumbents.")
    ap.add_argument("--offset", type=int, default=0,
                    help="skip the first N (tasks are ordered loosest gap first, "
                         "so batches run from most to least expected gain)")
    cli = ap.parse_args()

    os.chdir(ROOT)
    src = cli.from_run or MASTER
    rows = [r for r in csv.DictReader(io.open(src, encoding="utf-8-sig"))
            if r["family"] in STUDY]
    OBJ, UB, GAP = (("beta_obj", "beta_ub", "beta_gap_pct") if cli.from_run
                    else ("alns_obj", "best_ub", "final_cert_gap_pct"))
    print(f"input: {src}  (columns {OBJ} / {UB} / {GAP})")

    tasks = []
    for r in rows:
        obj, ub, gap = _f(r[OBJ]), _f(r[UB]), _f(r[GAP])
        if None in (obj, ub, gap) or gap <= 1e-12:
            continue
        tasks.append((r["instance"], r["family"], obj, ub, gap, cli.iters, cli.max_time))
    tasks.sort(key=lambda t: -t[4])            # loosest gaps first
    if cli.offset:
        tasks = tasks[cli.offset:]
    if cli.limit:
        tasks = tasks[:cli.limit]

    stamp = time.strftime("%Y%m%d_%H%M")
    out = os.path.join("results", f"bound_refine_{stamp}.csv")
    fields = ["instance", "family", "obj", "published_ub", "published_gap_pct",
              "lag_raw", "lag_ub", "new_ub", "new_gap_pct", "improved",
              "iterations", "converged", "refine_s", "error"]

    print("=" * 78)
    print(f"Post-hoc bound refinement — {len(tasks)} instances "
          f"(offset {cli.offset}), ordered loosest gap first")
    print(f"Budget  : {cli.iters} iterations / {cli.max_time:g}s   workers: {cli.workers}")
    print(f"Output  : {out}")
    print("=" * 78, flush=True)

    done = imp = 0
    t0 = time.time()
    with io.open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        with mp.Pool(processes=cli.workers) as pool:
            for res in pool.imap_unordered(refine, tasks, chunksize=1):
                done += 1
                for k in fields:
                    res.setdefault(k, "")
                w.writerow({k: res[k] for k in fields})
                fh.flush()
                imp += int(res.get("improved") or 0)
                if done % 20 == 0 or done == len(tasks):
                    print(f"  {done}/{len(tasks)}  improved={imp}  "
                          f"({time.time() - t0:.0f}s)", flush=True)
    print(f"\nfinished: {done} instances, {imp} tightened, "
          f"{time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
