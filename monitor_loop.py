"""
monitor_loop.py — Continuous 5-minute heartbeat for all active runs.

Prints one summary line every 5 minutes to stdout.
Launch once and leave running:
    python monitor_loop.py

Stop with Ctrl+C.
"""
import glob, json, os, time, csv

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "results", "analysis")
INTERVAL = 300   # 5 minutes

def _rows(pattern):
    files = sorted(glob.glob(os.path.join(RESULTS, pattern)))
    if not files:
        return 0, "no file", 0
    f = files[-1]
    age = time.time() - os.stat(f).st_mtime
    try:
        n = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1
    except Exception:
        n = 0
    return n, os.path.basename(f), age

def _ckpt(pattern):
    files = sorted(glob.glob(os.path.join(RESULTS, pattern)))
    if not files:
        return 0, 9999
    f = files[-1]
    age = time.time() - os.stat(f).st_mtime
    try:
        data = json.load(open(f, encoding="utf-8"))
        return len(data), age
    except Exception:
        return 0, age

def heartbeat():
    nf_rows, nf_file, nf_age  = _rows("noise_floor_2*.csv")
    nf_ckpt, nf_ck_age        = _ckpt("noise_floor_ckpt_2*.json")
    ab_rows, ab_file, ab_age  = _rows("adaptivity_ab_2*.csv")

    nf_stale = "⚠STALE" if nf_age > 3600 and nf_rows < 70 else ("DONE" if nf_rows >= 70 else "running")
    ab_done  = "✓DONE"  if ab_rows >= 420 else f"{ab_rows}/420"

    ts = time.strftime("%H:%M:%S")
    print(
        f"[{ts}]  "
        f"NF={nf_ckpt}/70 ckpt  {nf_rows}rows  age={int(nf_age//60)}m  {nf_stale}  |  "
        f"T1={ab_done}",
        flush=True
    )

print(f"Monitor started — printing every {INTERVAL//60} min. Ctrl+C to stop.", flush=True)
heartbeat()   # immediate first line
while True:
    time.sleep(INTERVAL)
    heartbeat()
