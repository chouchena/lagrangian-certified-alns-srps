"""
run_ablation.py — Ablation study for the adaptive-loop ALNS (SRPS-ALNS paper §5.4).

Redesigned per docs/ABLATION_DESIGN.md. Supersedes the old A0–A5 design
(stopped mid-run 2026-08-27), which had three measured defects: it could not
discriminate between arms on 29/30 instances, never tested the adaptivity
mechanism itself, and scored two arms against a bound they had removed the
machinery to produce.

Design summary:
  - 40 instances, common to every arm, stratified 20 hard-tail
    (beta_stop_reason == TIERS_EXHAUSTED) + 20 closing multi-phase
    (beta_stop_reason == GAP<0.3%, beta_phases > 1). Single-phase instances
    are excluded — every arm is identical on them by construction.
  - Bounds are FIXED from results/bounds_certified.csv (final_ub). No arm
    computes its own initial bound; no two-phase warm-mu protocol.
  - 10 configurations: A0 (full method) + B1–B8 (each isolates one feature)
    + S (all of B1–B8 simultaneously, for the total-value / redundancy check).
  - Two gaps reported per arm-instance: cert_gap_pct (against the common
    fixed bound — the PRIMAL effect) and cert_gap_own_pct (against the arm's
    own final bound — the CERTIFICATE effect; only meaningful for B7).
  - Reporting is STRATIFIED, NEVER POOLED. B6/B7 cannot act on the closing
    stratum by construction — averaging across strata would dilute a
    hard-tail-only mechanism to near-zero, exactly as happened to tier
    escalation under the old design.

Arms:
  A0  full method                          baseline
  B1  uniform operator choice              lambda_decay=1.0 (adaptive weights off)
  B2  greedy acceptance                    accept_worse=False (SA off)
  B3  destroy_random only                  destroy diversity off
  B4  _repair_profit only                  repair diversity off
  B5  no ejection chain                    post-loop improvement off
  B6  no tier escalation                   destroy-size adaptation off
  B7  no in-loop re-bound                  dual refresh on stall off
  B8  single seed                          multi-start off
  S   all of B1–B8 simultaneously          total value of the apparatus

Usage:
    python run_ablation.py [--cores N] [--resume CHECKPOINT] [--smoke]
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
from datetime import datetime

# ── Windows sleep prevention ──────────────────────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

def _prevent_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    except Exception:
        pass

def _allow_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from adapters.ops_adapter import OPSInstance, OPSSolution
from core.ops_bounds import lagrangian_bound
from core.operators import destroy_random, destroy_worst, destroy_shaw, repair_random, repair_regret
from core.post_process import ejection_chain
from core.search_controller import alns_search
from validators.validate_ops_solution import validate

# ── Constants ─────────────────────────────────────────────────────────────────
ABS_CAP    = 3600.0     # aligned to main campaign (doc: no discriminating instance exceeds this)
PHASE_RT   = 300.0
SEEDS_FULL   = [42, 123, 456, 789, 1337, 2024]
SEEDS_SINGLE = [42]
N_PER_STRATUM = 20      # 20 hard-tail + 20 closing = 40 total
SAMPLE_SEED   = 20260828  # fixed seed for reproducible stratified sampling

BENCH       = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
MASTER_CSV  = os.path.join("results", "adaptive_master.csv")
BOUNDS_CSV  = os.path.join("results", "bounds_certified.csv")
OUT_DIR     = os.path.join("results", "analysis")

_CFG = {
    "gap_threshold": 0.003,
    "destroy_fracs": [0.25, 1/3, 0.40],
    "phase_rt":      PHASE_RT,
    "lag_max_iter":  200,
    "lag_max_time":  60.0,
    "abs_cap":       ABS_CAP,
}

# ── Arm definitions ───────────────────────────────────────────────────────────
_B_FLAGS = {
    "B1": {"uniform_ops": True},
    "B2": {"greedy_accept": True},
    "B3": {"destroy_random_only": True},
    "B4": {"repair_profit_only": True},
    "B5": {"no_ejection": True},
    "B6": {"no_tier_escalation": True},
    "B7": {"no_ub_refresh": True},
    "B8": {"single_seed": True},
}
_S_FLAGS = {}
for _f in _B_FLAGS.values():
    _S_FLAGS.update(_f)

ARMS = [
    {"id": "A0", "label": "full method",                  "flags": {}},
    {"id": "B1", "label": "uniform operator choice",       "flags": _B_FLAGS["B1"]},
    {"id": "B2", "label": "greedy acceptance",             "flags": _B_FLAGS["B2"]},
    {"id": "B3", "label": "destroy_random only",           "flags": _B_FLAGS["B3"]},
    {"id": "B4", "label": "repair_profit only",            "flags": _B_FLAGS["B4"]},
    {"id": "B5", "label": "no ejection chain",             "flags": _B_FLAGS["B5"]},
    {"id": "B6", "label": "no tier escalation",            "flags": _B_FLAGS["B6"]},
    {"id": "B7", "label": "no in-loop re-bound",           "flags": _B_FLAGS["B7"]},
    {"id": "B8", "label": "single seed",                   "flags": _B_FLAGS["B8"]},
    {"id": "S",  "label": "all of B1-B8 (total apparatus)", "flags": _S_FLAGS},
]
ARM_MAP = {a["id"]: a for a in ARMS}


# ── Provenance ─────────────────────────────────────────────────────────────────
_IGNORE_PREFIXES = ("SESSION", "results/", "results\\", "*.log", "nag_prompt")

def _git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           timeout=15, cwd=os.path.dirname(os.path.abspath(__file__)))
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""

def provenance(argv):
    porcelain = _git("status", "--porcelain")
    src_dirty = []
    for l in porcelain.splitlines():
        if l.startswith("??"):          # untracked — not a source change
            continue
        # Porcelain v1: 2-char status code, then a space, then the path.
        # Slicing a fixed offset is fragile across status-code variants —
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


# ── Master / bounds loaders ────────────────────────────────────────────────────
def _load_master():
    m = {}
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            label = r["instance"].strip()
            m[label] = {
                "family":            r["family"].strip(),
                "n":                 r.get("n", "").strip(),
                "alpha":             r.get("alpha", "").strip(),
                "beta_stop_reason":  r.get("beta_stop_reason", "").strip(),
                "beta_phases":       r.get("beta_phases", "").strip(),
                "alns_runtime_s":    r.get("alns_runtime_s", "").strip(),
            }
    return m

def _load_bounds():
    b = {}
    with open(BOUNDS_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            label = r["instance"].strip()
            ub_s  = r.get("final_ub", "").strip()
            if ub_s not in ("", "NA"):
                b[label] = math.floor(float(ub_s) + 1e-9)
    return b


def _historical_runtime_key(meta):
    try:
        return float(meta.get("alns_runtime_s", ""))
    except (TypeError, ValueError):
        return float("inf")


def _select_sample(master, bounds):
    """Stratified 20 hard-tail + 20 closing sample, per docs/ABLATION_DESIGN.md.

    Membership: beta_stop_reason == 'TIERS_EXHAUSTED' (hard tail, of 70) or
    beta_stop_reason == 'GAP<0.3%' and beta_phases > 1 (closing, of 198).
    Single-phase closers are excluded — every arm is identical there.
    Selection is a fixed-seed random sample within each stratum (structural
    properties only; membership does not depend on any arm's result).
    """
    hard_pool  = sorted(lbl for lbl, m in master.items()
                        if m["beta_stop_reason"] == "TIERS_EXHAUSTED" and lbl in bounds)
    close_pool = sorted(lbl for lbl, m in master.items()
                        if m["beta_stop_reason"] == "GAP<0.3%"
                        and m["beta_phases"] not in ("", "0", "1")
                        and lbl in bounds)

    rng = random.Random(SAMPLE_SEED)
    hard_sample  = sorted(rng.sample(hard_pool, min(N_PER_STRATUM, len(hard_pool))))
    close_sample = sorted(rng.sample(close_pool, min(N_PER_STRATUM, len(close_pool))))

    sample = [(lbl, "hard_tail") for lbl in hard_sample] + \
             [(lbl, "closing")   for lbl in close_sample]
    return sample, len(hard_pool), len(close_pool)


# ── Worker stdout suppression ─────────────────────────────────────────────────
def _worker_init():
    sys.stdout = open(os.devnull, "w")


# ── Core adaptive loop (shared by every arm) ──────────────────────────────────
def _adaptive_loop(inst, ub_init, cfg, flags):
    """
    Run the adaptive ALNS loop on `inst` with optional ablation flags.

    flags: dict with any of:
      'uniform_ops'         — B1: lambda_decay=1.0 (adaptive weights frozen at
                               initial [1.0]*k; roulette_select over equal
                               weights is uniform selection)
      'greedy_accept'       — B2: accept_worse=False (no SA acceptance)
      'destroy_random_only' — B3: destroy pool -> [destroy_random]
      'repair_profit_only'  — B4: repair pool -> [_repair_profit]
      'no_ejection'         — B5: skip post-loop ejection chain
      'no_tier_escalation'  — B6: tier stays 0; TIERS_EXHAUSTED never fires
      'no_ub_refresh'       — B7: skip Lagrangian re-bound on stall
      'single_seed'         — B8: use only seeds=[42]

    Returns dict: final_obj, loop_final_ub, stop_reason, phases, ec_gain,
    total_rt_s, seeds_used, best_seed, n_seed_restarts, tier_final,
    stall_run_final.
    """
    GAP_THRESHOLD = cfg["gap_threshold"]
    DESTROY_FRACS = cfg["destroy_fracs"]
    PHASE_RT_     = cfg["phase_rt"]
    LAG_MAX_ITER  = cfg["lag_max_iter"]
    LAG_MAX_TIME  = cfg["lag_max_time"]
    ABS_CAP_      = cfg["abs_cap"]

    seeds = SEEDS_SINGLE if flags.get("single_seed") else SEEDS_FULL
    lambda_decay = 1.0 if flags.get("uniform_ops") else 0.8
    accept_worse = not flags.get("greedy_accept")

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

    if flags.get("repair_profit_only"):
        repair_ops = [_repair_profit]
    else:
        repair_ops = [_repair_profit, _repair_ratio, _repair_regret2, _repair_random]

    if flags.get("destroy_random_only"):
        destroy_ops = [destroy_random]
    else:
        destroy_ops = [destroy_random, destroy_worst, destroy_shaw]

    best_sol = OPSSolution(inst)
    _repair_profit(best_sol)
    best_obj = best_sol.objective()

    ub        = ub_init
    prev_mu   = None
    t_start   = time.perf_counter()
    phase     = 0
    tier      = 0
    stall_run = 0
    stop_reason = "RT_CAP"
    best_seed = None
    n_seed_restarts = 0

    while True:
        elapsed   = time.perf_counter() - t_start
        remaining = ABS_CAP_ - elapsed
        if remaining <= 1.0:
            stop_reason = "RT_CAP"
            break

        phase += 1
        phase_budget = min(PHASE_RT_, remaining)
        n_sel  = max(1, len(best_sol.selected))
        d_max  = max(3, int(n_sel * DESTROY_FRACS[tier]))

        def gap_fn(sol):
            return max(0.0, (ub - sol.objective()) / ub) if ub else 0.0

        phase_t0       = time.perf_counter()
        phase_best_obj = best_obj

        for _, seed in enumerate(s for _ in range(10_000) for s in seeds):
            rem = phase_budget - (time.perf_counter() - phase_t0)
            if rem <= 1.0:
                break
            start_sol = best_sol.copy()
            returned_best, neg_obj, info = alns_search(
                initial_solution=start_sol,
                copy_fn=lambda s: s.copy(),
                objective_fn=lambda s: -s.objective(),
                destroy_ops=destroy_ops,
                repair_ops=repair_ops,
                destroy_size_fn=lambda: random.randint(1, d_max),
                max_iterations=500,
                start_temp=100.0,
                cooling_rate=0.985,
                lambda_decay=lambda_decay,
                sigma1=33.0, sigma2=20.0, sigma3=13.0,
                seed=seed,
                gap_fn=gap_fn,
                gap_threshold=1e-6,
                gap_stop=(ub is not None),
                max_time=rem,
                stall_patience=150,
                stall_max_scale=4.0,
                accept_worse=accept_worse,
            )
            seed_obj = -neg_obj
            n_seed_restarts += 1
            if seed_obj > best_obj:
                best_obj = seed_obj
                best_sol = returned_best
                best_seed = seed
            if ub is not None and (ub - best_obj) < 0.9999:
                stop_reason = "UB"
                break
            if info["stop_reason"] == "gap_threshold":
                stop_reason = "UB"
                break

        obj_improved = best_obj > phase_best_obj
        stall_run = 0 if obj_improved else stall_run + 1

        if stop_reason == "UB":
            break

        if not flags.get("no_ub_refresh") and not obj_improved and ub is not None:
            lag = lagrangian_bound(
                inst,
                max_iter=LAG_MAX_ITER,
                lower_bound=best_obj,
                max_time=LAG_MAX_TIME,
                mu_init=prev_mu,
            )
            ub      = math.floor(lag["upper_bound"] + 1e-9)
            prev_mu = lag["best_mu"]

        gap_pct = (ub - best_obj) / ub * 100 if ub else None

        if obj_improved:
            tier = 0
        elif not flags.get("no_tier_escalation"):
            tier += 1

        if gap_pct is not None and gap_pct < GAP_THRESHOLD * 100:
            stop_reason = "GAP<threshold"
            break
        # Stall exit is independent of the destroy ladder (production parity):
        # without it, an arm that disables tier escalation has no stall exit
        # and runs to ABS_CAP on exactly the stratum defined by hitting that
        # exit, confounding the mechanism with the compute it is then given.
        if stall_run >= 3:
            stop_reason = "STALL_STOP"
            break
        if not flags.get("no_tier_escalation") and tier > 2:
            stop_reason = "TIERS_EXHAUSTED"
            break

    if flags.get("no_ejection"):
        ec_gain = 0
    else:
        ec_gain = ejection_chain(best_sol, depth=3, max_rounds=30, verbose=False)
    final_obj = best_sol.objective()

    validate(inst, best_sol, claimed_obj=final_obj)

    return {
        "final_obj":       final_obj,
        "loop_final_ub":   ub,
        "stop_reason":     stop_reason,
        "phases":          phase,
        "ec_gain":         ec_gain,
        "total_rt_s":      round(time.perf_counter() - t_start, 1),
        "seeds_used":      ",".join(str(s) for s in seeds),
        "best_seed":       best_seed,
        "n_seed_restarts": n_seed_restarts,
        "tier_final":      tier,
        "stall_run_final": stall_run,
    }


# ── Worker ─────────────────────────────────────────────────────────────────────
def _worker(job):
    """One (instance, arm) job against the fixed certified bound."""
    import traceback as _tb
    label, meta, stratum, cfg, arm_id, flags, ub_fixed, prov = job
    try:
        family = meta["family"]
        ipath  = os.path.join(BENCH, family, "instances", label + ".txt")
        inst   = OPSInstance.from_instance_file(ipath)

        r = _adaptive_loop(inst, ub_init=ub_fixed, cfg=cfg, flags=flags)

        final_obj = r["final_obj"]
        cert_gap  = (max(0.0, (ub_fixed - final_obj) / ub_fixed * 100)
                     if ub_fixed else None)

        own_ub  = r.get("loop_final_ub")
        gap_own = (max(0.0, (own_ub - final_obj) / own_ub * 100)
                   if own_ub else None)

        return {
            "label": label, "family": family, "stratum": stratum,
            "arm_id": arm_id, "error": None,
            "best_ub": ub_fixed, "obj": final_obj, "cert_gap_pct": cert_gap,
            "own_ub": own_ub, "cert_gap_own_pct": gap_own,
            "stop_reason": r["stop_reason"], "phases": r["phases"],
            "ec_gain": r["ec_gain"], "total_rt_s": r["total_rt_s"],
            "seeds_used": r["seeds_used"], "best_seed": r["best_seed"],
            "n_seed_restarts": r["n_seed_restarts"],
            "tier_final": r["tier_final"], "stall_run_final": r["stall_run_final"],
            "commit": prov["commit"], "source_dirty": prov["source_dirty"],
        }
    except Exception:
        return {
            "label": label, "family": meta.get("family", "?"), "stratum": stratum,
            "arm_id": arm_id, "error": _tb.format_exc(),
            "best_ub": ub_fixed, "obj": None, "cert_gap_pct": None,
            "own_ub": None, "cert_gap_own_pct": None,
            "stop_reason": "ERROR", "phases": 0, "ec_gain": 0, "total_rt_s": 0.0,
            "seeds_used": "", "best_seed": None, "n_seed_restarts": 0,
            "tier_final": None, "stall_run_final": None,
            "commit": prov["commit"], "source_dirty": prov["source_dirty"],
        }


# ── Summary statistics ────────────────────────────────────────────────────────
def _arm_stats(gaps):
    if not gaps:
        return {}
    g = sorted(gaps)
    n = len(g)
    return {
        "mean":   sum(g) / n,
        "median": g[n // 2],
        "p75":    g[int(n * 0.75)],
        "max":    g[-1],
        "n":      n,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive-loop ablation study (B1-B8 + S)")
    parser.add_argument("--cores", type=int, default=os.cpu_count(),
                        help="Parallel workers (default: all CPU cores)")
    parser.add_argument("--resume", metavar="CHECKPOINT",
                        help="Path to a checkpoint JSON; skip already-completed (instance, arm) jobs")
    parser.add_argument("--smoke", action="store_true",
                        help="Quick test: 4 instances (2 hard-tail + 2 closing), all 10 arms, ABS_CAP=60s")
    _args = parser.parse_args()
    N_WORKERS = max(1, _args.cores)

    _prevent_sleep()
    PROV = provenance(sys.argv)

    # On --resume, reuse the ORIGINAL run's timestamp (parsed from the
    # checkpoint filename) so the CSV is genuinely appended to, not
    # fragmented into a new file every time a run is interrupted and
    # resumed. Without this, each restart over a long unattended run would
    # split results across multiple CSVs with no automatic merge, and the
    # final stratified summary would silently reflect only the last
    # invocation's partial data.
    if _args.resume:
        _resume_base = os.path.basename(_args.resume)
        _prefix, _suffix = "ablation_b1b8s_ckpt_", ".json"
        if _resume_base.startswith(_prefix) and _resume_base.endswith(_suffix):
            TIMESTAMP = _resume_base[len(_prefix):-len(_suffix)]
        else:
            TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")
            print(f"WARNING: --resume checkpoint name doesn't match the expected "
                  f"pattern; cannot recover the original timestamp. Starting a "
                  f"NEW CSV ({TIMESTAMP}) -- results will be split across files.")
    else:
        TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(OUT_DIR, exist_ok=True)
    CSV_PATH  = os.path.join(OUT_DIR, f"ablation_b1b8s_{TIMESTAMP}.csv")
    CKPT_PATH = os.path.join(OUT_DIR, f"ablation_b1b8s_ckpt_{TIMESTAMP}.json")

    master = _load_master()
    bounds = _load_bounds()
    sample, n_hard_pool, n_close_pool = _select_sample(master, bounds)

    arms_to_run = ARMS
    smoke_cfg = dict(_CFG)
    if _args.smoke:
        smoke_cfg["abs_cap"] = 60.0
        ABS_CAP = 60.0  # display only
        hard_two  = [(lbl, s) for lbl, s in sample if s == "hard_tail"][:2]
        close_two = [(lbl, s) for lbl, s in sample if s == "closing"][:2]
        sample = hard_two + close_two
        # All 10 arms, not a subset — B2/B3/B4/B5/S are the newest, least-
        # tested code paths and must be exercised before a real 20h launch.

    n_inst = len(sample)
    n_arms = len(arms_to_run)

    SEP = "=" * 80
    header = (
        f"Ablation study (B1-B8 + S) — adaptive-loop ALNS  —  {TIMESTAMP}\n"
        f"Instances    : {n_inst}  "
        f"(hard-tail pool={n_hard_pool}, closing pool={n_close_pool}, sample seed={SAMPLE_SEED})\n"
        f"Arms         : {n_arms}\n"
        f"ABS_CAP      : {ABS_CAP:.0f}s per instance per arm\n"
        f"Cores        : {N_WORKERS}\n"
        f"Smoke        : {_args.smoke}\n"
        f"Resume       : {_args.resume or 'no'}\n"
        f"Commit       : {PROV['commit'][:12]}\n"
        f"Source dirty : {PROV['source_dirty']}\n"
        f"Output CSV   : {CSV_PATH}\n"
        f"Checkpoint   : {CKPT_PATH}\n"
    )
    print(SEP)
    print(header)
    print(SEP)

    if PROV["source_dirty"]:
        print(f"WARNING: source tree is dirty: {PROV['dirty_files']}")
        print("Continuing — dirty files are non-source (SESSION, results, logs).")

    # ── Build job list ─────────────────────────────────────────────────────────
    done_keys = set()
    if _args.resume and os.path.exists(_args.resume):
        with open(_args.resume, encoding="utf-8") as f:
            done_keys = set(tuple(k) for k in json.load(f))
        print(f"Resume: {len(done_keys)} (instance, arm) jobs already done from {_args.resume}")

    jobs = []
    for label, stratum in sample:
        meta = master[label]
        ub_fixed = bounds[label]
        for arm in arms_to_run:
            if (label, arm["id"]) in done_keys:
                continue
            jobs.append((label, meta, stratum, smoke_cfg, arm["id"], arm["flags"], ub_fixed, PROV))

    # Historical runtime orders dispatch only. The fixed stratified sample,
    # arm definitions, seeds, bounds, and per-job algorithm remain unchanged.
    # Short jobs first provide prompt persisted evidence before long jobs.
    jobs.sort(key=lambda job: (_historical_runtime_key(job[1]), job[0], job[4]))

    print(f"\n{len(jobs)} jobs queued ({n_inst} instances x {n_arms} arms, "
          f"minus {len(done_keys)} already done)\n")
    print("Queue order: shortest-to-longest historical ALNS runtime\n")

    fields = ["family", "instance", "stratum", "arm_id", "best_ub", "obj",
              "cert_gap_pct", "own_ub", "cert_gap_own_pct", "stop_reason",
              "phases", "ec_gain", "total_rt_s", "seeds_used", "best_seed",
              "n_seed_restarts", "tier_final", "stall_run_final",
              "commit", "source_dirty", "error"]

    write_header = not (_args.resume and os.path.exists(CSV_PATH))
    results: list[dict] = []

    # On resume, load previously-completed rows so the final stratified
    # summary reflects the FULL dataset (all invocations), not just whatever
    # ran in this particular process. Without this, a summary printed after
    # any restart would silently understate n and misreport every stat.
    if _args.resume and os.path.exists(CSV_PATH):
        with open(CSV_PATH, encoding="utf-8-sig") as _f:
            for _row in csv.DictReader(_f):
                _cg = _row.get("cert_gap_pct", "")
                results.append({
                    "label": _row["instance"], "family": _row["family"],
                    "stratum": _row["stratum"], "arm_id": _row["arm_id"],
                    "cert_gap_pct": float(_cg) if _cg not in ("", None) else None,
                    "error": _row.get("error") or None,
                })
        print(f"Loaded {len(results)} previously-completed rows from {CSV_PATH} "
              f"for the final summary")

    t0 = time.perf_counter()
    n_done = 0

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as _csv_fh:
        _csv_w = csv.DictWriter(_csv_fh, fieldnames=fields, extrasaction="ignore")
        if write_header:
            _csv_w.writeheader()
            _csv_fh.flush()

        with mp.Pool(processes=N_WORKERS, initializer=_worker_init) as pool:
            for r in pool.imap_unordered(_worker, jobs, chunksize=1):
                n_done += 1
                done_keys.add((r["label"], r["arm_id"]))
                if r.get("error"):
                    print(f"  ERROR [{n_done:3d}/{len(jobs)}] [{r['arm_id']}] "
                          f"{r['label']}: {r['error'][:150]}", flush=True)
                else:
                    cert_s = f"{r['cert_gap_pct']:.4f}%" if r["cert_gap_pct"] is not None else "N/A"
                    print(f"  [{n_done:3d}/{len(jobs)}] {r['arm_id']:3s} {r['stratum']:9s} "
                          f"{r['label']:35s}  cert={cert_s:8s}  rt={r['total_rt_s']:6.0f}s"
                          f"  stop={r['stop_reason']}", flush=True)
                results.append(r)
                _csv_w.writerow({
                    "family":           r["family"],
                    "instance":         r["label"],
                    "stratum":          r["stratum"],
                    "arm_id":           r["arm_id"],
                    "best_ub":          f"{r['best_ub']:.4f}" if r.get("best_ub") else "",
                    "obj":              r.get("obj", ""),
                    "cert_gap_pct":     f"{r['cert_gap_pct']:.6f}" if r.get("cert_gap_pct") is not None else "",
                    "own_ub":           f"{r['own_ub']:.4f}" if r.get("own_ub") else "",
                    "cert_gap_own_pct": f"{r['cert_gap_own_pct']:.6f}" if r.get("cert_gap_own_pct") is not None else "",
                    "stop_reason":      r.get("stop_reason", ""),
                    "phases":           r.get("phases", ""),
                    "ec_gain":          r.get("ec_gain", ""),
                    "total_rt_s":       r.get("total_rt_s", ""),
                    "seeds_used":       r.get("seeds_used", ""),
                    "best_seed":        r.get("best_seed", ""),
                    "n_seed_restarts":  r.get("n_seed_restarts", ""),
                    "tier_final":       r.get("tier_final", ""),
                    "stall_run_final":  r.get("stall_run_final", ""),
                    "commit":           r["commit"],
                    "source_dirty":     r["source_dirty"],
                    "error":            r.get("error", "") or "",
                })
                _csv_fh.flush()
                with open(CKPT_PATH, "w", encoding="utf-8") as _cf:
                    json.dump(sorted(done_keys), _cf)

    wall = time.perf_counter() - t0
    n_err = sum(1 for r in results if r.get("error"))
    print(f"\nDone — {wall/60:.1f} min  ({n_err} errors)")

    # ── Stratified summary (never pooled) ─────────────────────────────────────
    for stratum in ("hard_tail", "closing"):
        strat_results = [r for r in results if r["stratum"] == stratum]
        if not strat_results:
            continue
        arm_gaps = {a["id"]: [] for a in arms_to_run}
        for r in strat_results:
            if r.get("cert_gap_pct") is not None:
                arm_gaps[r["arm_id"]].append(r["cert_gap_pct"])
        stats = {aid: _arm_stats(g) for aid, g in arm_gaps.items()}
        a0_mean = stats.get("A0", {}).get("mean")

        print(f"\n{SEP}")
        print(f"STRATUM: {stratum}  (n_instances={len(set(r['label'] for r in strat_results))})")
        print(SEP)
        print(f"{'Arm':4s}  {'Description':32s}  {'Mean%':>8}  {'Med%':>8}  {'P75%':>8}  {'Max%':>8}  {'D_A0':>9}")
        print("-" * 90)
        for arm in arms_to_run:
            st = stats.get(arm["id"], {})
            if not st:
                print(f"{arm['id']:4s}  {arm['label']:32s}  (no results)")
                continue
            delta = st["mean"] - a0_mean if a0_mean is not None else float("nan")
            print(f"{arm['id']:4s}  {arm['label']:32s}  {st['mean']:>8.4f}%"
                  f"  {st['median']:>8.4f}%  {st['p75']:>8.4f}%  {st['max']:>8.4f}%  {delta:>+9.4f}%")

        # marginal / total diagnostic
        marginals = {aid: (stats[aid]["mean"] - a0_mean)
                     for aid in [a["id"] for a in arms_to_run if a["id"].startswith("B")]
                     if aid in stats and a0_mean is not None}
        if "S" in stats and a0_mean is not None and marginals:
            total = stats["S"]["mean"] - a0_mean
            sum_marginal = sum(marginals.values())
            print(f"\n  sum(marginal B1-B8) = {sum_marginal:+.4f}%   total (S - A0) = {total:+.4f}%")
            if abs(sum_marginal) > 1e-9:
                print(f"  ratio total/sum_marginal = {total/sum_marginal:.3f}  "
                      f"({'redundant components' if abs(total) < abs(sum_marginal) else 'independent/compounding'})")

    print(f"\nAll rows written incrementally to: {CSV_PATH}")
    print(f"Checkpoint (for --resume): {CKPT_PATH}")

    _allow_sleep()
