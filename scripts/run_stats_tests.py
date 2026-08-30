"""
run_stats_tests.py -- Statistical validity tests for COR submission.

Tests:
  1. Wilcoxon signed-rank: our objectives vs published BKS.
  2. Bootstrap 95% CI on mean certified gap across all 660 instances.
  3. Reproducibility: compare repro_run2 vs adaptive_master (after Exp 1).

Output: results/analysis/stats_tests_<timestamp>.txt (also printed to console)

Usage:
    python scripts/run_stats_tests.py
    python scripts/run_stats_tests.py --repro results/repro_run2_summary.csv
"""
from __future__ import annotations
import argparse, os, sys
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats

os.makedirs("results/analysis", exist_ok=True)
stamp    = datetime.now().strftime("%Y%m%d_%H%M")
out_path = f"results/analysis/stats_tests_{stamp}.txt"

parser = argparse.ArgumentParser()
parser.add_argument("--master", default="results/adaptive_master.csv")
parser.add_argument("--repro",  default=None)
args = parser.parse_args()

log = open(out_path, "w", encoding="utf-8")
def p(*a, **k):
    print(*a, **k); print(*a, **k, file=log)

STUDY = ["B","C","D","EB","EC","ED"]
p("="*70)
p("STATISTICAL VALIDITY TESTS FOR COR SUBMISSION")
p(f"Timestamp: {stamp}")
p("="*70)

if not os.path.exists(args.master):
    p(f"ERROR: {args.master} not found"); log.close(); sys.exit(1)

master = pd.read_csv(args.master)
master = master[master["family"].isin(STUDY)].copy()
p(f"Loaded {len(master)} study instances.")

for gap_col in ("final_cert_gap_pct","beta_gap_pct","cert_gap_pct"):
    if gap_col in master.columns: break
for obj_col in ("alns_obj","beta_obj","obj"):
    if obj_col in master.columns: break

# TEST 1 ---
p("\n--- TEST 1: Wilcoxon signed-rank  (our obj vs BKS) ---")
has_bks = master[master["bks"].notna()].copy()
has_bks = has_bks[~has_bks["bks"].astype(str).str.strip().isin(["","?","NA"])].copy()
has_bks["bks_f"] = pd.to_numeric(has_bks["bks"], errors="coerce")
has_bks["obj_f"] = pd.to_numeric(has_bks[obj_col], errors="coerce")
has_bks = has_bks.dropna(subset=["bks_f","obj_f"])
has_bks["diff"] = has_bks["obj_f"] - has_bks["bks_f"]
p(f"  Instances with BKS: {len(has_bks)}")
p(f"  Improved: {(has_bks['diff']>0).sum()}  Matched: {(has_bks['diff']==0).sum()}  Below: {(has_bks['diff']<0).sum()}")
nz = has_bks["diff"][has_bks["diff"]!=0]
if len(nz)>=5:
    st,pv = stats.wilcoxon(nz, alternative="two-sided", zero_method="wilcox")
    p(f"  Wilcoxon stat={st:.2f}  p={pv:.6f}")
    p("  SIGNIFICANT (p<0.05)" if pv<0.05 else "  NOT significant (p>=0.05) -- complementary framing holds")
else:
    p(f"  Too few non-zero diffs ({len(nz)}) -- use descriptive stats only")

# TEST 2 ---
p("\n--- TEST 2: Bootstrap 95% CI on mean certified gap ---")
gaps = pd.to_numeric(master[gap_col], errors="coerce").dropna().values
rng  = np.random.default_rng(seed=42)
boots = np.array([rng.choice(gaps,size=len(gaps),replace=True).mean() for _ in range(10000)])
lo,hi = np.percentile(boots,[2.5,97.5])
p(f"  N={len(gaps)}")
p(f"  Mean   = {gaps.mean():.4f}%")
p(f"  Median = {np.median(gaps):.4f}%")
p(f"  Max    = {gaps.max():.4f}%")
p(f"  95% CI = [{lo:.4f}%, {hi:.4f}%]")
p(f"  Paper text: mean {gaps.mean():.3f}% (95% CI [{lo:.3f}%, {hi:.3f}%])")
for t in [0.3,0.5,1.0,2.0]:
    p(f"  Within {t:.1f}%: {100*(gaps<t).mean():.1f}%")

# TEST 3 ---
p("\n--- TEST 3: Reproducibility (Run 2 vs Run 1) ---")
if not args.repro:
    p("  SKIPPED. After Experiment 1, re-run:")
    p("    python scripts/run_stats_tests.py --repro results/repro_run2_summary.csv")
elif not os.path.exists(args.repro):
    p(f"  ERROR: {args.repro} not found")
else:
    run2 = pd.read_csv(args.repro)
    for oc in ("beta_obj","alns_obj","obj"):
        if oc in run2.columns: obj2_col=oc; break
    for gc in ("beta_gap_pct","final_cert_gap_pct","cert_gap_pct"):
        if gc in run2.columns: gap2_col=gc; break
    m = master[["instance",obj_col,gap_col]].merge(
        run2[["instance",obj2_col,gap2_col]].rename(columns={obj2_col:"obj2",gap2_col:"gap2"}),
        on="instance",how="inner")
    m["obj1"]=pd.to_numeric(m[obj_col],errors="coerce")
    m["gap1"]=pd.to_numeric(m[gap_col],errors="coerce")
    m["obj2"]=pd.to_numeric(m["obj2"],errors="coerce")
    m["gap2"]=pd.to_numeric(m["gap2"],errors="coerce")
    m=m.dropna()
    p(f"  Matched: {len(m)}")
    p(f"  Identical obj: {(m['obj1']==m['obj2']).sum()} ({100*(m['obj1']==m['obj2']).mean():.1f}%)")
    p(f"  Run2 improved: {(m['obj2']>m['obj1']).sum()}")
    p(f"  Run2 regressed: {(m['obj2']<m['obj1']).sum()}")
    p(f"  Mean gap run1: {m['gap1'].mean():.4f}%  run2: {m['gap2'].mean():.4f}%")
    gd=m["gap2"]-m["gap1"]; nzgd=gd[gd!=0]
    if len(nzgd)>=5:
        st2,pv2=stats.wilcoxon(nzgd,zero_method="wilcox")
        p(f"  Wilcoxon gap diff: stat={st2:.2f}  p={pv2:.6f}")
        p("  STABLE (p>=0.05) -- cite reproducibility" if pv2>=0.05 else "  ! Significant diff -- investigate changed instances")
    else:
        p(f"  Too few differing instances ({len(nzgd)}) for Wilcoxon")

p("\n"+"="*70)
p(f"Output saved: {out_path}")
p("="*70)
log.close()
