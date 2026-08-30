"""
build_bpc_subgroups.py — §6.2 fine-grained outcome split against the BPC
baseline (Riera-Ledesma & Salazar-Gonzalez, 2021). Refines the coarse
optimal/incumbent/not_reported split into solver-relevant subgroups:

  A  BPC proves optimal
     A1  recover optimum  (our obj = BKS)
     A2  miss optimum     (our obj < BKS)        -> no added value
  B  BPC incumbent, gap at 1h cap
     B1  improves BKS     (our obj > BKS)
     B2  matches BKS      (our obj = BKS)
     B3  below BKS        (our obj < BKS)
  C  BPC reports no solution                     -> sole solver

Three "incumbent"-class instances come from BPC groups that were only
partially solved (group-level reporting), so no per-instance BPC value is
attributable; they are reported separately and, in the manuscript, grouped
with C by footnote (excluded from the C count and the first-ever tally).

Validity guard: a valid Lagrangian upper bound cannot be below a known
feasible objective. We therefore report the certified gap against
ub_valid = max(best_ub, bks), which only affects the single instance
ED_n045_008_a75_024 (adaptive UB under-shot the BPC-proven optimum by 1).

Source : results/adaptive_master_refined.csv  (+ results/analysis/bpc_times.csv for
         BPC's actual per-group reported CPU time, not its 1h cap).
Usage  : python build_bpc_subgroups.py [--csv results/adaptive_master_refined.csv]
Output : results/analysis/bpc_subgroups_<date>.{txt,csv}
"""
import argparse, os
from datetime import datetime

import numpy as np
import pandas as pd

STUDY = ["B", "C", "D", "EB", "EC", "ED"]


def load(csv):
    d = pd.read_csv(csv)
    s = d[d["family"].isin(STUDY)].copy()
    for c in ["alns_obj", "bks", "best_ub", "final_cert_gap_pct", "alns_runtime_s"]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    bt = pd.read_csv("results/analysis/bpc_times.csv")
    s = s.merge(bt[["family", "n", "alpha", "bpcE_cpu_oa_s"]],
                on=["family", "n", "alpha"], how="left")
    # validity guard: UB >= any known feasible objective
    ub_valid = np.where(s["bks"].notna(),
                        np.maximum(s["best_ub"], s["bks"]), s["best_ub"])
    s["cert_valid"] = (ub_valid - s["alns_obj"]) / s["alns_obj"] * 100.0
    s["cert_valid"] = s["cert_valid"].clip(lower=0.0)
    s["obj_d"] = s["alns_obj"] - s["bks"]
    s["obj_pct"] = np.where(s["bks"] > 0, s["obj_d"] / s["bks"] * 100.0, np.nan)
    return s


def agg(sub):
    return pd.Series({
        "n": len(sub),
        "obj_d": round(sub["obj_d"].mean(), 2),
        "obj_pct": round(sub["obj_pct"].mean(), 3),
        "cert%": round(sub["cert_valid"].mean(), 3),
        "our_rt_s": round(sub["alns_runtime_s"].mean(), 0),
        "bpc_rt_s": round(sub["bpcE_cpu_oa_s"].mean(), 0),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/adaptive_master_refined.csv")
    args = ap.parse_args()
    os.makedirs("results/analysis", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    s = load(args.csv)
    A = s[s.bpc_class_label == "optimal"]
    B = s[s.bpc_class_label == "incumbent"]
    C = s[s.bpc_class_label == "not_reported"]
    blank = lambda df: df["beta_status"].fillna("").str.strip() == ""

    B_real = B[B.beta_status.isin(["BEAT", "TIE", "GAP"])]
    B_amb = B[blank(B)]   # incumbent class, no attributable per-instance BKS
    rows = {
        "A  optimal":            agg(A),
        "A1 recover optimum":    agg(A[A.beta_status == "TIE"]),
        "A2 miss optimum":       agg(A[A.beta_status == "GAP"]),
        "B  incumbent (real)":   agg(B_real),
        "B1 improves BKS":       agg(B[B.beta_status == "BEAT"]),
        "B2 matches BKS":        agg(B[B.beta_status == "TIE"]),
        "B3 below BKS":          agg(B[B.beta_status == "GAP"]),
        "C  not reported":       agg(C),
        "(*) ambiguous, w/ C":   agg(B_amb),
    }
    tab = pd.DataFrame(rows).T

    c_first_ever = int(blank(C).sum())
    c_with_bks = C[~blank(C)]
    c_split = c_with_bks["beta_status"].value_counts().to_dict()

    out = [f"BPC subgroup split — run {stamp}   source {args.csv}",
           f"Study set: {len(s)} instances (B/C/D/EB/EC/ED)",
           "(obj_d/obj_pct = our objective minus BKS; cert% uses validity-guarded UB)",
           "", tab.to_string(),
           "",
           f"C first-ever (no BKS): {c_first_ever}",
           f"C with BKS ({len(c_with_bks)}): {c_split}  [BEAT=improve, TIE=match, GAP=below]"]
    report = "\n".join(out)
    print(report)
    with open(f"results/analysis/bpc_subgroups_{stamp}.txt", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    tab.to_csv(f"results/analysis/bpc_subgroups_{stamp}.csv")
    print(f"\nWrote results/analysis/bpc_subgroups_{stamp}.{{txt,csv}}")


if __name__ == "__main__":
    main()
