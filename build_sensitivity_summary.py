"""
build_sensitivity_summary.py — aggregates the OAT sensitivity trials into one
table so every §5.1 / §6.5.2 number derives from a committed script.

Each trial CSV in results/sensitivity/ is one parameter setting run on the same
30-instance stratified subset with the adaptive loop (run_sensitivity.py).
Reports mean/median/max certified gap per trial and the delta vs the baseline.

Scope note (2026-08-30): the trial CSVs were generated 2026-06-20/21, before
the post-search refinement stage (`rebuild_bounds_certified.py`, added
2026-08-26) existed, and `run_sensitivity.py` never calls it. The gap columns
here are therefore on the pre-refinement, pre-monotonicity-guard dual-bound
codepath and are not on the same basis as the paper's post-refinement headline
gap (`final_cert_gap_pct` in `adaptive_master_refined.csv`). Refinement only
re-solves the dual against a *fixed* incumbent objective and never changes it
(see `rebuild_bounds_certified.py` docstring), and the primal search code
(`core/search_controller.py`, `core/operators.py`) has had no default-behavior
changes since these trials ran (only additive instrumentation and an opt-in,
default-True `accept_worse` flag added later for the ablation study). The
objective-value columns added below (`obj_*`) are therefore unaffected by the
refinement/monotonicity-guard staleness and are the metric to use for any
claim about the *current* algorithm; the gap columns should be read only as
evidence about the in-loop mechanism's sensitivity, at the pre-refinement
resolution stated in the paper.

Usage:
    python build_sensitivity_summary.py [--dir results/sensitivity]

Output:
    results/analysis/sensitivity_summary_<date>.csv
"""
import argparse, glob, os
from datetime import datetime

import pandas as pd

GAP_COL = "final_gap_pct"
OBJ_COL = "final_obj"
REF_COL = "ref_obj"


def trial_name(path):
    return os.path.basename(path).replace("sensitivity_", "").rsplit("_", 2)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="results/sensitivity")
    args = ap.parse_args()

    rows = []
    for f in sorted(glob.glob(os.path.join(args.dir, "*.csv"))):
        d = pd.read_csv(f)
        if GAP_COL not in d.columns:
            continue
        x = pd.to_numeric(d[GAP_COL], errors="coerce").dropna()
        row = {"trial": trial_name(f), "file": os.path.basename(f),
               "n": len(x), "mean": round(x.mean(), 4),
               "median": round(x.median(), 4), "max": round(x.max(), 4)}

        # Objective-value effect: refinement-independent, since refinement
        # never alters the incumbent objective (only re-solves the dual
        # against it). ref_obj is the fixed external reference (main-campaign
        # incumbent) read from adaptive_master.csv by run_sensitivity.py, so
        # it is identical across trials and safe to compare directly.
        if OBJ_COL in d.columns and REF_COL in d.columns:
            obj = pd.to_numeric(d[OBJ_COL], errors="coerce")
            ref = pd.to_numeric(d[REF_COL], errors="coerce")
            valid = obj.notna() & ref.notna() & (ref != 0)
            rel_pct = ((obj[valid] - ref[valid]) / ref[valid] * 100)
            row["obj_delta_mean"] = round(float((obj[valid] - ref[valid]).mean()), 4)
            row["obj_reldelta_mean_pct"] = round(float(rel_pct.mean()), 5)
            row["obj_reldelta_max_abs_pct"] = round(float(rel_pct.abs().max()), 5)
            row["obj_n_worse_than_ref"] = int((obj[valid] < ref[valid]).sum())
        rows.append(row)

    df = pd.DataFrame(rows)
    base = df[df.trial == "baseline"]["mean"]
    base = float(base.iloc[0]) if len(base) else float("nan")
    df["delta_baseline"] = (df["mean"] - base).round(4)

    if "obj_reldelta_mean_pct" in df.columns:
        obj_base = df[df.trial == "baseline"]["obj_reldelta_mean_pct"]
        obj_base = float(obj_base.iloc[0]) if len(obj_base) else float("nan")
        df["obj_reldelta_vs_baseline_pct"] = (df["obj_reldelta_mean_pct"] - obj_base).round(5)

    df = df.sort_values("trial").reset_index(drop=True)

    os.makedirs("results/analysis", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = f"results/analysis/sensitivity_summary_{stamp}.csv"
    df.to_csv(out, index=False)

    print(f"Baseline mean cert gap (pre-refinement) = {base:.4f}%  (30-instance subset)")
    if "obj_reldelta_mean_pct" in df.columns:
        print(f"Baseline mean objective deviation from reference = {obj_base:+.5f}%  "
              "(refinement-independent)")
    print(df.to_string(index=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
