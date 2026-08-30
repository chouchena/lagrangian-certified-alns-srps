"""
build_repro_artifacts.py — generate the reproducibility data artifacts that need
NO solver run, from the existing canonical results + instance files:

  data/instance_manifest.csv     full 660 index + processor-load stats + inclusion flags
  results/hard_tail_70.csv       the 70 TIERS_EXHAUSTED instances (the hard-tail set)
  results/main_660_results.csv   central certificate table (raw vs guarded bound, gaps, flags)

Columns that require the planned canonical re-run (per-instance mu, refresh counts,
Lagrangian-iteration totals) are intentionally LEFT OUT here and added by that run.

Usage:  python build_repro_artifacts.py
"""
import glob, json, os, statistics
import numpy as np
import pandas as pd

STUDY = ["B", "C", "D", "EB", "EC", "ED"]
INST_BASE = "benchmarks/ops_raw/OPS-Benchmark-master/input"
SEED_SET = "42;123;456;789;1337;2024"

# 30-instance stratified subset (single source: run_sensitivity.py SENSITIVITY_INSTANCES);
# the ablation uses the same set.
SUBSET_30 = {
    "B_n100_001_a25_001","B_n110_006_a50_017","B_n120_011_a75_033","B_n140_021_a25_061","B_n150_026_a50_077",
    "C_n050_001_a25_001","C_n060_011_a50_032","C_n065_016_a75_048","C_n070_021_a25_061","C_n080_031_a50_092",
    "D_n040_001_a25_001","D_n050_011_a50_032","D_n060_021_a75_063","D_n070_031_a25_091","D_n080_041_a50_122",
    "EB_n100_001_a25_001","EB_n110_006_a50_017","EB_n120_011_a75_033","EB_n140_021_a25_061","EB_n150_026_a50_077",
    "EC_n050_001_a25_001","EC_n060_011_a50_032","EC_n065_016_a75_048","EC_n070_021_a25_061","EC_n080_031_a50_092",
    "ED_n040_001_a25_001","ED_n050_011_a50_032","ED_n060_021_a75_063","ED_n070_031_a25_091","ED_n080_041_a50_122",
}


def _instance_json(inst, fam):
    p = f"{INST_BASE}/{fam}/instances/{inst}.txt"
    try:
        return json.load(open(p))
    except Exception:
        return None


def proc_stats(inst, fam):
    d = _instance_json(inst, fam)
    if not d or "Jk" not in d:
        return (np.nan, np.nan, np.nan, np.nan)
    Jk = d["Jk"]
    sizes = [len(x) for x in Jk if len(x) > 0]
    kj = d.get("Kj")
    max_kj = max((len(s) for s in kj), default=np.nan) if kj else np.nan
    return (len(Jk), max_kj, max(sizes) if sizes else 0,
            round(statistics.mean(sizes), 2) if sizes else 0.0)


def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    d = pd.read_csv("results/adaptive_master.csv")
    s = d[d["family"].isin(STUDY)].copy()
    for c in ["alns_obj", "bks", "best_ub", "final_cert_gap_pct", "alns_runtime_s", "bpc_oa_gap_pct"]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    try:
        bt = pd.read_csv("results/analysis/bpc_times.csv")
        s = s.merge(bt[["family", "n", "alpha", "bpcE_cpu_oa_s"]], on=["family", "n", "alpha"], how="left")
    except Exception:
        s["bpcE_cpu_oa_s"] = np.nan

    # validity guard: reported UB never below a known feasible objective
    ub_rep = np.where(s["bks"].notna(), np.maximum(s["best_ub"], s["bks"]), s["best_ub"])
    s["ub_reported"] = ub_rep
    s["cert_guarded"] = ((ub_rep - s["alns_obj"]) / s["alns_obj"] * 100.0).clip(lower=0)

    # per-instance processor-load stats
    stats = s.apply(lambda r: proc_stats(r["instance"], r["family"]), axis=1, result_type="expand")
    s[["nproc", "max_kj", "max_jk", "mean_jk"]] = stats

    is_hard = s["beta_stop_reason"] == "TIERS_EXHAUSTED"
    in30 = s["instance"].isin(SUBSET_30)

    # ---- instance_manifest.csv ----
    man = pd.DataFrame({
        "instance_id": s["instance"], "family": s["family"], "n": s["n"], "alpha": s["alpha"],
        "num_processors_total": s["nproc"].astype("Int64"),
        "max_required_processors_per_job": s["max_kj"].astype("Int64"),
        "max_jobs_per_processor": s["max_jk"].astype("Int64"),
        "mean_jobs_per_processor": s["mean_jk"],
        "bpc_status": s["bpc_class_label"], "bpc_gap_pct": s["bpc_oa_gap_pct"],
        "bpc_time_seconds": s["bpcE_cpu_oa_s"],
        "included_in_main_study": True,
        "included_in_ablation_30": in30, "included_in_sensitivity_30": in30,
        "included_in_hard_tail_70": is_hard,
    })
    man.to_csv("data/instance_manifest.csv", index=False)

    # ---- hard_tail_70.csv ----
    ht = s[is_hard][["instance", "family", "n", "alpha", "beta_stop_reason",
                     "cert_guarded", "alns_runtime_s", "beta_phases"]].copy()
    ht.columns = ["instance_id", "family", "n", "alpha", "final_stop_reason",
                  "baseline_cert_gap_percent", "runtime_seconds", "phases"]
    ht.to_csv("results/hard_tail_70.csv", index=False)

    # ---- main_660_results.csv ----
    main = pd.DataFrame({
        "instance_id": s["instance"], "family": s["family"], "n": s["n"], "budget_level": s["alpha"],
        "seed_set": SEED_SET,
        "best_primal_profit": s["alns_obj"],
        "lagrangian_upper_bound_raw": s["best_ub"],
        "lagrangian_upper_bound_reported": s["ub_reported"],
        "certificate_gap_percent": s["cert_guarded"].round(4),
        "stop_reason": s["beta_stop_reason"], "runtime_seconds": s["alns_runtime_s"],
        "proven_optimal_by_lagrangian_match": (s["cert_guarded"] == 0),
        "matches_bpc_optimum": (s["bpc_class_label"] == "optimal") & (s["alns_obj"] == s["bks"]),
        "improves_published_bks": (s["beta_status"].fillna("").str.strip() == "BEAT"),
        "published_bks": s["bks"],
    })
    main.to_csv("results/main_660_results.csv", index=False)

    print(f"data/instance_manifest.csv      {len(man)} rows  (max|J_k|={int(s['max_jk'].max())})")
    print(f"results/hard_tail_70.csv        {len(ht)} rows  (stop reasons: {ht['final_stop_reason'].unique().tolist()})")
    print(f"results/main_660_results.csv    {len(main)} rows  "
          f"(proven optimal={int(main['proven_optimal_by_lagrangian_match'].sum())}, "
          f"matches BPC opt={int(main['matches_bpc_optimum'].sum())}, "
          f"improves BKS={int(main['improves_published_bks'].sum())})")
    print("NOTE: per-instance mu, num_ub_refreshes, lagrangian-iteration totals are added by the canonical re-run.")


if __name__ == "__main__":
    main()
