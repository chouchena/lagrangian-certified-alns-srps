"""
run_sensitivity.py — One-at-a-time (OAT) sensitivity analysis for the adaptive ALNS.

Runs a fixed 30-instance stratified subset under a single parameter variation.
All parameters hold their default values except the one specified via --param / --value.

Instance selection rule (documented in §5.1):
  5 instances per family (B/C/D/EB/EC/ED), one per family × n-percentile cell:
    n-levels: 0th, 25th, 50th, 75th, 100th percentile of each family's n-range.
    alpha assigned cyclically: [0.25, 0.50, 0.75, 0.25, 0.50].
    Within each (family, n, alpha) cell: alphabetically first instance.
  Yields equal family representation (5 per family), balanced alpha coverage,
  and full n-range coverage within each family. Total: 30 instances.

Usage:
    python run_sensitivity.py                         # baseline (all defaults)
    python run_sensitivity.py --param gap_threshold --value 0.001
    python run_sensitivity.py --param gap_threshold --value 0.005
    python run_sensitivity.py --param gap_threshold --value 0.010
    python run_sensitivity.py --param destroy_fracs --value tight
    python run_sensitivity.py --param destroy_fracs --value wide
    python run_sensitivity.py --param phase_rt --value 150
    python run_sensitivity.py --param phase_rt --value 450
    python run_sensitivity.py --param lag_max_iter --value 100
    python run_sensitivity.py --param lag_max_iter --value 400
    python run_sensitivity.py --param lag_max_time --value 30
    python run_sensitivity.py --param lag_max_time --value 120
"""
from __future__ import annotations

import argparse
import ctypes
import csv
import math
import multiprocessing as mp
import os
import random
import sys
import time

# ── Windows sleep prevention (same pattern as run_ablation.py) ────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
def _prevent_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    except Exception: pass
def _allow_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from adapters.ops_adapter import OPSInstance, OPSSolution
from core.ops_bounds import lagrangian_bound
from core.operators import destroy_random, destroy_shaw, destroy_worst, repair_random, repair_regret
from core.post_process import ejection_chain
from core.search_controller import alns_search

# ── Default config (matches run_adaptive_full.py) ────────────────────────────
_DEFAULTS = {
    "gap_threshold": 0.003,
    "destroy_fracs": [0.25, 1/3, 0.40],
    "phase_rt":      300.0,
    "lag_max_iter":  200,
    "lag_max_time":  60.0,
}

ABS_CAP   = 1800.0    # shorter cap for sensitivity trials (3 phases max)
N_WORKERS = 6  # fixed campaign-wide (CLAUDE.md: must not vary between experiments)

_prevent_sleep()  # hold off sleep for the duration of this trial
SEEDS     = [42, 123, 456, 789, 1337, 2024]
BENCH     = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
MASTER_CSV = os.path.join("results", "adaptive_master.csv")
OUT_DIR   = os.path.join("results", "sensitivity")

