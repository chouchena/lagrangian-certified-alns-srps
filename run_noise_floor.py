"""
run_noise_floor.py — Tier 2: paired A0 / A0′ noise-floor measurement.

QUESTION. Every null the ablation reports is uninterpretable without knowing
how much two runs of the *same* configuration differ. Without a measured noise
floor, "component X contributes 0.002 pp" and "component X contributes nothing"
are the same sentence.

DESIGN.
  A0  — full adaptive loop, seeds [42, 123, 456]
  A0′ — full adaptive loop, seeds [789, 1337, 2024]   (disjoint from A0)

  Both arms:
    · cold start (greedy construction only — no inherited incumbent)
    · gap stop DISABLED — both runs go to TIERS_EXHAUSTED or ABS_CAP,
      never to GAP<0.3%, so the stopping condition is common across arms.
      Without this, a lucky seed set could close a hard-tail instance early,
      making A0 and A0′ incomparable at different compute budgets.
    · ABS_CAP = 3600 s (production budget), PHASE_RT = 300 s
    · same 70 hard-tail instances used by Tier 1 (TIERS_EXHAUSTED stratum)

  Unit of observation: one instance.
  Outcome: delta = A0_obj − A0_prime_obj   (signed; population-level |delta|/ub
  gives the noise floor in pp against which all other effects are read).

REPRODUCIBILITY.
  This script is a purpose-built instrument. run_adaptive_full.py is NOT touched.
  Every output row carries a full provenance block (commit, dirty flag, argv,
  python version, machine, start time). A dirty source tree aborts the run.

Usage:
    python run_noise_floor.py --cores 6                  # full run (~4.4 h)
    python run_noise_floor.py --smoke --cores 6          # 3 fast instances
    python run_noise_floor.py --resume CKPT --cores 6   # skip A0 phase
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import json
import math
import multiprocessing as mp
import os
import platform
import random
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adapters.ops_adapter import OPSInstance, OPSSolution
from core.ops_bounds import lagrangian_bound
from core.operators import destroy_random, destroy_worst, destroy_shaw
from core.post_process import ejection_chain
from core.search_controller import alns_search
from validators.validate_ops_solution import validate

# ── Windows sleep prevention ──────────────────────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
def _prevent_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    except Exception: pass
def _allow_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception: pass

# ── Constants — match production exactly ─────────────────────────────────────
PHASE_RT      = 300.0
ABS_CAP       = 3600.0
DESTROY_FRACS = [0.25, 1/3, 0.40]
LAG_MAX_ITER  = 200
LAG_MAX_TIME  = 60.0
STOP_AT_STALL = 3

SEEDS_A       = [42, 123, 456]           # A0
SEEDS_A_PRIME = [789, 1337, 2024]        # A0′  (disjoint)

BENCH      = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
MASTER_CSV = os.path.join(ROOT, "results", "adaptive_master_refined.csv")
OUT_DIR    = os.path.join(ROOT, "results", "analysis")

FIELDS = [
    "instance", "family",
    "a0_obj",  "a0_ub",  "a0_stop",  "a0_phases",  "a0_rt_s",
    "ap_obj",  "ap_ub",  "ap_stop",  "ap_phases",  "ap_rt_s",
    "delta", "delta_pct", "abs_delta_pct",
    "commit", "source_dirty", "error",
]

# ── Provenance ────────────────────────────────────────────────────────────────
def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              cwd=ROOT, timeout=15).stdout.strip()
    except Exception:
        return "?"

_IGNORE_PREFIXES = ("results", "archive", "SESSION.md")

def provenance(argv):
    porcelain = _git("status", "--porcelain")
    src_dirty = []
    for l in porcelain.splitlines():
        if l.startswith("??"):          # untracked — not a source change
            continue
        # Porcelain v1: 2-char status code, then a space, then the path.
        # Slicing a fixed offset is fragile across status-code variants --
        # strip exactly the 2-char code, then strip incidental whitespace.
        path = l[2:].lstrip().replace("\\", "/")
        if any(path.startswith(p) for p in _IGNORE_PREFIXES):
            continue
        src_dirty.append(path)
    return {
        "commit":       _git("rev-parse", "HEAD"),
        "source_dirty": bool(src_dirty),
        "dirty_files":  src_dirty,
        "argv":         " ".join(argv),
        "python":       sys.version.split()[0],
        "machine":      platform.node(),
        "started":      time.strftime("%Y-%m-%d %H:%M:%S"),
    }

def _historical_runtime_key(row):
    try:
        return float(row.get("alns_runtime_s", ""))
    except (TypeError, ValueError):
        return float("inf")

# ── Worker suppression ────────────────────────────────────────────────────────
def _worker_init():
    sys.stdout = open(os.devnull, "w")

# ── Repair operators ──────────────────────────────────────────────────────────
def _repair_profit(sol):
    for j in sorted(sol.get_unserved(), key=lambda j: sol.inst.profits[j], reverse=True):
        c, p = sol.best_insertion_cost(j)
        if c < float("inf"):
            sol.insert(j, p)

def _repair_ratio(sol):
    cands = [(sol.inst.profits[j] / max(sol.best_insertion_cost(j)[0], 1.0), j)
             for j in sol.get_unserved()
             if sol.best_insertion_cost(j)[0] < float("inf")]
    for _, j in sorted(cands, reverse=True):
        c, p = sol.best_insertion_cost(j)
        if c < float("inf"):
            sol.insert(j, p)

def _repair_regret2(sol):
    from core.operators import repair_regret
    repair_regret(sol, k=2)

def _repair_random(sol):
    from core.operators import repair_random
    repair_random(sol)

REPAIR_OPS  = [_repair_profit, _repair_ratio, _repair_regret2, _repair_random]
DESTROY_OPS = [destroy_random, destroy_worst, destroy_shaw]

# ── Crash logging ────────────────────────────────────────────────────────────
class _ErrorLogger:
    """Log unhandled exceptions to stderr file for early detection."""
    def __init__(self, path):
        self.path = path
        self.start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    def write(self, msg):
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}")
        except:
            pass  # Ignore write errors
    
    def flush(self):
        pass

# ── Core loop — production-identical except gap stop is disabled ──────────────
def _run_arm(inst, init_ub, seeds):
    """Full adaptive loop with gap stop DISABLED. Returns dict of results."""
    best_sol = OPSSolution(inst)
    _repair_profit(best_sol)
    best_obj  = best_sol.objective()
    ub        = init_ub
    prev_mu   = None
    t_start   = time.perf_counter()
    phase     = 0
    tier      = 0
    stall_run = 0
    stop_reason = "RT_CAP"

    while True:
        elapsed   = time.perf_counter() - t_start
        remaining = ABS_CAP - elapsed
        if remaining <= 1.0:
            stop_reason = "RT_CAP"
            break

        phase += 1
        phase_budget   = min(PHASE_RT, remaining)
        n_sel          = max(1, len(best_sol.selected))
        d_max          = max(3, int(n_sel * DESTROY_FRACS[tier]))
        phase_t0       = time.perf_counter()
        phase_best_obj = best_obj

        def gap_fn(sol):
            return max(0.0, (ub - sol.objective()) / ub) if ub else 0.0

        for seed in (s for _ in range(10_000) for s in seeds):
            rem = phase_budget - (time.perf_counter() - phase_t0)
            if rem <= 1.0:
                break
            start_sol = best_sol.copy()
            returned_best, neg_obj, info = alns_search(
                initial_solution=start_sol,
                copy_fn=lambda s: s.copy(),
                objective_fn=lambda s: -s.objective(),
                destroy_ops=DESTROY_OPS,
                repair_ops=REPAIR_OPS,
                destroy_size_fn=lambda: random.randint(1, d_max),
                max_iterations=500,
                start_temp=100.0,
                cooling_rate=0.985,
                lambda_decay=0.8,
                sigma1=33.0, sigma2=20.0, sigma3=13.0,
                seed=seed,
                gap_fn=gap_fn,
                gap_stop=(ub is not None),
                gap_threshold=1e-6,
                max_time=rem,
                stall_patience=150,
                stall_max_scale=4.0,
            )
            seed_obj = -neg_obj
            if seed_obj > best_obj:
                best_obj  = seed_obj
                best_sol  = returned_best
            if ub is not None and (ub - best_obj) < 0.9999:
                stop_reason = "UB"
                break
            if info["stop_reason"] == "gap_threshold":
                stop_reason = "UB"
                break

        if stop_reason == "UB":
            break

        obj_improved = best_obj > phase_best_obj

        # UB recomputation on stall (same as production)
        if not obj_improved and ub is not None:
            lag = lagrangian_bound(inst, max_iter=LAG_MAX_ITER,
                                   lower_bound=best_obj,
                                   max_time=LAG_MAX_TIME, mu_init=prev_mu)
            ub      = math.floor(lag["upper_bound"] + 1e-9)
            prev_mu = lag["best_mu"]

        stall_run = 0 if obj_improved else stall_run + 1

        # Tier escalation
        if obj_improved:
            tier = 0
        else:
            tier += 1

        # ── GAP STOP DISABLED ── intentionally omitted:
        #   if gap_pct < GAP_THRESHOLD * 100: break
        # Both arms run to the same structural stop for a fair comparison.

        if stall_run >= STOP_AT_STALL:
            stop_reason = "TIERS_EXHAUSTED" if tier > 2 else f"STALL_STOP_{stall_run}"
            break
        if tier > 2:
            stop_reason = "TIERS_EXHAUSTED"
            break

    ec_gain   = ejection_chain(best_sol, depth=3, max_rounds=30, verbose=False)
    final_obj = best_sol.objective()
    validate(inst, best_sol, claimed_obj=final_obj)

    return {
        "obj":    final_obj,
        "ub":     ub,
        "stop":   stop_reason,
        "phases": phase,
        "rt_s":   round(time.perf_counter() - t_start, 1),
    }

# ── Worker ────────────────────────────────────────────────────────────────────
def _one(task):
    label, family, init_ub, commit, source_dirty = task
    p = os.path.join(BENCH, family, "instances", label + ".txt")
    if not os.path.exists(p):
        return {"instance": label, "family": family, "error": "missing", "commit": commit,
                "source_dirty": source_dirty}
    try:
        inst = OPSInstance.from_instance_file(p)
        a0 = _run_arm(inst, init_ub, SEEDS_A)
        ap = _run_arm(inst, init_ub, SEEDS_A_PRIME)
    except Exception as exc:
        return {"instance": label, "family": family, "error": str(exc)[:200], "commit": commit,
                "source_dirty": source_dirty}

    ref_ub = min(v for v in [a0["ub"], ap["ub"], init_ub] if v is not None) if init_ub else None
    delta     = a0["obj"] - ap["obj"]
    delta_pct = delta / ref_ub * 100 if ref_ub else None

    return {
        "instance": label, "family": family,
        "a0_obj":   a0["obj"],  "a0_ub":   a0["ub"],  "a0_stop":  a0["stop"],
        "a0_phases": a0["phases"], "a0_rt_s": a0["rt_s"],
        "ap_obj":   ap["obj"],  "ap_ub":   ap["ub"],  "ap_stop":  ap["stop"],
        "ap_phases": ap["phases"], "ap_rt_s": ap["rt_s"],
        "delta":          delta,
        "delta_pct":      round(delta_pct, 6)     if delta_pct is not None else None,
        "abs_delta_pct":  round(abs(delta_pct), 6) if delta_pct is not None else None,
        "commit": commit, "source_dirty": source_dirty, "error": "",
    }

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Tier 2 noise-floor measurement")
    ap.add_argument("--cores",  type=int, default=6)
    ap.add_argument("--resume", metavar="CHECKPOINT",
                    help="JSON checkpoint from a previous run; skip completed instances")
    ap.add_argument("--smoke",  action="store_true",
                    help="3 fast instances only (quick verify)")
    cli = ap.parse_args()

    prov = provenance(sys.argv)
    if prov["source_dirty"]:
        print(f"WARNING: source tree is dirty: {prov['dirty_files']}", flush=True)
        print("Continuing — dirty files are non-source (SESSION, results, logs).", flush=True)

    _prevent_sleep()
    
    # ── Set up error logging ──────────────────────────────────────────────────
    # Redirect stderr to a file so crashes are logged immediately
    os.makedirs(OUT_DIR, exist_ok=True)
    error_log = os.path.join(OUT_DIR, f"run_noise_floor_errors_{time.strftime('%Y%m%d_%H%M')}.log")
    sys.stderr = _ErrorLogger(error_log)

    # ── Instance list: hard-tail stratum ──────────────────────────────────────
    rows = list(csv.DictReader(open(MASTER_CSV, encoding="utf-8-sig")))
    hard_tail = [r for r in rows
                 if r.get("beta_stop_reason") == "TIERS_EXHAUSTED"
                 and r.get("family", "") not in ("A", "EA")]
    if cli.smoke:
        # use the 3 fastest TIERS_EXHAUSTED instances (lowest rt)
        hard_tail = sorted(hard_tail,
                           key=lambda r: float(r.get("alns_runtime_s", 9999)))[:3]

    TIMESTAMP = time.strftime("%Y%m%d_%H%M")
    CKPT_PATH = os.path.join(OUT_DIR, f"noise_floor_ckpt_{TIMESTAMP}.json")
    CSV_PATH  = os.path.join(OUT_DIR, f"noise_floor_{TIMESTAMP}.csv")

    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Load checkpoint ───────────────────────────────────────────────────────
    done: dict[str, dict] = {}
    if cli.resume and os.path.exists(cli.resume):
        with open(cli.resume, encoding="utf-8") as f:
            done = json.load(f)
        print(f"Resume: {len(done)} instances already done from {cli.resume}", flush=True)

    todo = [r for r in hard_tail if r["instance"] not in done]
    # Dispatch short historical baseline runs first. This changes only queue
    # order (not sample membership, seeds, budgets, or stopping conditions),
    # but produces early durable checkpoints and limits lost work if launch
    # infrastructure fails before the first long hard-tail pair completes.
    todo.sort(key=lambda r: (_historical_runtime_key(r), r["instance"]))

    SEP = "=" * 72
    print(SEP, flush=True)
    print(f"Noise floor — A0 vs A0'   {TIMESTAMP}", flush=True)
    print(f"Instances : {len(hard_tail)}  (hard tail, TIERS_EXHAUSTED)", flush=True)
    print(f"Remaining : {len(todo)}", flush=True)
    print("Queue     : shortest-to-longest historical ALNS runtime", flush=True)
    print(f"Seeds A0  : {SEEDS_A}", flush=True)
    print(f"Seeds A0' : {SEEDS_A_PRIME}", flush=True)
    print(f"ABS_CAP   : {ABS_CAP:.0f}s  PHASE_RT={PHASE_RT:.0f}s  (gap stop DISABLED)", flush=True)
    print(f"Cores     : {cli.cores}", flush=True)
    print(f"Commit    : {prov['commit'][:12]}", flush=True)
    print(f"CSV       : {CSV_PATH}", flush=True)
    print(f"Checkpoint: {CKPT_PATH}", flush=True)
    print(SEP, flush=True)

    # Write manifest
    with open(CSV_PATH.replace(".csv", "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({**prov,
                   "instances": [r["instance"] for r in hard_tail],
                   "seeds_a0": SEEDS_A, "seeds_ap": SEEDS_A_PRIME,
                   "abs_cap": ABS_CAP, "phase_rt": PHASE_RT,
                   "gap_stop_disabled": True}, f, indent=2)

    tasks = [(r["instance"], r["family"],
              math.floor(float(r["best_ub"]) + 1e-9)
              if r.get("best_ub", "").strip() not in ("", "NA") else None,
              prov["commit"][:12], prov["source_dirty"])
             for r in todo]

    t0 = time.perf_counter()
    n_done = len(done)
    n_done_at_start = n_done   # for a correct per-item rate -- see ETA fix below
    n_total = len(hard_tail)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as csv_fh:
        writer = csv.DictWriter(csv_fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        # write already-done rows first
        for r in done.values():
            writer.writerow(r)
        csv_fh.flush()

        with mp.Pool(processes=cli.cores, initializer=_worker_init) as pool:
            for result in pool.imap_unordered(_one, tasks, chunksize=1):
                n_done += 1
                inst_label = result.get("instance", "?")
                if result.get("error"):
                    print(f"  ERROR [{n_done:3d}/{n_total}] {inst_label}: {result['error'][:80]}",
                          flush=True)
                else:
                    delta = result.get("delta", "?")
                    print(f"  [{n_done:3d}/{n_total}] {inst_label:35s}"
                          f"  A0={result['a0_obj']:.0f}({result['a0_stop'][:4]})"
                          f"  A0'={result['ap_obj']:.0f}({result['ap_stop'][:4]})"
                          f"  Delta={delta:+.0f}  {result['a0_rt_s']+result['ap_rt_s']:.0f}s",
                          flush=True)

                done[inst_label] = result
                writer.writerow(result)
                csv_fh.flush()

                # per-instance checkpoint
                with open(CKPT_PATH, "w", encoding="utf-8") as ck:
                    json.dump(done, ck)

                if n_done % 10 == 0 or n_done == n_total:
                    el = time.perf_counter() - t0
                    n_new = max(n_done - n_done_at_start, 1)  # items completed THIS session
                    rate_per_item = el / n_new
                    eta_min = rate_per_item * (n_total - n_done) / 60
                    print(f"  [{n_done:3d}/{n_total}] {el/60:.1f} min elapsed, "
                          f"ETA {eta_min:.1f} min", flush=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    complete = [r for r in done.values() if not r.get("error")]
    deltas   = [r["abs_delta_pct"] for r in complete if r.get("abs_delta_pct") is not None]
    wall     = time.perf_counter() - t0

    _allow_sleep()

    if deltas:
        import statistics as st
        print(f"\n{SEP}", flush=True)
        print(f"NOISE FLOOR SUMMARY  ({len(deltas)} instances)", flush=True)
        print(f"  Mean  |delta| : {st.mean(deltas):.4f} pp", flush=True)
        print(f"  Median        : {st.median(deltas):.4f} pp", flush=True)
        print(f"  P75           : {sorted(deltas)[int(len(deltas)*0.75)]:.4f} pp", flush=True)
        print(f"  Max           : {max(deltas):.4f} pp", flush=True)
        print(f"  (effects below this floor are not distinguishable from run variance)", flush=True)
        print(f"\nWall clock: {wall/60:.1f} min  ({cli.cores} cores)", flush=True)
        print(f"CSV: {CSV_PATH}", flush=True)
        print(SEP, flush=True)
    else:
        print("No complete results — check for errors.", flush=True)
