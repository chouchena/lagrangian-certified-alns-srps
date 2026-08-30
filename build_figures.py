"""
build_figures.py — generate the two paper figures from the canonical adaptive
results, so every figure is reproducible from a committed script.

Figure 1 (fig_cert_tiers.pdf): certificate-tier distribution over the 660-instance
                               study set, using the post-refinement series.
Figure 2 (fig_hardness.pdf):   mean certified gap by family and budget tightness
                               alpha (the certification-difficulty summary).

Usage:  python build_figures.py [--csv results/adaptive_master_refined.csv]
Output: paper/figures/fig_cert_tiers.pdf , paper/figures/fig_hardness.pdf
"""
import argparse, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STUDY = ["B", "C", "D", "EB", "EC", "ED"]
TIER_EDGES = [-1e-9, 1e-9, 0.5, 1.0, 2.0, float("inf")]
TIER_LABELS = ["exact", "<0.5%", "0.5–1%", "1–2%", ">2%"]
ALPHAS = [0.25, 0.50, 0.75]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/adaptive_master_refined.csv")
    args = ap.parse_args()
    outdir = "paper/figures"
    os.makedirs(outdir, exist_ok=True)

    d = pd.read_csv(args.csv)
    s = d[d["family"].isin(STUDY)].copy()
    s["g"] = pd.to_numeric(s["final_cert_gap_pct"], errors="coerce")
    # Validity guard (see build_paper_stats.py): a valid upper bound is never
    # below a known feasible objective; recompute the gap on the single
    # instance whose adaptive UB underran the BPC-proven optimum.
    _bks = pd.to_numeric(s["bks"], errors="coerce")
    _alns = pd.to_numeric(s["alns_obj"], errors="coerce")
    _ub = pd.to_numeric(s["best_ub"], errors="coerce")
    _viol = _bks.notna() & (_ub < _bks)
    s.loc[_viol, "g"] = ((_bks[_viol] - _alns[_viol]) / _alns[_viol] * 100.0).clip(lower=0)

    # ---- Figure 1: certificate-tier distribution ----
    tiers = pd.cut(s["g"], bins=TIER_EDGES, labels=TIER_LABELS)
    counts = tiers.value_counts().reindex(TIER_LABELS).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    bars = ax.bar(TIER_LABELS, counts.values,
                  color=["#1a9850", "#91cf60", "#fee08b", "#fc8d59", "#d73027"],
                  edgecolor="black", linewidth=0.5)
    for b, c in zip(bars, counts.values):
        pct = 100 * c / len(s)
        ax.text(b.get_x() + b.get_width() / 2, c + 4,
                f"{c}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Number of instances")
    ax.set_xlabel("Certified-gap tier")
    ax.set_ylim(0, max(counts.values) * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{outdir}/fig_cert_tiers.pdf")
    plt.close(fig)

    # ---- Figure 2: mean certified gap by family x alpha ----
    piv = s.pivot_table(values="g", index="family", columns="alpha",
                        aggfunc="mean").reindex(STUDY)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    x = np.arange(len(STUDY)); w = 0.26
    colors = {0.25: "#d73027", 0.50: "#fc8d59", 0.75: "#1a9850"}
    for i, a in enumerate(ALPHAS):
        ax.bar(x + (i - 1) * w, piv[a].values, w,
               label=f"α={a:.2f}", color=colors[a], edgecolor="black",
               linewidth=0.4)
    ax.set_xticks(x); ax.set_xticklabels(STUDY)
    ax.set_ylabel("Mean certified gap (%)")
    ax.set_xlabel("Family")
    ax.legend(title=None, frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{outdir}/fig_hardness.pdf")
    plt.close(fig)

    print("Wrote:")
    print(f"  {outdir}/fig_cert_tiers.pdf   tiers={dict(zip(TIER_LABELS, counts.values))}")
    print(f"  {outdir}/fig_hardness.pdf     family x alpha mean cert gap")
    print(piv.round(3).to_string())


if __name__ == "__main__":
    main()
