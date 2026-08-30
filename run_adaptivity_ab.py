# -*- coding: utf-8 -*-
"""Does the adaptive operator weighting earn its name? A paired inner-level A/B.

THE QUESTION. The method is an *Adaptive* Large Neighborhood Search. Operator
usage shares show the weights move (destroy [0.287, 0.402, 0.311] against a
uniform 0.333), but movement is not benefit. No experiment in this project has
ever tested whether adapting them helps.

WHY NOT A FULL ARM. A conventional ablation arm would run the whole adaptive
loop with weighting disabled and compare certified gaps. That design cannot
answer the question here, because 415 of the 660 instances terminate on the
0.3% gap threshold: their gaps are censored at 0.2998 by construction, so any
arm that still crosses the threshold lands on the same objective. Measured on
the previous ablation, this produced exactly 0.0000 pp on 11 of 11
discriminating instances for three separate arms -- not small effects,
censoring.

THE DESIGN. `alns_search` seeds the global RNG on entry (search_controller.py:108)
and every operator draws from it, so a call is fully determined by
(seed, start solution). Two calls from an identical greedy start with an
identical seed therefore differ only in the mechanism under test.

  adaptive : lambda_decay = 0.8  (production)
  frozen   : lambda_decay = 1.0  -> w = 1.0*w + 0*(score) -- weights never move

Freezing via lambda_decay is a bit-exact isolation: initial weights are
[1.0]*k, `roulette_select` over equal weights *is* uniform selection, and it
consumes the same single random.uniform draw either way. Nothing but the
mechanism changes.

The unit of observation is one (instance, seed) pair, not one instance, and
there is no outer loop -- no phases, no tiers, no bound, no stopping rule, so
no censoring. The outcome is the objective after a fixed iteration count:
continuous, uncensored, exactly paired.

ITERATION-MATCHED, NOT TIME-MATCHED. Deliberate. Acceptance variants differ in
cost per iteration by up to 1.84x, so a wall-clock budget would compare
different amounts of search and manufacture an effect.

    python run_adaptivity_ab.py --smoke
    python run_adaptivity_ab.py --instances 40 --seeds 3 --iters 500 --workers 6
"""
from __future__ import annotations
import argparse, csv, io, json, os, platform, random, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adapters.ops_adapter import OPSInstance, OPSSolution      # noqa: E402
from core.search_controller import alns_search                 # noqa: E402
from core.operators import (destroy_random, destroy_shaw,      # noqa: E402
                            destroy_worst)
from run_adaptive_full import (_repair_profit, _repair_ratio,   # noqa: E402
                               _repair_regret2, _repair_random,
                               DESTROY_FRACS)

BENCH = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
DESTROY_OPS = [destroy_random, destroy_worst, destroy_shaw]
REPAIR_OPS = [_repair_profit, _repair_ratio, _repair_regret2, _repair_random]
EXCLUDED = ("A", "EA")


