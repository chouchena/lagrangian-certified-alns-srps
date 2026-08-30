"""
run_campaign.py — Master runner: ablation → sensitivity pipeline.

Runs both stages in sequence. Each is independently resumable:
  - Ablation:     resumes from Phase 1 checkpoint if one exists
  - Sensitivity:  skips any trial whose CSV already exists (idempotent)

Sleep/hibernate is prevented for the full duration via SetThreadExecutionState.
All output is written to results/campaign_<timestamp>.log as well as stdout,
so the run is recoverable even if the terminal is closed.

Launch in a STANDALONE PowerShell window (not VS Code terminal) so a VS Code
crash cannot kill it:

    Start-Process powershell -ArgumentList '-NoExit -Command "cd ''C:\\...\\Full_SRPS-ALNS''; python run_campaign.py --cores 6 *>&1 | Tee-Object results/campaign_run.log"'

Or simply:
    python run_campaign.py --cores 6
"""
from __future__ import annotations

import argparse
import ctypes
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# ── Sleep prevention ──────────────────────────────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

def _prevent_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    except Exception: pass

def _allow_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception: pass


def _latest_checkpoint():
    """Return path to most recent Phase 1 checkpoint, or None."""
    pattern = os.path.join(ROOT, "results", "analysis", "ablation_phase1_*.json")
    hits = sorted(glob.glob(pattern))
    return hits[-1] if hits else None


def _ablation_already_complete():
    """True if a Phase 2 CSV with >30 rows (header + A0 + 5 arms × 30 = 181 rows min) exists."""
    pattern = os.path.join(ROOT, "results", "analysis", "ablation_warmmu_*.csv")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, encoding="utf-8") as f:
                if sum(1 for _ in f) >= 31:   # at least header + 30 A0 rows
                    return True
        except Exception:
            pass
    return False


def run(cmd, label):
    print(f"\n{'='*72}", flush=True)
    print(f"STAGE: {label}", flush=True)
    print(f"CMD  : {' '.join(cmd)}", flush=True)
    print(f"START: {time.strftime('%H:%M:%S')}", flush=True)
    print('='*72, flush=True)
    t0 = time.perf_counter()
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    elapsed = time.perf_counter() - t0
    status = "OK" if rc == 0 else f"FAILED (exit={rc})"
    print(f"\n{label}: {status}  ({elapsed/60:.1f} min)", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=int, default=6)
    ap.add_argument("--skip-ablation",    action="store_true", help="Jump straight to sensitivity")
    ap.add_argument("--skip-sensitivity", action="store_true", help="Run ablation only")
    args = ap.parse_args()

    _prevent_sleep()
    print(f"Campaign started {time.strftime('%Y-%m-%d %H:%M:%S')}  |  cores={args.cores}", flush=True)

    t_total = time.perf_counter()
    rc_ablation = rc_sensitivity = 0

    # ── Stage 1: Ablation ────────────────────────────────────────────────────
    if not args.skip_ablation:
        if _ablation_already_complete():
            print("\nAblation: complete CSV found — skipping.", flush=True)
        else:
            ckpt = _latest_checkpoint()
            cmd = [sys.executable, "run_ablation.py", "--cores", str(args.cores)]
            if ckpt:
                print(f"\nAblation: Phase 1 checkpoint found: {ckpt}", flush=True)
                print("  Resuming Phase 2 — Phase 1 will be skipped.", flush=True)
                cmd += ["--resume", ckpt]
            rc_ablation = run(cmd, "Ablation (A0–A5)")
            if rc_ablation != 0:
                print("WARNING: Ablation exited non-zero. Sensitivity will still run.", flush=True)

    # ── Stage 2: Sensitivity pipeline ───────────────────────────────────────
    if not args.skip_sensitivity:
        rc_sensitivity = run(
            [sys.executable, "run_sensitivity_pipeline.py"],
            "Sensitivity pipeline (11 trials)"
        )

    # ── Summary ──────────────────────────────────────────────────────────────
    wall = time.perf_counter() - t_total
    _allow_sleep()
    print(f"\n{'='*72}", flush=True)
    print(f"Campaign complete  {time.strftime('%Y-%m-%d %H:%M:%S')}  |  {wall/60:.0f} min total", flush=True)
    print(f"  Ablation    : {'OK' if rc_ablation    == 0 else 'FAILED'}", flush=True)
    print(f"  Sensitivity : {'OK' if rc_sensitivity == 0 else 'FAILED'}", flush=True)
    print('='*72, flush=True)

    return max(rc_ablation, rc_sensitivity)


if __name__ == "__main__":
    sys.exit(main())
