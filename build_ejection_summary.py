"""Recompute the ejection-chain identity reported in the manuscript.

Because the ejection chain is applied only after the adaptive loop, removing it
changes an incumbent by its recorded integral `beta_ec_gain`. Holding the same
certificate fixed changes the certified gap exactly by `beta_ec_gain / UB`.

Usage:
    python build_ejection_summary.py [--csv results/adaptive_master_refined.csv]

Output:
    results/analysis/ejection_summary.txt
    results/analysis/ejection_summary.csv
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

STUDY = {"B", "C", "D", "EB", "EC", "ED"}


def gap_effect(frame: pd.DataFrame) -> pd.Series:
    gain = pd.to_numeric(frame["beta_ec_gain"], errors="coerce").fillna(0.0)
    ub = pd.to_numeric(frame["best_ub"], errors="coerce")
    return 100.0 * gain / ub


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="results/adaptive_master_refined.csv")
    parser.add_argument("--outdir", default="results/analysis")
    args = parser.parse_args()

    frame = pd.read_csv(args.csv)
    frame = frame[frame["family"].isin(STUDY)].copy()
    required = {"beta_ec_gain", "best_ub", "beta_stop_reason", "beta_phases", "final_cert_gap_pct"}
    missing = required.difference(frame.columns)
    if missing:
        raise SystemExit(f"missing required columns: {sorted(missing)}")
    frame["ejection_gap_effect_pp"] = gap_effect(frame)
    frame["ec_gain_num"] = pd.to_numeric(frame["beta_ec_gain"], errors="coerce").fillna(0.0)
    frame["phases_num"] = pd.to_numeric(frame["beta_phases"], errors="coerce").fillna(0)
    frame["gap_num"] = pd.to_numeric(frame["final_cert_gap_pct"], errors="coerce")

    cohorts = {
        "all_study": frame,
        "hard_tail": frame[frame["beta_stop_reason"] == "TIERS_EXHAUSTED"],
        "multi_phase_closed": frame[(frame["phases_num"] > 1) & (frame["gap_num"] <= 1e-12)],
    }
    rows = []
    for cohort, data in cohorts.items():
        rows.append({
            "cohort": cohort,
            "instances": len(data),
            "instances_with_gain": int((data["ec_gain_num"] > 0).sum()),
            "mean_gap_effect_pp": data["ejection_gap_effect_pp"].mean(),
            "proven_optima_depending_on_ec": int(((data["ec_gain_num"] > 0) & (data["gap_num"] <= 1e-12)).sum()),
        })
    out = pd.DataFrame(rows)
    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "ejection_summary.csv")
    txt_path = os.path.join(args.outdir, "ejection_summary.txt")
    out.to_csv(csv_path, index=False)
    lines = ["Ejection-chain identity (certified-gap effect = 100 * ec_gain / UB)", out.to_string(index=False)]
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(lines) + "\n")
    print("\n\n".join(lines))
    print(f"\nWrote {csv_path}\nWrote {txt_path}")


if __name__ == "__main__":
    main()