def provenance(argv):
    def git(*a):
        try:
            return subprocess.run(["git", *a], capture_output=True, text=True,
                                  cwd=ROOT).stdout.strip()
        except Exception:
            return "?"
    # Reproducibility depends on the SOURCE tree, not on whether result files
    # happen to be committed. Reporting a bare "dirty" conflates the two and
    # makes every run look unreproducible once it writes its own output.
    porcelain = git("status", "--porcelain")
    src_dirty = [l for l in porcelain.splitlines()
                 if l[3:].split("/")[0] not in ("results", "archive")
                 and not l.startswith("??")]
    return {
        "commit": git("rev-parse", "HEAD"),
        "source_dirty": bool(src_dirty),
        "source_dirty_files": [l[3:] for l in src_dirty],
        "argv": " ".join(argv),
        "python": sys.version.split()[0],
        "machine": platform.node(),
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None", "?", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _fresh(inst):
    """Greedy construction — the identical start both variants receive."""
    s = OPSSolution(inst)
    _repair_profit(s)
    return s


def _run(inst, seed, iters, lambda_decay):
    sol = _fresh(inst)
    # match production exactly (run_adaptive_full.py:223,252): destroy size is a
    # random draw in [1, d_max] with d_max from the SELECTED count at tier 0
    n_sel = max(1, len(sol.selected))
    d_max = max(3, int(n_sel * DESTROY_FRACS[0]))
    t0 = time.perf_counter()
    best, obj, info = alns_search(
        initial_solution=sol,
        copy_fn=lambda s: s.copy(),
        objective_fn=lambda s: -s.objective(),      # lower is better
        destroy_ops=DESTROY_OPS,
        repair_ops=REPAIR_OPS,
        destroy_size_fn=lambda: random.randint(1, d_max),
        max_iterations=iters,
        start_temp=100.0,
        cooling_rate=0.985,
        lambda_decay=lambda_decay,
        seed=seed,
    )
    return {
        "obj": best.objective(),
        "s": round(time.perf_counter() - t0, 2),
        "iters": info.get("iterations_run"),
        "d_w": info.get("d_weights"),
        "r_w": info.get("r_weights"),
        "d_u": info.get("d_usage"),
        "r_u": info.get("r_usage"),
        "acc_worse": info.get("n_accept_worse"),
    }


def one(task):
    label, family, seed, iters = task
    p = os.path.join(BENCH, family, "instances", label + ".txt")
    if not os.path.exists(p):
        return {"instance": label, "seed": seed, "error": "missing instance"}
    try:
        inst = OPSInstance.from_instance_file(p)
        ad = _run(inst, seed, iters, 0.8)      # adaptive (production)
        fr = _run(inst, seed, iters, 1.0)      # frozen -> uniform selection
    except Exception as exc:                                  # pragma: no cover
        return {"instance": label, "seed": seed, "error": str(exc)[:140]}

    # frozen weights must be exactly the initial [1.0]*k, or the isolation leaked
    leak = ""
    for name, w, k in (("d", fr["d_w"], len(DESTROY_OPS)),
                       ("r", fr["r_w"], len(REPAIR_OPS))):
        if w is not None and any(abs(x - 1.0) > 1e-12 for x in w):
            leak += "%s_weights_moved " % name
    return {
        "instance": label, "family": family, "seed": seed, "iters": iters,
        "obj_adaptive": ad["obj"], "obj_frozen": fr["obj"],
        "delta": ad["obj"] - fr["obj"],          # >0 means adaptivity helped
        "s_adaptive": ad["s"], "s_frozen": fr["s"],
        "d_weights_adaptive": ad["d_w"], "r_weights_adaptive": ad["r_w"],
        "d_usage_adaptive": ad["d_u"], "r_usage_adaptive": fr["d_u"] and ad["r_u"],
        "d_usage_frozen": fr["d_u"], "r_usage_frozen": fr["r_u"],
        "acc_worse_adaptive": ad["acc_worse"], "acc_worse_frozen": fr["acc_worse"],
        "isolation_leak": leak.strip(), "error": "",
    }


FIELDS = ["instance", "family", "seed", "iters", "obj_adaptive", "obj_frozen",
          "delta", "s_adaptive", "s_frozen", "d_weights_adaptive",
          "r_weights_adaptive", "d_usage_adaptive", "r_usage_adaptive",
          "d_usage_frozen", "r_usage_frozen", "acc_worse_adaptive",
          "acc_worse_frozen", "isolation_leak", "error"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=40)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--iters", type=int, default=500)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sample-seed", type=int, default=20260827)
    ap.add_argument("--smoke", action="store_true",
                    help="3 instances x 2 seeds x 60 iterations")
    cli = ap.parse_args()
    if cli.smoke:
        cli.instances, cli.seeds, cli.iters, cli.workers = 3, 2, 60, 3

    rows = [r for r in csv.DictReader(
        io.open("results/adaptive_master_refined.csv", encoding="utf-8-sig"))
        if r["family"] not in EXCLUDED]
    # hard tail: the uncensored stratum (min gap 0.3059 vs closing max 0.2998)
    tail = [r for r in rows if r.get("beta_stop_reason") == "TIERS_EXHAUSTED"]
    rnd = random.Random(cli.sample_seed)
    pick = tail if cli.instances >= len(tail) else rnd.sample(tail, cli.instances)

    seeds = [42, 123, 456, 789, 1337, 2024][:cli.seeds]
    tasks = [(r["instance"], r["family"], s, cli.iters) for r in pick for s in seeds]

    prov = provenance(sys.argv)
    stamp = time.strftime("%Y%m%d_%H%M")
    dst = "results/analysis/adaptivity_ab_%s.csv" % stamp
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    io.open(dst.replace(".csv", "_manifest.json"), "w", encoding="utf-8").write(
        json.dumps({**prov, "instances": [r["instance"] for r in pick],
                    "seeds": seeds, "iters": cli.iters}, indent=2))

    print("adaptivity A/B  |  %d instances x %d seeds = %d pairs  |  %d iters  |  %d workers"
          % (len(pick), len(seeds), len(tasks), cli.iters, cli.workers), flush=True)
    print("commit %s%s\n" % (prov["commit"][:9], "  SOURCE-DIRTY" if prov["source_dirty"] else ""),
          flush=True)

    done = err = leaks = 0
    t0 = time.perf_counter()
    # incremental write: a long run must not depend on a terminal write
    with io.open(dst, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader(); fh.flush()
        with ProcessPoolExecutor(max_workers=cli.workers) as ex:
            for r in ex.map(one, tasks):
                if r.get("error"):
                    err += 1
                    print("  ERROR %-22s seed=%s %s"
                          % (r["instance"], r.get("seed"), r["error"]), flush=True)
                    continue
                if r.get("isolation_leak"):
                    leaks += 1
                    print("  LEAK  %-22s %s" % (r["instance"], r["isolation_leak"]),
                          flush=True)
                w.writerow(r); fh.flush()
                done += 1
                if done % 10 == 0 or done == len(tasks):
                    el = time.perf_counter() - t0
                    print("  [%3d/%3d] %5.1f min elapsed, ETA %5.1f min"
                          % (done, len(tasks), el / 60,
                             (el / done) * (len(tasks) - done) / 60), flush=True)

    print("\nwritten: %s   pairs %d   errors %d   isolation leaks %d"
          % (dst, done, err, leaks))
    return 1 if (err or leaks) else 0


if __name__ == "__main__":
    sys.exit(main())
