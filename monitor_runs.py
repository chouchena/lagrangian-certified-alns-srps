"""
monitor_runs.py — one-shot health check for all active ablation runs.

Run at any time:
    python monitor_runs.py

Checks: noise floor, adaptivity A/B, ablation warmmu.
Reports: row counts, last write time, whether each file is growing or stalled.
"""
import csv, glob, json, os, time

ROOT    = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "results", "analysis")
STALE_WARN_S = 3600   # warn if no update in 1 h (hard-tail pairs legitimately take 30-60 min each)

now = time.time()

def _check(label, pattern, expected_rows=None):
    files = sorted(glob.glob(os.path.join(RESULTS, pattern)))
    if not files:
        print(f"  {label:<30s} NO FILE FOUND")
        return
    f = files[-1]
    stat  = os.stat(f)
    age_s = now - stat.st_mtime
    try:
        rows = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1  # minus header
    except Exception:
        rows = "?"
    last = time.strftime("%H:%M:%S", time.localtime(stat.st_mtime))
    size_kb = round(stat.st_size / 1024, 1)
    age_str = f"{int(age_s//60)}m{int(age_s%60)}s ago"
    stale = " ⚠ STALE" if age_s > STALE_WARN_S else ""
    pct = f" ({rows}/{expected_rows} = {100*rows//expected_rows}%)" if expected_rows and isinstance(rows, int) else ""
    status = "✓" if not stale else "?"
    print(f"  {status} {label:<30s} rows={rows}{pct}  {size_kb}KB  last={last} ({age_str}){stale}")

    # last row preview
    try:
        with open(f, encoding="utf-8-sig") as fh:
            lines = fh.readlines()
        if len(lines) > 1:
            last_row = lines[-1].strip()[:100]
            print(f"      last: {last_row}")
    except Exception:
        pass

    # checkpoint
    ckpt = f.replace(".csv", "").replace("noise_floor_", "noise_floor_ckpt_") + ".json"
    ckpt2 = os.path.join(RESULTS, os.path.basename(f).replace(".csv", "_manifest.json"))
    for c in [ckpt, ckpt2]:
        if os.path.exists(c):
            cage = now - os.stat(c).st_mtime
            print(f"      ckpt: {os.path.basename(c)}  {round(os.stat(c).st_size/1024,1)}KB  {int(cage//60)}m ago")
            break

def _check_ckpt(label, pattern):
    """Check a JSON checkpoint even without a complete CSV."""
    files = sorted(glob.glob(os.path.join(RESULTS, pattern)))
    if not files:
        return
    f = files[-1]
    age_s = now - os.stat(f).st_mtime
    try:
        data = json.load(open(f, encoding="utf-8"))
        n = len(data)
    except Exception:
        n = "?"
    print(f"  ✓ {label:<30s} ckpt instances={n}  {round(os.stat(f).st_size/1024,1)}KB  "
          f"{int(age_s//60)}m{int(age_s%60)}s ago")

SEP = "=" * 65

print(SEP)
print(f"Run monitor  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(SEP)

print("\n[ Noise floor — Tier 2 ]")
_check("smoke/full CSV", "noise_floor_2*.csv", expected_rows=None)
_check_ckpt("checkpoint", "noise_floor_ckpt_2*.json")

print("\n[ Adaptivity A/B — Tier 1 ]")
_check("full run", "adaptivity_ab_2*.csv", expected_rows=420)

print("\n[ Ablation warmmu — A0-A5 ]")
_check("run", "ablation_warmmu_2*.csv")
_check_ckpt("checkpoint", "ablation_phase1_2*.json")

print(SEP)
print("Stale threshold: files not updated in 10 min get ⚠.")
print("Hard-tail instances with gap stop disabled can take up to 60 min per pair.")
print("A checkpoint growing = still running. A CSV not growing = waiting for batch.")
print(SEP)
