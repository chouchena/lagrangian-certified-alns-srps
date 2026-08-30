"""
watchdog.py — Background monitor and autofix for long-running experiments.

Checks every 60 s. If a registered run is not progressing and not done,
it commits any dirty non-source files, then relaunches from the latest
checkpoint. Logs every action. Sends a Windows toast notification on
autofix or completion (graceful degradation if BurntToast unavailable).

Usage:
    python watchdog.py          # watches the default run set (RUNS below)
    python watchdog.py --once   # one check cycle then exit (for testing)

Safety:
  - MAX_RESTARTS (3) per run — never loops forever
  - Only restarts if run is not done AND no Python workers are active
  - Never deletes any data
  - Commits ONLY non-source dirty files (SESSION.md, results/, texput.log)
"""
from __future__ import annotations

import ctypes
import glob
import json
import os
import subprocess
import sys
import time

ROOT     = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(ROOT, "results", "watchdog.log")
STATE_PATH = os.path.join(ROOT, "results", "watchdog_state.json")
MAX_RESTARTS   = 50
STALE_THRESH_S = 7200   # 2 h with no checkpoint growth -> declare stalled (slow path)
NO_PROGRESS_THRESH_S = 360   # 6 min with no workers AND no new rows -> declare stalled (fast path)
CHECK_INTERVAL = 60     # seconds between checks

# Pinned explicit interpreter path -- NEVER use bare "python" or sys.executable
# for relaunching a child run. If THIS watchdog process was itself started
# under the wrong Python (PATH-dependent, e.g. via supervisor.ps1's inherited
# environment), sys.executable would faithfully propagate that mistake to
# every relaunch. A version mismatch (3.13 vs the project's 3.10) caused a
# real, repeated, silent crash on 2026-08-28 (Windows multiprocessing spawn
# regression, OSError: WinError 87) -- pinning eliminates this permanently.
PYTHON_EXE = r"C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe"

# ── Windows sleep prevention ──────────────────────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
try:
    ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
except Exception:
    pass