# ── Stratified 30-instance subset ────────────────────────────────────────────
SENSITIVITY_INSTANCES = [
    "B_n100_001_a25_001",   # B n=100 a=0.25 gap=0.09% GAP<0.3%
    "B_n110_006_a50_017",   # B n=110 a=0.50 gap=0.29% GAP<0.3%
    "B_n120_011_a75_033",   # B n=120 a=0.75 gap=0.00% UB
    "B_n140_021_a25_061",   # B n=140 a=0.25 gap=1.66% TIERS_EXHAUSTED
    "B_n150_026_a50_077",   # B n=150 a=0.50 gap=0.18% GAP<0.3%
    "C_n050_001_a25_001",   # C n=50  a=0.25 gap=0.00% GAP<0.3%
    "C_n060_011_a50_032",   # C n=60  a=0.50 gap=0.00% GAP<0.3%
    "C_n065_016_a75_048",   # C n=65  a=0.75 gap=0.00% UB
    "C_n070_021_a25_061",   # C n=70  a=0.25 gap=0.23% GAP<0.3%
    "C_n080_031_a50_092",   # C n=80  a=0.50 gap=0.04% GAP<0.3%
    "D_n040_001_a25_001",   # D n=40  a=0.25 gap=0.00% UB
    "D_n050_011_a50_032",   # D n=50  a=0.50 gap=0.00% UB
    "D_n060_021_a75_063",   # D n=60  a=0.75 gap=0.00% UB
    "D_n070_031_a25_091",   # D n=70  a=0.25 gap=0.00% UB
    "D_n080_041_a50_122",   # D n=80  a=0.50 gap=0.27% GAP<0.3%
    "EB_n100_001_a25_001",  # EB n=100 a=0.25 gap=0.12% GAP<0.3%
    "EB_n110_006_a50_017",  # EB n=110 a=0.50 gap=0.21% GAP<0.3%
    "EB_n120_011_a75_033",  # EB n=120 a=0.75 gap=0.02% GAP<0.3%
    "EB_n140_021_a25_061",  # EB n=140 a=0.25 gap=0.24% GAP<0.3%
    "EB_n150_026_a50_077",  # EB n=150 a=0.50 gap=0.23% GAP<0.3%
    "EC_n050_001_a25_001",  # EC n=50  a=0.25 gap=0.00% UB
    "EC_n060_011_a50_032",  # EC n=60  a=0.50 gap=0.00% UB
    "EC_n065_016_a75_048",  # EC n=65  a=0.75 gap=0.05% GAP<0.3%
    "EC_n070_021_a25_061",  # EC n=70  a=0.25 gap=0.12% GAP<0.3%
    "EC_n080_031_a50_092",  # EC n=80  a=0.50 gap=0.05% GAP<0.3%
    "ED_n040_001_a25_001",  # ED n=40  a=0.25 gap=0.00% UB
    "ED_n050_011_a50_032",  # ED n=50  a=0.50 gap=0.08% GAP<0.3%
    "ED_n060_021_a75_063",  # ED n=60  a=0.75 gap=0.06% GAP<0.3%
    "ED_n070_031_a25_091",  # ED n=70  a=0.25 gap=0.00% UB
    "ED_n080_041_a50_122",  # ED n=80  a=0.50 gap=0.22% GAP<0.3%
]


# ── Parameter parsing ─────────────────────────────────────────────────────────
_DESTROY_FRACS_PRESETS = {
    "tight":   [0.20, 0.28, 0.35],
    "default": [0.25, 1/3,  0.40],
    "wide":    [0.30, 0.40, 0.50],
}


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--param",  default=None,
                        choices=["gap_threshold", "destroy_fracs",
                                 "phase_rt", "lag_max_iter", "lag_max_time"],
                        help="Parameter to vary (omit for baseline)")
    parser.add_argument("--value", default=None,
                        help="Value for the varied parameter")
    return parser.parse_args()


def _resolve_config(param, value_str):
    cfg = dict(_DEFAULTS)
    label = "baseline"
    if param is None:
        return cfg, label

    label = f"{param}={value_str}"
    if param == "gap_threshold":
        cfg["gap_threshold"] = float(value_str)
    elif param == "destroy_fracs":
        if value_str in _DESTROY_FRACS_PRESETS:
            cfg["destroy_fracs"] = _DESTROY_FRACS_PRESETS[value_str]
        else:
            vals = [float(x) for x in value_str.split(",")]
            cfg["destroy_fracs"] = vals
    elif param == "phase_rt":
        cfg["phase_rt"] = float(value_str)
    elif param == "lag_max_iter":
        cfg["lag_max_iter"] = int(value_str)
    elif param == "lag_max_time":
        cfg["lag_max_time"] = float(value_str)
    return cfg, label


