"""
build_adaptive_master.py

Builds results/adaptive_master.csv by merging:
  - Instance metadata + BPC data from results/master_results.csv
  - Adaptive run results from results/adaptive_full_<timestamp>.csv

For study families (B/C/D/EB/EC/ED):
  final_cert_gap_pct  <- beta_gap_pct    (adaptive certified gap — Tobit reads this)
  alns_obj            <- beta_obj         (adaptive best primal)
  alns_runtime_s      <- beta_total_rt_s  (adaptive total RT)
  best_ub             <- beta_ub          (floored Lagrangian UB from adaptive run)
  alns_lag_proven_optimal <- (beta_gap_pct == 0.0)

Old master results preserved in master_* columns for cross-check.

For A/EA families (not in adaptive run): copied verbatim from master_results.csv.

Usage:
    python build_adaptive_master.py
    python build_adaptive_master.py --adaptive results/adaptive_full_20260619_0917.csv
"""
from __future__ import annotations
import argparse, csv, glob, math, os, sys

RESULTS_DIR   = "results"
MASTER_CSV    = os.path.join(RESULTS_DIR, "master_results.csv")
OUT_CSV       = os.path.join(RESULTS_DIR, "adaptive_master.csv")
STUDY_FAMILIES = {"B", "C", "D", "EB", "EC", "ED"}


