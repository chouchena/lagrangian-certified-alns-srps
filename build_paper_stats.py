"""
build_paper_stats.py — single source of truth for the paper's headline numbers.

Every §6.1–§6.3 figure (certified-gap summary, certificate tiers, BEAT/TIE/GAP
counts and magnitudes, first-ever solutions, runtime) is derived here from the
canonical adaptive results so that no number is hand-computed in the prose.

Scope: 660-instance study set — families B, C, D, EB, EC, ED (K=2,3,4).
The default input is the post-refinement canonical series. Source column:
`final_cert_gap_pct`, not `master_cert_gap_pct` (the superseded non-adaptive
solver, retained in the CSV only for reference).

Usage:
    python build_paper_stats.py [--csv results/adaptive_master_refined.csv]

Outputs (results/analysis/):
    paper_stats_<date>.txt   human-readable report (mirrors stdout)
    paper_stats_<date>.json  machine-readable numbers for downstream checks
"""
import argparse, json, os, sys
from datetime import datetime

import numpy as np
import pandas as pd

STUDY_FAMILIES = ["B", "C", "D", "EB", "EC", "ED"]
TIER_EDGES = [-1e-9, 1e-9, 0.5, 1.0, 2.0, float("inf")]
TIER_LABELS = ["exact", "<0.5%", "0.5-1%", "1-2%", ">2%"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/adaptive_master_refined.csv")
    args = ap.parse_args()

    os.makedirs("results/analysis", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    txt_path = f"results/analysis/paper_stats_{stamp}.txt"
    json_path = f"results/analysis/paper_stats_{stamp}.json"

    df = pd.read_csv(args.csv)
    s = df[df["family"].isin(STUDY_FAMILIES)].copy()
    s["g"] = pd.to_numeric(s["final_cert_gap_pct"], errors="coerce")
    s["rt"] = pd.to_numeric(s["alns_runtime_s"], errors="coerce")
    s["status"] = s["beta_status"].fillna("").str.strip()
    s["bksf"] = pd.to_numeric(s["bks"], errors="coerce")
    s["alns"] = pd.to_numeric(s["alns_obj"], errors="coerce")
    s["ubf"] = pd.to_numeric(s["best_ub"], errors="coerce")
    # Validity guard: a valid upper bound is never below a known feasible
    # objective. On the single instance where the adaptive UB underran the
    # BPC-proven optimum, recompute the certified gap against that optimum so
    # the instance is not miscounted as proven optimal.
    _viol = s["bksf"].notna() & (s["ubf"] < s["bksf"])
    s.loc[_viol, "g"] = ((s.loc[_viol, "bksf"] - s.loc[_viol, "alns"])
                         / s.loc[_viol, "alns"] * 100.0).clip(lower=0)

    out, R = [], {}

    def emit(line=""):
        out.append(line)

    emit(f"Paper headline statistics — run {stamp}")
    emit(f"Source: {args.csv}  column=final_cert_gap_pct  (adaptive loop)")
    emit(f"Study set: {len(s)} instances (B/C/D/EB/EC/ED, K=2,3,4)")
    emit("")

    # --- certified-gap summary ---
    g = s["g"]
    R["n"] = int(len(s))
    R["cert_mean"] = round(float(g.mean()), 4)
    R["cert_median"] = round(float(g.median()), 4)
    R["cert_max"] = round(float(g.max()), 4)
    R["cert_max_instance"] = str(s.loc[g.idxmax(), "instance"])
    R["proven_optimal"] = int((g == 0).sum())
    # 95% CI for the mean (normal approx; n=660 so z=1.96 ≈ t). Reported in §6.1.
    _sem = float(g.sem())
    R["cert_sd"] = round(float(g.std(ddof=1)), 4)
    R["cert_sem"] = round(_sem, 4)
    R["cert_ci95"] = [round(R["cert_mean"] - 1.96 * _sem, 4),
                      round(R["cert_mean"] + 1.96 * _sem, 4)]
    emit("== Certified gap (%) ==")
    emit(f"  mean={R['cert_mean']}  median={R['cert_median']}  "
         f"max={R['cert_max']} ({R['cert_max_instance']})")
    emit(f"  95% CI for mean = [{R['cert_ci95'][0]}, {R['cert_ci95'][1]}]  "
         f"(sd={R['cert_sd']}, sem={R['cert_sem']})")
    emit(f"  proven optimal (gap=0): {R['proven_optimal']} "
         f"({100*R['proven_optimal']/len(s):.1f}%)")

    # --- certificate tiers ---
    tiers = pd.cut(g, bins=TIER_EDGES, labels=TIER_LABELS)
    tc = tiers.value_counts().reindex(TIER_LABELS).fillna(0).astype(int)
    R["tiers"] = {k: int(v) for k, v in tc.items()}
    R["within_0.5pct"] = round(100 * float((g < 0.5).mean()), 1)
    R["within_2pct"] = round(100 * float((g < 2).mean()), 1)
    emit("")
    emit("== Certificate tiers ==")
    for k in TIER_LABELS:
        emit(f"  {k:8s} {tc[k]:4d}  {100*tc[k]/len(s):5.1f}%")
    emit(f"  within 0.5% = {R['within_0.5pct']}%   within 2% = {R['within_2pct']}%")

    # --- BEAT / TIE / GAP / first-ever ---
    st = s["status"]
    R["beat"] = int((st == "BEAT").sum())
    R["tie"] = int((st == "TIE").sum())
    R["gap"] = int((st == "GAP").sum())
    # First-ever = no prior solution from anyone: blank BKS AND BPC reported
    # nothing for the group. The few blank-BKS instances whose BPC group was
    # only partially solved are ambiguous (a BKS may exist) and are excluded.
    _nr = s["bpc_class_label"] == "not_reported"
    R["first_ever"] = int(((st == "") & _nr).sum())
    R["ambiguous_partial_group"] = int(((st == "") & ~_nr).sum())
    R["with_bks"] = R["beat"] + R["tie"] + R["gap"]
    R["beat_plus_tie"] = R["beat"] + R["tie"]
    beat = s[st == "BEAT"]
    gap = s[st == "GAP"]
    beat_pct = 100 * (beat["alns"] - beat["bksf"]) / beat["bksf"]
    gap_pct = 100 * (gap["bksf"] - gap["alns"]) / gap["bksf"]
    R["beat_pct"] = [round(float(beat_pct.min()), 3),
                     round(float(beat_pct.median()), 3),
                     round(float(beat_pct.max()), 3)]
    R["gap_shortfall_pct"] = [round(float(gap_pct.min()), 3),
                              round(float(gap_pct.median()), 3),
                              round(float(gap_pct.max()), 3)]
    emit("")
    emit("== Comparison with published BKS ==")
    emit(f"  BEAT={R['beat']}  TIE={R['tie']}  GAP={R['gap']}  "
         f"first-ever(no BKS, BPC-unreported)={R['first_ever']}  "
         f"ambiguous(partial-group)={R['ambiguous_partial_group']}")
    emit(f"  BEAT+TIE = {R['beat_plus_tie']}/{R['with_bks']} "
         f"({100*R['beat_plus_tie']/R['with_bks']:.1f}% of with-BKS)")
    emit(f"  BEAT magnitude %  min/median/max = {R['beat_pct']}")
    emit(f"  GAP shortfall %   min/median/max = {R['gap_shortfall_pct']}")
    emit(f"  first-ever by family: "
         f"{s[(st=='') & _nr].groupby('family').size().to_dict()}")

    # --- stop reasons ---
    R["stop_reasons"] = {k: int(v) for k, v in
                         s["beta_stop_reason"].value_counts().items()}
    emit("")
    emit("== Adaptive-loop stop reasons ==")
    for k, v in R["stop_reasons"].items():
        emit(f"  {k:18s} {v}")

    # --- runtime ---
    rt = s["rt"]
    R["runtime_s"] = {"median": round(float(rt.median()), 1),
                      "mean": round(float(rt.mean()), 1),
                      "p75": round(float(rt.quantile(0.75)), 1),
                      "max": round(float(rt.max()), 1)}
    emit("")
    emit("== ALNS runtime (s) ==")
    emit(f"  median={R['runtime_s']['median']}  mean={R['runtime_s']['mean']}  "
         f"P75={R['runtime_s']['p75']}  max={R['runtime_s']['max']}")

    # --- per-family ---
    emit("")
    emit("== Per-family certified gap (%) ==")
    fam = s.groupby("family")["g"].agg(["count", "mean", "median", "max"]).round(4)
    emit(fam.to_string())
    R["per_family"] = {k: {kk: round(float(vv), 4) for kk, vv in v.items()}
                       for k, v in fam.to_dict("index").items()}

    report = "\n".join(out)
    print(report)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2)
    print(f"\nWrote {txt_path}\nWrote {json_path}")


if __name__ == "__main__":
    main()