# ── Master loader ─────────────────────────────────────────────────────────────
def _load_master():
    m = {}
    with open(MASTER_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            label = r["instance"].strip()
            ub_s  = r.get("best_ub", "").strip()
            bks_s = r.get("bks", "").strip()
            m[label] = {
                "family": r["family"].strip(),
                "ref_obj": float(r["alns_obj"]) if r.get("alns_obj", "").strip() else 0.0,
                "ub":  math.floor(float(ub_s)) if ub_s not in ("", "NA") else None,
                "bks": float(bks_s) if bks_s not in ("", "?", "NA", "") else None,
            }
    return m


# ── Repair helpers ────────────────────────────────────────────────────────────
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

def _repair_regret2(sol): repair_regret(sol, k=2)
def _repair_random(sol):  repair_random(sol)

DESTROY_OPS = [destroy_random, destroy_worst, destroy_shaw]
REPAIR_OPS  = [_repair_profit, _repair_ratio, _repair_regret2, _repair_random]


# ── Per-instance runner ────────────────────────────────────────────────────────
def run_instance(args_tuple):
    label, meta, cfg = args_tuple
    family  = meta["family"]
    ref_obj = meta["ref_obj"]

    GAP_THRESHOLD = cfg["gap_threshold"]
    DESTROY_FRACS = cfg["destroy_fracs"]
    PHASE_RT      = cfg["phase_rt"]
    LAG_MAX_ITER  = cfg["lag_max_iter"]
    LAG_MAX_TIME  = cfg["lag_max_time"]

    ipath = os.path.join(BENCH, family, "instances", label + ".txt")
    inst  = OPSInstance.from_instance_file(ipath)

    # Fresh start — no PKL warm-start (avoids bias from main run incumbents)
    best_sol = OPSSolution(inst)
    _repair_profit(best_sol)
    best_obj = best_sol.objective()

    ub      = meta["ub"]
    prev_mu = None
    t_start = time.perf_counter()
    phase   = 0
    tier    = 0
    stop_reason = "RT_CAP"

    while True:
        elapsed   = time.perf_counter() - t_start
        remaining = ABS_CAP - elapsed
        if remaining <= 1.0:
            stop_reason = "RT_CAP"
            break

        phase += 1
        phase_budget   = min(PHASE_RT, remaining)
        n_sel  = max(1, len(best_sol.selected))
        d_max  = max(3, int(n_sel * DESTROY_FRACS[tier]))

        def gap_fn(sol):
            return max(0.0, (ub - sol.objective()) / ub) if ub else 0.0

        phase_t0      = time.perf_counter()
        phase_best_obj = best_obj

        for _, seed in enumerate(s for _ in range(10_000) for s in SEEDS):
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
                gap_threshold=1e-6,
                gap_stop=(ub is not None),
                max_time=rem,
                stall_patience=150,
                stall_max_scale=4.0,
            )
            seed_obj = -neg_obj
            if seed_obj > best_obj:
                best_obj = seed_obj
                best_sol = returned_best
            if ub is not None and (ub - best_obj) < 0.9999:
                stop_reason = "UB"
                break
            if info["stop_reason"] == "gap_threshold":
                stop_reason = "UB"
                break

        obj_improved = best_obj > phase_best_obj

        if stop_reason == "UB":
            break

        # UB recomputation on stall
        if not obj_improved and ub is not None:
            lag = lagrangian_bound(
                inst,
                max_iter=LAG_MAX_ITER,
                lower_bound=best_obj,
                max_time=LAG_MAX_TIME,
                mu_init=prev_mu,
            )
            ub      = math.floor(lag["upper_bound"])
            prev_mu = lag["best_mu"]

        gap_pct = (ub - best_obj) / ub * 100 if ub else None

        if obj_improved:
            tier = 0
        else:
            tier += 1

        if gap_pct is not None and gap_pct < GAP_THRESHOLD * 100:
            stop_reason = "GAP<threshold"
            break
        if tier > 2:
            stop_reason = "TIERS_EXHAUSTED"
            break

    # EC post-process
    ec_gain   = ejection_chain(best_sol, depth=3, max_rounds=30, verbose=False)
    final_obj = best_sol.objective()
    total_rt  = time.perf_counter() - t_start
    final_gap = (ub - final_obj) / ub * 100 if ub else None

    return {
        "instance":   label,
        "family":     family,
        "ref_obj":    ref_obj,
        "final_obj":  final_obj,
        "delta_ref":  final_obj - ref_obj,
        "final_gap_pct": round(final_gap, 6) if final_gap is not None else None,
        "ec_gain":    ec_gain,
        "phases":     phase,
        "stop_reason": stop_reason,
        "total_rt_s": round(total_rt, 1),
    }