def _find_adaptive_csv(explicit: str | None) -> str:
    if explicit and os.path.exists(explicit):
        return explicit
    candidates = sorted(glob.glob(os.path.join(RESULTS_DIR, "adaptive_full_*.csv")))
    # Exclude phases CSVs
    candidates = [c for c in candidates if "_phases" not in c]
    if not candidates:
        sys.exit("ERROR: No adaptive_full_*.csv found in results/. Run the adaptive loop first.")
    return candidates[-1]  # most recent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adaptive", default=None,
                        help="Path to adaptive run CSV (default: latest adaptive_full_*.csv)")
    parser.add_argument("--allow-partial", action="store_true",
                        help="Allow building from a partial run (< 660 study instances)")
    args = parser.parse_args()

    adaptive_path = _find_adaptive_csv(args.adaptive)
    print(f"Adaptive CSV : {adaptive_path}")
    print(f"Master CSV   : {MASTER_CSV}")
    print(f"Output       : {OUT_CSV}")
    print()

    # ── Load master ────────────────────────────────────────────────────────────
    master = {}
    master_fieldnames = []
    with open(MASTER_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        master_fieldnames = reader.fieldnames
        for r in reader:
            master[r["instance"].strip()] = r

    # ── Load adaptive results ──────────────────────────────────────────────────
    adaptive = {}
    with open(adaptive_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            adaptive[r["instance"].strip()] = r

    study_in_adaptive = {k: v for k, v in adaptive.items()
                         if v["family"].strip() in STUDY_FAMILIES}
    print(f"Master rows        : {len(master)}")
    print(f"Adaptive rows total: {len(adaptive)}")
    print(f"Adaptive study set : {len(study_in_adaptive)} / 660")

    if len(study_in_adaptive) < 660 and not args.allow_partial:
        sys.exit(
            f"ERROR: Adaptive run is only {len(study_in_adaptive)}/660 complete.\n"
            f"       Wait for completion or pass --allow-partial to build anyway."
        )

    # ── Output schema ──────────────────────────────────────────────────────────
    out_fields = [
        # Identifiers
        "instance", "family", "n", "alpha", "group_id",
        # Reference
        "bks",
        # BPC data (from paper tables — unchanged)
        "bpc_oa_gap_pct", "bpc_n_solved", "bpc_group_count",
        "bpc_class", "bpc_class_label", "bpc_note",
        # Old master results (preserved for cross-check)
        "master_obj", "master_cert_gap_pct", "master_rt_s", "master_status",
        # Adaptive primal results
        "alns_obj", "alns_runtime_s", "best_ub",
        # KEY outcome for Tobit / quality analysis
        "final_cert_gap_pct",
        # Adaptive metadata
        "alns_lag_proven_optimal",
        "beta_stop_reason", "beta_phases", "beta_ec_gain",
        # BKS comparison
        "beta_vs_bks", "beta_status",
        # Improvement over old master
        "beta_vs_master",
    ]

    out_rows = []
    n_study_written = n_aea_written = n_missing = 0

    for label, mrow in master.items():
        family = mrow["family"].strip()
        orow = {f: "" for f in out_fields}

        # ── Identifiers + BPC data (always from master) ──────────────────────
        for f in ["instance", "family", "n", "alpha", "group_id", "bks",
                  "bpc_oa_gap_pct", "bpc_n_solved", "bpc_group_count",
                  "bpc_class", "bpc_class_label", "bpc_note"]:
            orow[f] = mrow.get(f, "")

        # ── Old master results (always preserved) ─────────────────────────────
        orow["master_obj"]          = mrow.get("alns_obj", "")
        orow["master_cert_gap_pct"] = mrow.get("final_cert_gap_pct", "")
        orow["master_rt_s"]         = mrow.get("alns_runtime_s", "")
        orow["master_status"]       = mrow.get("alns_status", "")

        if family in STUDY_FAMILIES:
            arow = adaptive.get(label)
            if arow is None:
                # Adaptive run hasn't completed this instance yet
                # Fall back to master for Tobit continuity
                orow["alns_obj"]              = mrow.get("alns_obj", "")
                orow["alns_runtime_s"]        = mrow.get("alns_runtime_s", "")
                orow["best_ub"]               = mrow.get("best_ub", "")
                orow["final_cert_gap_pct"]    = mrow.get("final_cert_gap_pct", "")
                orow["alns_lag_proven_optimal"] = mrow.get("alns_lag_proven_optimal", "")
                orow["beta_stop_reason"]      = "NOT_RUN"
                n_missing += 1
            else:
                gap_s = arow.get("beta_gap_pct", "").strip()
                gap   = float(gap_s) if gap_s else None
                ub_s  = arow.get("beta_ub", "").strip()

                orow["alns_obj"]           = arow.get("beta_obj", "")
                orow["alns_runtime_s"]     = arow.get("beta_total_rt_s", "")
                orow["best_ub"]            = ub_s
                orow["final_cert_gap_pct"] = gap_s
                orow["alns_lag_proven_optimal"] = str(gap == 0.0) if gap is not None else ""
                orow["beta_stop_reason"]   = arow.get("beta_stop_reason", "")
                orow["beta_phases"]        = arow.get("beta_phases", "")
                orow["beta_ec_gain"]       = arow.get("beta_ec_gain", "")
                orow["beta_vs_bks"]        = arow.get("beta_vs_bks", "")
                orow["beta_status"]        = arow.get("beta_status", "")
                orow["beta_vs_master"]     = arow.get("beta_vs_master", "")
                n_study_written += 1

        else:
            # A / EA families: copy verbatim from master
            orow["alns_obj"]           = mrow.get("alns_obj", "")
            orow["alns_runtime_s"]     = mrow.get("alns_runtime_s", "")
            orow["best_ub"]            = mrow.get("best_ub", "")
            orow["final_cert_gap_pct"] = mrow.get("final_cert_gap_pct", "")
            orow["alns_lag_proven_optimal"] = mrow.get("alns_lag_proven_optimal", "")
            n_aea_written += 1

        out_rows.append(orow)

    # ── Write output ───────────────────────────────────────────────────────────
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        w.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} rows -> {OUT_CSV}")
    print(f"  Study families (B/C/D/EB/EC/ED) : {n_study_written} adaptive  |  {n_missing} fallback-to-master")
    print(f"  A/EA families                    : {n_aea_written} (copied from master)")

    if n_missing:
        print(f"\n  WARNING: {n_missing} study instances missing from adaptive run — using old master gaps.")
        print(f"           Tobit results will be mixed (adaptive + old). Re-run when complete.")
    else:
        print(f"\n  All 660 study instances have adaptive results. Tobit will be fully adaptive.")


if __name__ == "__main__":
    main()
