"""
build_appendix_A.py — generates the full per-instance ablation table (Appendix A)
from the adaptive-loop ablation results, so every Appendix-A / §6.5.1 number
derives from a committed script rather than a hand-computed value.

Source: results/analysis/ablation_warmmu_<date>.csv  (6 arms A0-A5 x 30 instances,
        produced by run_ablation.py — the adaptive loop).

Usage:
    python build_appendix_A.py [--csv results/analysis/ablation_warmmu_20260621_0558.csv]

Outputs (results/analysis/):
    appendix_A_ablation_table.md    markdown per-instance table (A0-A5 + deltas)
    appendix_A_ablation_table.csv   same, machine-readable
    appendix_A_summary.txt          aggregate means, per-family deltas, stop reasons
"""
import argparse, glob, os

import pandas as pd

ARMS = ["A0", "A1", "A2", "A3", "A4", "A5"]


def main():
    raise SystemExit(
        "build_appendix_A.py is INVALIDATED (2026-08-27): its A0--A5 "
        "ablation design is not a source for any current manuscript claim. "
        "Use build_ablation_summary.py for the redesigned B1--B8+S study; "
        "see docs/REPRODUCIBILITY.md."
    )

    ap = argparse.ArgumentParser()
    default = sorted(glob.glob("results/analysis/ablation_warmmu_*.csv"))
    ap.add_argument("--csv", default=default[-1] if default else None)
    args = ap.parse_args()
    if not args.csv:
        raise SystemExit("No ablation CSV found.")

    d = pd.read_csv(args.csv)
    d["cert"] = pd.to_numeric(d["cert_gap_pct"], errors="coerce")

    piv = d.pivot_table(index=["family", "instance"], columns="arm_id",
                        values="cert").reset_index()
    a0_stop = d[d.arm_id == "A0"].set_index("instance")["stop_reason"]
    for a in ARMS[1:]:
        piv[a + "_d"] = piv[a] - piv["A0"]
    piv = piv.merge(a0_stop.rename("A0_stop"), on="instance")
    piv = piv.sort_values(["family", "instance"])

    # --- per-instance markdown ---
    hdr = ("| Family | Instance | " + " | ".join(ARMS) +
           " | A1-A0 | A4-A0 | A0 stop |")
    sep = "|" + "---|" * (len(ARMS) + 5)
    lines = [hdr, sep]
    for _, r in piv.iterrows():
        cells = " | ".join(f"{r[a]:.3f}" for a in ARMS)
        lines.append(f"| {r['family']} | {r['instance']} | {cells} | "
                     f"{r['A1_d']:+.3f} | {r['A4_d']:+.3f} | {r['A0_stop']} |")
    md = "\n".join(lines)
    with open("results/analysis/appendix_A_ablation_table.md", "w",
              encoding="utf-8") as f:
        f.write(md + "\n")
    piv.round(4).to_csv("results/analysis/appendix_A_ablation_table.csv",
                        index=False)

    # --- aggregate summary ---
    out = []
    out.append(f"Appendix A summary — source {args.csv}")
    out.append(f"Instances: {len(piv)}   Arms: {ARMS}")
    out.append("")
    out.append("Arm aggregate mean cert gap (%):")
    means = {a: round(piv[a].mean(), 4) for a in ARMS}
    for a in ARMS:
        out.append(f"  {a}: {means[a]:.4f}   delta_A0={means[a]-means['A0']:+.4f}")
    out.append("")
    out.append("Per-family delta vs A0 (mean):")
    fam = piv.groupby("family")[[a + "_d" for a in ARMS[1:]]].mean().round(4)
    out.append(fam.to_string())
    out.append("")
    out.append("A0 stop-reason counts:")
    for k, v in piv["A0_stop"].value_counts().items():
        out.append(f"  {k:18s} {v}")
    summary = "\n".join(out)
    with open("results/analysis/appendix_A_summary.txt", "w",
              encoding="utf-8") as f:
        f.write(summary + "\n")

    print(summary)
    print("\nWrote results/analysis/appendix_A_ablation_table.{md,csv}")
    print("Wrote results/analysis/appendix_A_summary.txt")


if __name__ == "__main__":
    main()
