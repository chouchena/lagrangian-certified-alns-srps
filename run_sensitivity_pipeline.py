"""
run_sensitivity_pipeline.py — Run all sensitivity variant trials sequentially.

Runs 11 trials (2 per parameter × 5 parameters + 1 extra for gap_threshold):
  gap_threshold : 0.001, 0.005, 0.010
  destroy_fracs : tight, wide
  phase_rt      : 150, 450
  lag_max_iter  : 100, 400
  lag_max_time  : 30, 120

Each trial writes its CSV to results/sensitivity/.
Skips any trial whose output CSV already exists (safe to re-run).

Usage:
    python run_sensitivity_pipeline.py
"""
import ctypes, glob, os, subprocess, sys, time

_ES_CONTINUOUS = 0x80000000; _ES_SYSTEM_REQUIRED = 0x00000001
def _prevent_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    except Exception: pass
def _allow_sleep():
    try: ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception: pass

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "run_sensitivity.py")
OUT_DIR = os.path.join(ROOT, "results", "sensitivity")

TRIALS = [
    ("gap_threshold", "0.001"),
    ("gap_threshold", "0.005"),
    ("gap_threshold", "0.010"),
    ("destroy_fracs", "tight"),
    ("destroy_fracs", "wide"),
    ("phase_rt",      "150"),
    ("phase_rt",      "450"),
    ("lag_max_iter",  "100"),
    ("lag_max_iter",  "400"),
    ("lag_max_time",  "30"),
    ("lag_max_time",  "120"),
]

def already_done(param, value):
    tag = f"{param}_{value}"
    return bool(glob.glob(os.path.join(OUT_DIR, f"sensitivity_{tag}_*.csv")))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    _prevent_sleep()

    total = len(TRIALS)
    t_pipeline = time.perf_counter()

    print("=" * 72)
    print(f"Sensitivity pipeline — {total} variant trials")
    print("=" * 72)

    for i, (param, value) in enumerate(TRIALS, 1):
        label = f"{param}={value}"
        if already_done(param, value):
            print(f"\n[{i}/{total}] SKIP {label} (CSV already exists)")
            continue

        print(f"\n[{i}/{total}] START {label}  ({time.strftime('%H:%M:%S')})")
        t0 = time.perf_counter()

        result = subprocess.run(
            [sys.executable, RUNNER, "--param", param, "--value", value],
            cwd=ROOT,
        )  # workers fixed at 6 inside run_sensitivity.py (CLAUDE.md)

        elapsed = time.perf_counter() - t0
        if result.returncode == 0:
            print(f"[{i}/{total}] DONE  {label}  ({elapsed/60:.1f} min)")
        else:
            print(f"[{i}/{total}] FAILED {label} (exit={result.returncode}) — continuing")

    wall = time.perf_counter() - t_pipeline
    _allow_sleep()
    print(f"\n{'='*72}")
    print(f"Pipeline complete — {wall/60:.0f} min total")
    print(f"Results in: {OUT_DIR}")
    print("=" * 72)