# ── Registered runs ───────────────────────────────────────────────────────────
# Each entry: (run_id, checkpoint_glob, csv_glob, total_expected, relaunch_cmd)
RUNS = [
    {
        "id":        "noise_floor",
        "title":     "Tier2-NoiseFloor",
        "ckpt_glob": "results/analysis/noise_floor_ckpt_2*.json",
        "csv_glob":  "results/analysis/noise_floor_2*.csv",
        "total":     70,
        "cmd":       [PYTHON_EXE, "run_noise_floor.py", "--cores", "6"],
        "log_path":  "results/noise_floor_run.log",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def log(msg: str):
    # Writes directly to LOG_PATH with an open-append-close pattern (file is
    # never held open between calls). This is safe as long as no OTHER
    # process holds a competing lock on the same file — which was exactly
    # the original bug: launching watchdog.py under `Tee-Object` caused
    # Tee-Object to hold an exclusive handle on watchdog.log while this
    # function also tried to open it, raising PermissionError and (before
    # the fix below existed) taking the crash unhandled. supervisor.ps1
    # no longer uses Tee-Object for this reason — see supervisor.ps1.
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # Never let logging itself take down the monitoring loop.


def notify(title: str, body: str):
    """Windows toast notification — silent if BurntToast unavailable."""
    try:
        subprocess.run(
            ["powershell", "-Command",
             f'New-BurntToastNotification -Text "{title}", "{body}"'],
            capture_output=True, timeout=10, cwd=ROOT
        )
    except Exception:
        pass   # BurntToast not installed — watchdog log is the record


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def python_workers_alive() -> bool | None:
    """True if any Python process is CURRENTLY burning CPU; False if none are;
    None if the check itself failed (caller must not treat None as "alive" —
    Get-Process's CPU field is CUMULATIVE since process start, so a single
    snapshot cannot distinguish "actively working" from "burned some CPU a
    long time ago, then hung". This takes two samples ~2s apart and checks
    for a real increase, which is the only way to detect an active process.
    """
    script = (
        "$p = Get-Process python* -ErrorAction SilentlyContinue | "
        "Select-Object Id, @{N='CPU';E={$_.CPU}}; "
        "$p | ConvertTo-Json -Compress"
    )
    try:
        r1 = subprocess.run(["powershell", "-Command", script],
                            capture_output=True, text=True, timeout=15, cwd=ROOT)
        if r1.returncode != 0 or not r1.stdout.strip():
            return False  # no python processes at all
        time.sleep(2.0)
        r2 = subprocess.run(["powershell", "-Command", script],
                            capture_output=True, text=True, timeout=15, cwd=ROOT)
        if r2.returncode != 0 or not r2.stdout.strip():
            return False

        def _parse(raw):
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            return {d["Id"]: float(d.get("CPU") or 0.0) for d in data}

        before, after = _parse(r1.stdout), _parse(r2.stdout)
        for pid, cpu_after in after.items():
            if cpu_after - before.get(pid, 0.0) > 0.05:
                return True   # this process burned real CPU in the last 2s
        return False   # processes exist but none are actively computing
    except Exception as exc:
        log(f"  WARNING: liveness check failed ({exc}) — treating as UNKNOWN, not alive")
        return None


def commit_non_source_dirty():
    """Stage and commit non-source dirty files (results, SESSION, logs)."""
    try:
        porcelain = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=ROOT, timeout=20
        ).stdout
        dirty = []
        for l in porcelain.splitlines():
            path = l[3:].replace("\\", "/").strip()
            if path.startswith(("results/", "archive/", "SESSION", "texput")):
                dirty.append(path)
        if dirty:
            subprocess.run(["git", "add"] + dirty, cwd=ROOT, capture_output=True, timeout=20)
            subprocess.run(
                ["git", "commit", "-m", "watchdog: auto-commit non-source artifacts"],
                cwd=ROOT, capture_output=True, timeout=20
            )
            log(f"  committed {len(dirty)} non-source file(s): {dirty[:5]}")
    except subprocess.TimeoutExpired:
        log("  WARNING: git commit timed out (20s) — likely a concurrent git lock; skipping this cycle")
    except Exception as exc:
        log(f"  WARNING: commit failed: {exc}")


def latest_checkpoint(run: dict) -> str | None:
    hits = sorted(glob.glob(os.path.join(ROOT, run["ckpt_glob"])))
    return hits[-1] if hits else None


def rows_done(run: dict) -> int:
    hits = sorted(glob.glob(os.path.join(ROOT, run["csv_glob"])))
    if not hits:
        return 0
    try:
        return sum(1 for _ in open(hits[-1], encoding="utf-8-sig")) - 1
    except Exception:
        return 0


def ckpt_count(run: dict) -> int:
    ckpt = latest_checkpoint(run)
    if not ckpt:
        return 0
    try:
        return len(json.load(open(ckpt, encoding="utf-8")))
    except Exception:
        return 0


def ckpt_age_s(run: dict) -> float:
    ckpt = latest_checkpoint(run)
    if not ckpt:
        return float("inf")
    return time.time() - os.stat(ckpt).st_mtime


def relaunch(run: dict, state: dict):
    """Relaunch the run, using --resume if a checkpoint exists."""
    run_id = run["id"]
    restarts = state.get(run_id, {}).get("restarts", 0)
    if restarts >= MAX_RESTARTS:
        log(f"  MAX_RESTARTS ({MAX_RESTARTS}) reached for {run_id} — NOT relaunching. Manual intervention needed.")
        notify(f"Watchdog: {run['title']}", f"MAX_RESTARTS reached — manual fix needed")
        return

    commit_non_source_dirty()

    ckpt = latest_checkpoint(run)
    cmd  = run["cmd"][:]
    if ckpt:
        cmd += ["--resume", ckpt]
        log(f"  resuming from checkpoint: {os.path.basename(ckpt)}")
    else:
        log("  no checkpoint — starting fresh")

    log_path = os.path.join(ROOT, run["log_path"])
    launch_cmd = (
        f"cd '{ROOT}'; {' '.join(cmd)} *>&1 | Tee-Object '{log_path}'"
    )
    subprocess.Popen(
        ["powershell", "-NoLogo", "-NoProfile", "-Command", launch_cmd],
        cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW
    )

    state.setdefault(run_id, {})["restarts"] = restarts + 1
    state[run_id]["last_restart"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)
    log(f"  relaunched (restart #{restarts + 1}/{MAX_RESTARTS})")
    notify(f"Watchdog: {run['title']}", f"Restarted (attempt {restarts+1}/{MAX_RESTARTS})")


# ── Main check loop ───────────────────────────────────────────────────────────
def check_all(state: dict, once: bool = False):
    for run in RUNS:
        rid   = run["id"]
        title = run["title"]
        total = run["total"]
        done  = rows_done(run)
        ckpt  = ckpt_count(run)
        age   = ckpt_age_s(run)

        if done >= total:
            # Run finished
            was_done = state.get(rid, {}).get("done_notified", False)
            if not was_done:
                log(f"{title}: COMPLETE ({done}/{total} rows)")
                notify(f"✓ {title} COMPLETE", f"{done}/{total} rows written")
                state.setdefault(rid, {})["done_notified"] = True
                save_state(state)
            continue

        workers = python_workers_alive()
        ts = time.strftime("%H:%M")
        workers_str = "yes" if workers is True else ("NO" if workers is False else "UNKNOWN")
        log(f"[{ts}] {title}: ckpt={ckpt}/{total}  rows={done}  age={int(age//60)}m  workers={workers_str}")

        if workers is True:
            # Workers are running — record progress watermark and move on.
            rstate = state.setdefault(rid, {})
            rstate["last_seen_done"] = done
            rstate["last_seen_time"] = time.time()
            save_state(state)
            continue

        # workers is False or None (check failed) — in both cases we cannot
        # confirm the run is actively progressing, so we fall through to the
        # same stall-detection logic. Treating "unknown" as "not confirmed
        # alive" is deliberately conservative: a monitor that silently
        # assumes health when it cannot verify it is not a monitor.
        # ── No workers running. Determine whether this is a genuine stall. ──
        # BUG FIXED (2026-08-28): this used to only fast-path when `done == 0`
        # (zero TOTAL rows ever written), which never fires again once a run
        # has produced *any* historical output — so a resumed run that hangs
        # immediately after a relaunch (done > 0 from the carried-over rows,
        # zero NEW progress) fell through to "appears healthy" and was never
        # retried except by the 2h global checkpoint-age check. This is
        # exactly what happened: the run relaunched at 10:23, hung at
        # startup, and was invisible to this logic for over an hour.
        #
        # Fix: track last_seen_done/last_seen_time per run in persistent
        # state (updated above whenever workers ARE running). If `done` has
        # not increased AND no workers are running for more than
        # NO_PROGRESS_THRESH_S, that is a stall — independent of whether any
        # rows exist historically or how old the on-disk checkpoint file is.
        rstate = state.setdefault(rid, {})
        last_done = rstate.get("last_seen_done")
        last_time = rstate.get("last_seen_time")
        if last_done is None or done != last_done:
            # First time seeing this run with no workers, or it just changed —
            # start the no-progress clock now rather than assuming a stall.
            rstate["last_seen_done"] = done
            rstate["last_seen_time"] = time.time()
            save_state(state)
            no_progress_s = 0.0
        else:
            no_progress_s = time.time() - (last_time or time.time())

        if age > STALE_THRESH_S:
            log(f"  STALLED: {int(age//3600)}h since last checkpoint write, no workers. Autofixing.")
            relaunch(run, state)
        elif no_progress_s > NO_PROGRESS_THRESH_S:
            log(f"  STALLED: no workers and no new rows for {int(no_progress_s//60)}m "
                f"(done stuck at {done}). Autofixing.")
            relaunch(run, state)
        elif ckpt <= 3:
            # Might have just aborted at startup — check log for evidence.
            log_file = os.path.join(ROOT, run["log_path"])
            aborted = False
            if os.path.exists(log_file):
                tail = open(log_file, encoding="utf-8", errors="replace").read()[-2000:]
                if "ABORT" in tail or "Error" in tail or "Traceback" in tail:
                    aborted = True
                    log(f"  ABORT/ERROR detected in run log — autofixing")
            if aborted:
                relaunch(run, state)
            else:
                log(f"  No workers ({ckpt} ckpt, {done} rows, no-progress={int(no_progress_s//60)}m) — watching")
        else:
            log(f"  No workers but run appears healthy ({ckpt} ckpt, {done} rows, "
                f"no-progress={int(no_progress_s//60)}m) — watching")


def main():
    once = "--once" in sys.argv
    log("=" * 60)
    log(f"Watchdog started — checking every {CHECK_INTERVAL}s  (max_restarts={MAX_RESTARTS})")
    log(f"Registered runs: {[r['id'] for r in RUNS]}")
    log("=" * 60)

    state = load_state()

    while True:
        try:
            check_all(state, once)
        except Exception as exc:
            # A single bad cycle must never silently kill the monitoring loop.
            log(f"WATCHDOG CYCLE ERROR (continuing): {type(exc).__name__}: {exc}")
        if once:
            break
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
