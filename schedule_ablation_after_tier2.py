"""
schedule_ablation_after_tier2.py — waits for the Tier 2 noise-floor run to
finish (checkpoint reaches 70/70), then automatically launches the full
40-instance x 10-arm ablation study (run_ablation.py) hidden, using the cores
Tier 2 frees up. After launch, continues monitoring ablation itself and
auto-relaunches it (with --resume) if it stalls -- a dedicated,
ablation-scoped supervisor, kept separate from watchdog.py's noise_floor
supervision to avoid watchdog.py's process-liveness check (which is not
scoped per-run) racing with or duplicating this launch during the handoff.

Polls every 60s throughout: first waiting for Tier 2, then launching, then
supervising ablation itself. Logs everything to
results/ablation_scheduler.log.

Usage:
    python schedule_ablation_after_tier2.py --cores 6
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = r"C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe"
LOG_PATH = os.path.join(ROOT, "results", "ablation_scheduler.log")
POLL_S = 60
MAX_WAIT_H = 30          # give up waiting for Tier 2 after this many hours
TOTAL_JOBS = 400         # 40 instances x 10 arms
NO_PROGRESS_THRESH_S = 360     # 6 min, no ablation workers + no new rows -> stall
STALE_THRESH_S = 7200          # 2h with no checkpoint growth at all -> stall (slow path)
MAX_RESTARTS = 20


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def tier2_done():
    ckpts = sorted(glob.glob(os.path.join(ROOT, "results", "analysis", "noise_floor_ckpt_2*.json")))
    if not ckpts:
        return False, 0
    try:
        n = len(json.load(open(ckpts[-1], encoding="utf-8")))
    except Exception:
        return False, 0
    return n >= 70, n


def latest_ablation_ckpt():
    hits = sorted(glob.glob(os.path.join(ROOT, "results", "analysis", "ablation_b1b8s_ckpt_2*.json")))
    return hits[-1] if hits else None


def ablation_status():
    """Returns (n_done, ckpt_path, ckpt_age_s)."""
    ckpt = latest_ablation_ckpt()
    if not ckpt:
        return 0, None, float("inf")
    try:
        n = len(json.load(open(ckpt, encoding="utf-8")))
    except Exception:
        n = 0
    age = time.time() - os.stat(ckpt).st_mtime
    return n, ckpt, age


def ablation_workers_alive():
    """Scoped check (unlike watchdog.py's generic one): True only if a
    python.exe process is actually running run_ablation.py specifically,
    so this can't be confused by Tier 2's own workers during the handoff."""
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
             "| Where-Object { $_.CommandLine -match 'run_ablation.py' }).Count"],
            capture_output=True, text=True, timeout=20, cwd=ROOT)
        return int(r.stdout.strip() or "0") > 0
    except Exception:
        return None  # unknown -- treated conservatively by the caller


def launch_ablation(cores, resume_ckpt=None):
    ablation_log = os.path.join(ROOT, "results", "ablation_run.log")
    args = f"run_ablation.py --cores {cores}"
    if resume_ckpt:
        args += f" --resume \"{resume_ckpt}\""
    psi_cmd = (
        f"cd '{ROOT}'; & '{PYTHON_EXE}' {args} *>&1 | Tee-Object '{ablation_log}'"
    )
    from subprocess import Popen, CREATE_NO_WINDOW
    Popen(["powershell.exe", "-NoLogo", "-NoProfile", "-Command", psi_cmd],
          creationflags=CREATE_NO_WINDOW, cwd=ROOT)
    if resume_ckpt:
        log(f"RELAUNCHED ablation: cores={cores}  resume={os.path.basename(resume_ckpt)}")
    else:
        log(f"LAUNCHED ablation: cores={cores}  log={ablation_log}")


def supervise_ablation(cores):
    """Post-launch monitoring loop: polls every 60s, relaunches (--resume) on
    a detected stall, gives up after MAX_RESTARTS (logs loudly, doesn't loop
    forever)."""
    restarts = 0
    last_done = None
    last_time = None
    while True:
        time.sleep(POLL_S)
        done, ckpt, age = ablation_status()
        if done >= TOTAL_JOBS:
            log(f"ablation COMPLETE: {done}/{TOTAL_JOBS} rows")
            return

        workers = ablation_workers_alive()
        ts = time.strftime("%H:%M")
        w_str = "yes" if workers is True else ("NO" if workers is False else "UNKNOWN")
        log(f"[{ts}] ablation: ckpt={done}/{TOTAL_JOBS}  age={int(age//60) if age != float('inf') else '?'}m  workers={w_str}")

        if workers is True:
            last_done, last_time = done, time.time()
            continue

        if last_done is None or done != last_done:
            last_done, last_time = done, time.time()
            no_progress_s = 0.0
        else:
            no_progress_s = time.time() - (last_time or time.time())

        stalled = (age > STALE_THRESH_S) or (no_progress_s > NO_PROGRESS_THRESH_S)
        if not stalled:
            continue

        if restarts >= MAX_RESTARTS:
            log(f"  MAX_RESTARTS ({MAX_RESTARTS}) reached for ablation — "
                f"NOT relaunching. Manual intervention needed.")
            return

        log(f"  STALLED (age={int(age)}s, no_progress={int(no_progress_s)}s). Autofixing.")
        launch_ablation(cores, resume_ckpt=ckpt)
        restarts += 1
        last_done, last_time = done, time.time()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=int, default=6)
    args = ap.parse_args()

    log(f"Scheduler started. Waiting for Tier 2 (70/70), polling every {POLL_S}s, "
        f"max wait {MAX_WAIT_H}h.")
    t0 = time.time()
    launched = False
    while True:
        done, n = tier2_done()
        elapsed_h = (time.time() - t0) / 3600
        log(f"poll: tier2 ckpt={n}/70  elapsed={elapsed_h:.2f}h")
        if done:
            log("Tier 2 COMPLETE (70/70). Launching ablation now.")
            launch_ablation(args.cores)
            launched = True
            break
        if elapsed_h >= MAX_WAIT_H:
            log(f"MAX_WAIT ({MAX_WAIT_H}h) reached — Tier 2 still not done. "
                f"NOT launching automatically. Manual intervention needed.")
            break
        time.sleep(POLL_S)

    if launched:
        log("Switching to post-launch ablation supervision (auto-relaunch on stall).")
        supervise_ablation(args.cores)

    log("Scheduler exiting.")




if __name__ == "__main__":
    main()
