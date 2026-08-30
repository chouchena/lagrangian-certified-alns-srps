"""
build_bpc_comparison.py — §6.2 comparison of our adaptive results against the
BPC baseline (Riera-Ledesma & Salazar-Gonzalez, 2021), aggregated so the
main-text table is compact and every number derives from a committed script.

Source: results/adaptive_master_refined.csv (post-refinement columns final_cert_gap_pct /
beta_status / alns_runtime_s; BPC reference columns bpc_oa_gap_pct /
bpc_class_label, carried verbatim from the baseline paper).

Two aggregations:
  (A) by BPC outcome class  (optimal / incumbent / not_reported)
  (B) by family

Usage:  python build_bpc_comparison.py [--csv results/adaptive_master_refined.csv]
Output: results/analysis/bpc_comparison_<date>.{txt,csv}
"""
import argparse, os
from datetime import datetime

import numpy as np
import pandas as pd

STUDY = ["B", "C", "D", "EB", "EC", "ED"]


def agg(df):
    g = pd.to_numeric(df["final_cert_gap_pct"], errors="coerce")
    rt = pd.to_numeric(df["alns_runtime_s"], errors="coerce")
    st = df["beta_status"].fillna("").str.strip()
    bpc = pd.to_numeric(df["bpc_oa_gap_pct"], errors="coerce")
    return pd.Series({
        "instances": len(df),
        "bpc_mean_gap%": round(bpc.mean(), 3),
        "our_mean_cert%": round(g.mean(), 3),
        "our_exact": int((g == 0).sum()),
        "BEAT": int((st == "BEAT").sum()),
        "TIE": int((st == "TIE").sum()),
        "GAP": int((st == "GAP").sum()),
        "no_BKS": int((st == "").sum()),
        "mean_rt_s": round(rt.mean(), 0),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/adaptive_master_refined.csv")
    args = ap.parse_args()
    os.makedirs("results/analysis", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    d = pd.read_csv(args.csv)
    s = d[d["family"].isin(STUDY)].copy()

    by_class = (s.groupby("bpc_class_label").apply(agg, include_groups=False)
                .reindex(["optimal", "incumbent", "not_reported"]))
    by_family = s.groupby("family").apply(agg, include_groups=False).reindex(STUDY)

    out = []
    out.append(f"BPC comparison — run {stamp}   source {args.csv}")
    out.append(f"Study set: {len(s)} instances (B/C/D/EB/EC/ED)")
    out.append("")
    out.append("== (A) By BPC outcome class ==")
    out.append(by_class.to_string())
    out.append("")
    out.append("== (B) By family ==")
    out.append(by_family.to_string())
    report = "\n".join(out)
    print(report)

    txt = f"results/analysis/bpc_comparison_{stamp}.txt"
    with open(txt, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    pd.concat({"by_class": by_class, "by_family": by_family}).to_csv(
        f"results/analysis/bpc_comparison_{stamp}.csv")
    print(f"\nWrote {txt}")
    print(f"Wrote results/analysis/bpc_comparison_{stamp}.csv")


if __name__ == "__main__":
    main()