def _worker_init():
    sys.stdout = open(os.devnull, "w")

def _run_task(args):
    return run_instance(args)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args_parsed = _parse_args()
    cfg, run_label = _resolve_config(args_parsed.param, args_parsed.value)

    TIMESTAMP = time.strftime("%Y%m%d_%H%M")
    os.makedirs(OUT_DIR, exist_ok=True)
    OUT_CSV = os.path.join(OUT_DIR, f"sensitivity_{run_label.replace('=','_')}_{TIMESTAMP}.csv")

    master = _load_master()
    tasks = [
        (label, master[label], cfg)
        for label in SENSITIVITY_INSTANCES
        if label in master
    ]

    print("=" * 72)
    print(f"Sensitivity trial: {run_label}")
    print(f"  gap_threshold : {cfg['gap_threshold']*100:.2f}%")
    print(f"  destroy_fracs : {[round(f,3) for f in cfg['destroy_fracs']]}")
    print(f"  phase_rt      : {cfg['phase_rt']:.0f}s  (ABS_CAP={ABS_CAP:.0f}s)")
    print(f"  lag_max_iter  : {cfg['lag_max_iter']}")
    print(f"  lag_max_time  : {cfg['lag_max_time']:.0f}s")
    print(f"Instances: {len(tasks)} | Workers: {N_WORKERS}")
    print(f"Output: {OUT_CSV}")
    print("=" * 72)

    results = []
    t_wall  = time.perf_counter()

    with mp.Pool(processes=N_WORKERS, initializer=_worker_init) as pool:
        for r in pool.imap_unordered(_run_task, tasks, chunksize=1):
            results.append(r)
            gap_s = f"{r['final_gap_pct']:.4f}%" if r['final_gap_pct'] is not None else "N/A"
            print(f"  {r['instance']:35s}  gap={gap_s:8s}  rt={r['total_rt_s']:6.0f}s"
                  f"  stop={r['stop_reason']}", flush=True)

    wall = time.perf_counter() - t_wall

    # Write CSV
    fields = ["instance","family","ref_obj","final_obj","delta_ref",
              "final_gap_pct","ec_gain","phases","stop_reason","total_rt_s"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    # Summary
    gaps = [r["final_gap_pct"] for r in results if r["final_gap_pct"] is not None]
    mean_gap = sum(gaps)/len(gaps) if gaps else 0.0
    max_gap  = max(gaps) if gaps else 0.0
    ub_n  = sum(1 for r in results if r["stop_reason"] == "UB")
    gap_n = sum(1 for r in results if r["stop_reason"] == "GAP<threshold")
    te_n  = sum(1 for r in results if r["stop_reason"] == "TIERS_EXHAUSTED")
    rt_n  = sum(1 for r in results if r["stop_reason"] == "RT_CAP")

    print("\n" + "=" * 72)
    print(f"  Trial: {run_label}  |  {len(results)} instances  |  wall={wall/60:.1f} min")
    print(f"  gap mean={mean_gap:.4f}%  max={max_gap:.4f}%")
    print(f"  Stop: UB={ub_n}  GAP<thr={gap_n}  TIERS_EX={te_n}  RT_CAP={rt_n}")
    print(f"  -> {OUT_CSV}")
    print("=" * 72)
