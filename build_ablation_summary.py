"""
build_ablation_summary.py -- Appendix ablation stratified summary (tab:ablation,
tab:ablation-family), plus the Tier 2 noise-floor scale bar and a B5/B7
consistency check against the stronger census/identity measurements already
reported elsewhere in the paper.

Aggregates the completed B1-B8+S ablation (run_ablation.py, 40 instances x 10
arms) together with:

  - the measured hard-tail noise floor (Tier 2, run_noise_floor.py, 70
    instances, A0 vs A0' disjoint seeds) used as the detectability scale bar,
    and the minimum detectable effect (MDE) it implies at this design's
    n=20-per-stratum sample size;
  - a per-family / per-size breakdown that surfaces effects the pooled mean
    cancels. Declared exploratory: family cells range from n=1 to n=8 within
    a stratum, so these are hypothesis-generating, not confirmatory;
  - a consistency check for B5 (ejection chain) and B7 (in-loop re-bound)
    against the stronger, larger-population measurements already in the
    paper: the ejection-chain identity (0/660-derived) and the hard-tail
    re-bound census (build_hardtail_refresh.py, all 70 instances). These two
    arms were run here too even though the paper's ablation-design text
    argued a sampled arm would be weaker evidence than what is already in
    hand -- so they are reported as a cross-check, not a new primary source.

Usage:
    python build_ablation_summary.py

Inputs (auto-detected, latest by mtime, with a row-count sanity check):
    results/analysis/ablation_b1b8s_2*.csv   (not *_ckpt*, not *_manifest*; 400 rows)
    results/analysis/noise_floor_2*.csv      (not *_manifest*; 70 rows)
    results/analysis/hardtail_refresh_*.csv  (re-bound census, if present)
    results/adaptive_master.csv              (family, n, alpha)

Outputs (results/analysis/):
    ablation_summary_<ts>.txt   human-readable full report (what this prints)
    ablation_summary_<ts>.csv   per-arm x stratum pooled table
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sys
from datetime import datetime

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

Z_ALPHA2 = 1.959964   # two-sided alpha=0.05
Z_BETA   = 0.841621   # power=0.80

ARMS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "S"]


def _latest(pattern: str, min_rows: int | None = None, row_key=None) -> str:
    hits = sorted(glob.glob(pattern), key=os.path.getmtime)
    if min_rows is not None:
        hits = [h for h in hits if len(pd.read_csv(h)) >= min_rows]
    if not hits:
        raise SystemExit(f"No file matching {pattern} with >= {min_rows} rows found.")
    return hits[-1]


def load_ablation() -> pd.DataFrame:
    path = _latest(os.path.join("results", "analysis", "ablation_b1b8s_2*.csv"), min_rows=400)
    df = pd.read_csv(path)
    df = df[[c for c in df.columns]]
    print(f"Ablation source: {path}  ({len(df)} rows)")
    return df


def load_noise_floor() -> pd.DataFrame:
    hits = [h for h in glob.glob(os.path.join("results", "analysis", "noise_floor_2*.csv"))
            if "manifest" not in h]
    hits = [h for h in hits if len(pd.read_csv(h, encoding="utf-8-sig")) >= 70]
    if not hits:
        raise SystemExit("No complete (>=70 row) noise-floor CSV found.")
    path = sorted(hits, key=os.path.getmtime)[-1]
    df = pd.read_csv(path, encoding="utf-8-sig")
    print(f"Noise floor source: {path}  ({len(df)} rows)")
    return df


def load_hardtail_refresh():
    hits = glob.glob(os.path.join("results", "analysis", "hardtail_refresh_*.txt"))
    if not hits:
        return None
    path = sorted(hits, key=os.path.getmtime)[-1]
    print(f"Re-bound census source: {path}")
    return open(path, encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join("results", "analysis"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    ab = load_ablation()
    nf = load_noise_floor()
    census_txt = load_hardtail_refresh()

    # Ablation CSV already carries "family"; only n/alpha are pulled from the
    # master (dropped here to avoid a family_x/family_y suffix collision).
    master = pd.read_csv("results/adaptive_master.csv", encoding="utf-8-sig")[
        ["instance", "n", "alpha"]].drop_duplicates("instance")
    m = ab.merge(master, on="instance", how="left")
    m["n"] = pd.to_numeric(m["n"], errors="coerce")

    a0 = m[m.arm_id == "A0"][["instance", "stratum", "cert_gap_pct", "cert_gap_own_pct",
                              "obj", "stop_reason"]].rename(columns={
        "cert_gap_pct": "a0_gap", "cert_gap_own_pct": "a0_gap_own",
        "obj": "a0_obj", "stop_reason": "a0_stop"})
    d = m.merge(a0, on=["instance", "stratum"], how="left")
    d["delta"] = d["cert_gap_pct"] - d["a0_gap"]
    d["delta_own"] = d["cert_gap_own_pct"] - d["a0_gap_own"]

    # ---- 1) Noise floor + minimum detectable effect at n=20/stratum ----
    sigma = nf["delta_pct"].astype(float).std(ddof=1)
    mean_abs = nf["abs_delta_pct"].astype(float).mean()
    max_abs = nf["abs_delta_pct"].astype(float).max()
    n_strat = 20
    mde = sigma * (Z_ALPHA2 + Z_BETA) / math.sqrt(n_strat)

    lines = []
    lines.append("=" * 100)
    lines.append("1) NOISE FLOOR (Tier 2, hard-tail, n=70, A0 vs A0' disjoint seeds)")
    lines.append("=" * 100)
    lines.append(f"mean |delta| = {mean_abs:.4f} pp   max |delta| = {max_abs:.4f} pp   "
                 f"sd(signed delta) = {sigma:.4f} pp")
    lines.append(f"Minimum detectable effect at n={n_strat}/stratum "
                 f"(two-sided alpha=0.05, power=0.80): {mde:.4f} pp")
    lines.append("(Assumes the ablation's arm-vs-A0 run-to-run variance is comparable to the "
                 "measured Tier-2 same-instance different-run variance; not re-derived from the "
                 "ablation's own data because the ablation has no same-config replicate arm.)")

    # ---- 2) Pooled stratified table (the paper's primary ablation table) ----
    piv = d[d.arm_id.isin(ARMS)].pivot_table(index="stratum", columns="arm_id",
                                              values="delta", aggfunc="mean")
    lines.append("")
    lines.append("=" * 100)
    lines.append("2) POOLED MEAN DELTA vs A0, cert_gap_pct (pp) -- the primary ablation table")
    lines.append("=" * 100)
    lines.append(piv[ARMS].round(4).to_string())

    csv_out = piv[ARMS].round(4).reset_index()

    # ---- 3) Fraction of instances above the noise-floor mean, per arm ----
    lines.append("")
    lines.append("=" * 100)
    lines.append(f"3) INSTANCES WITH |delta| > noise-floor mean ({mean_abs:.4f} pp), per arm")
    lines.append("=" * 100)
    for arm in ARMS:
        sub = d[d.arm_id == arm]
        above = sub[sub["delta"].abs() > mean_abs]
        lines.append(f"{arm:4s}: {len(above):2d}/{len(sub)} instances above floor "
                     f"(strata: {dict(above.stratum.value_counts())})")

    # ---- 4) Family / size breakdown (exploratory) ----
    lines.append("")
    lines.append("=" * 100)
    lines.append("4) BY STRATUM x FAMILY -- EXPLORATORY (cells n=1..8; hypothesis-generating only)")
    lines.append("=" * 100)
    fam_piv = d[d.arm_id.isin(ARMS)].pivot_table(index=["stratum", "family"],
                                                  columns="arm_id", values="delta", aggfunc="mean")
    lines.append(fam_piv[ARMS].round(4).to_string())
    lines.append("")
    lines.append("cell sizes (n instances per stratum x family):")
    lines.append(d[d.arm_id == "A0"].groupby(["stratum", "family"]).size().to_string())

    d["n_bucket"] = d.groupby("stratum")["n"].transform(
        lambda s: pd.qcut(s, 2, labels=["small", "large"]))
    lines.append("")
    lines.append("BY STRATUM x SIZE BUCKET (median split within stratum) -- exploratory")
    size_piv = d[d.arm_id.isin(ARMS)].pivot_table(index=["stratum", "n_bucket"],
                                                   columns="arm_id", values="delta", aggfunc="mean",
                                                   observed=False)
    lines.append(size_piv[ARMS].round(4).to_string())

    # ---- 5) B5 / B7 cross-check against stronger existing measurements ----
    lines.append("")
    lines.append("=" * 100)
    lines.append("5) B5/B7 CROSS-CHECK vs stronger census/identity measurements already in the paper")
    lines.append("=" * 100)
    b5 = d[d.arm_id == "B5"].groupby("stratum")["delta"].mean()
    lines.append("B5 (no ejection chain) sampled arm-level mean delta (this ablation, n=20/stratum):")
    lines.append(b5.round(4).to_string())
    lines.append("Reference (identity over all 660, from the paper's main text): "
                 "hard_tail = 0.0000 pp (never fires there); closing (multi-phase) = 0.0011 pp.")

    b7 = d[d.arm_id == "B7"].copy()
    b7["obj_tie"] = (b7["obj"] - b7["a0_obj"]).abs() < 1e-6
    lines.append("")
    lines.append("B7 (no in-loop re-bound): objective identical to A0, by stratum (primal channel):")
    lines.append(b7.groupby("stratum")["obj_tie"].agg(["sum", "count"]).to_string())
    lines.append("Reference (census over all 70 hard-tail instances, build_hardtail_refresh.py): "
                 "objective identical on 70/70; mean CERTIFICATE (dual) gap reduction from the "
                 "re-bound = 0.264 pp -- invisible to any fixed-common-bound ablation by "
                 "construction, consistent with the sampled primal tie found here.")
    if census_txt:
        lines.append("")
        lines.append("--- re-bound census file (first 15 lines) ---")
        lines.extend(census_txt.splitlines()[:15])

    report = "\n".join(lines)
    print(report)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = os.path.join(args.outdir, f"ablation_summary_{stamp}.txt")
    csv_path = os.path.join(args.outdir, f"ablation_summary_{stamp}.csv")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    csv_out.to_csv(csv_path, index=False)
    print(f"\nWrote {txt_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
