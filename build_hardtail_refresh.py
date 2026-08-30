"""
build_hardtail_refresh.py — §6.5 hard-tail UB-refresh evidence (tab:hardtail-refresh).

Quantifies the effect of the *in-loop* Lagrangian re-bound on the 70 hard-tail
instances (the TIERS_EXHAUSTED set) by comparing two arms produced with the
run_adaptive_full.py flags:

    H0  (full)        python run_adaptive_full.py --subset results/hard_tail_70.csv \
                              --save-certificates --tag hardtail_H0
    H1a (no refresh)  python run_adaptive_full.py --subset results/hard_tail_70.csv \
                              --no-refresh --tag hardtail_H1a

Both arms start from the same initial (master) upper bound; H0 re-tightens it
in-loop on stall, H1a never does. The per-instance certified-gap difference

    Δgap = gap(H1a) − gap(H0)        (positive ⇒ in-loop refresh tightened)

isolates the contribution the fixed-bound ablation (run_ablation.py arm A3)
cannot show by construction. This is the direct evidence for the §6.5 claim.

Outputs (to results/analysis/):
    hardtail_refresh_<ts>.csv   per-instance gaps + Δ
    hardtail_refresh_<ts>.txt   aggregate summary
    hardtail_refresh_<ts>.tex   ready-to-paste LaTeX (tab:hardtail-refresh)

Usage:
    python build_hardtail_refresh.py                       # auto-detect latest H0/H1a CSVs
    python build_hardtail_refresh.py --h0 <csv> --h1a <csv>
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)


def _latest(pattern: str) -> str | None:
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def _load(path: str) -> dict:
    """Return {instance: row} keyed by instance name."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["instance"].strip()] = r
    return out


def _f(row: dict, key: str):
    v = (row.get(key) or "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h0", default=None, help="H0 (full) summary CSV.")
    ap.add_argument("--h1a", default=None, help="H1a (no-refresh) summary CSV.")
    ap.add_argument("--outdir", default=os.path.join("results", "analysis"))
    args = ap.parse_args()

    h0_path  = args.h0  or _latest(os.path.join("results", "adaptive_full_*hardtail_H0.csv"))
    h1a_path = args.h1a or _latest(os.path.join("results", "adaptive_full_*hardtail_H1a.csv"))

    if not h0_path or not h1a_path:
        raise SystemExit(
            "Could not locate both arms. Run the two experiments first:\n"
            "  python run_adaptive_full.py --subset results/hard_tail_70.csv "
            "--save-certificates --tag hardtail_H0\n"
            "  python run_adaptive_full.py --subset results/hard_tail_70.csv "
            "--no-refresh --tag hardtail_H1a\n"
            f"(found H0={h0_path}, H1a={h1a_path})")

    h0  = _load(h0_path)
    h1a = _load(h1a_path)
    common = sorted(set(h0) & set(h1a))
    if not common:
        raise SystemExit("No overlapping instances between the two arms.")

    rows = []
    for inst in common:
        g0  = _f(h0[inst],  "beta_gap_pct")
        g1  = _f(h1a[inst], "beta_gap_pct")
        if g0 is None or g1 is None:
            continue
        rows.append({
            "instance": inst,
            "family":   h0[inst].get("family", "").strip(),
            "n":        h0[inst].get("n", "").strip(),
            "alpha":    h0[inst].get("alpha", "").strip(),
            "gap_full":      g0,
            "gap_norefresh": g1,
            "dgap":          g1 - g0,
            "refreshes":     _f(h0[inst], "beta_num_ub_refreshes"),
        })

    dgaps = [r["dgap"] for r in rows]
    improved  = [r for r in rows if r["dgap"] > 1e-9]
    unchanged = [r for r in rows if abs(r["dgap"]) <= 1e-9]
    worsened  = [r for r in rows if r["dgap"] < -1e-9]

    def _crossings(thr):
        # H1a at/above threshold, H0 strictly below it
        return sum(1 for r in rows if r["gap_norefresh"] >= thr > r["gap_full"])
    to_1   = _crossings(1.0)
    to_05  = _crossings(0.5)
    to_exact = sum(1 for r in rows
                   if r["gap_norefresh"] > 1e-9 and r["gap_full"] <= 1e-9)

    os.makedirs(args.outdir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M")
    base = os.path.join(args.outdir, f"hardtail_refresh_{ts}")

    # ---- per-instance CSV ---------------------------------------------------
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["instance", "family", "n", "alpha",
                                          "gap_full", "gap_norefresh", "dgap", "refreshes"])
        w.writeheader()
        w.writerows(rows)

    # ---- aggregate summary --------------------------------------------------
    mean_full = statistics.mean(r["gap_full"] for r in rows)
    mean_nore = statistics.mean(r["gap_norefresh"] for r in rows)
    lines = [
        f"Hard-tail in-loop UB-refresh evidence — {ts}",
        f"H0  (full)       : {h0_path}",
        f"H1a (no refresh) : {h1a_path}",
        f"Instances compared: {len(rows)}",
        "",
        f"Mean certified gap  — full {mean_full:.3f}%   no-refresh {mean_nore:.3f}%",
        f"Mean   Δgap (reduction by refresh): {statistics.mean(dgaps):+.4f} pp",
        f"Median Δgap                        : {statistics.median(dgaps):+.4f} pp",
        f"Max    Δgap                        : {max(dgaps):+.4f} pp",
        f"Min    Δgap                        : {min(dgaps):+.4f} pp",
        "",
        f"Improved by refresh  : {len(improved)} / {len(rows)}",
        f"Unchanged            : {len(unchanged)} / {len(rows)}",
        f"Worsened             : {len(worsened)} / {len(rows)}",
        "",
        f"Threshold crossings (no-refresh -> full):",
        f"  → below 1.0% : {to_1}",
        f"  → below 0.5% : {to_05}",
        f"  → exact (0%) : {to_exact}",
    ]
    summary = "\n".join(lines)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(summary + "\n")

    # ---- LaTeX table (ready to paste) ---------------------------------------
    tex = (
        "% Generated by build_hardtail_refresh.py — do not edit by hand.\n"
        "\\begin{table}[t]\n\\centering\n"
        "\\caption{Effect of the in-loop Lagrangian re-bound on the 70 hard-tail "
        "instances (TIERS\\_EXHAUSTED). Both arms start from the same initial "
        "upper bound; the no-refresh arm never re-tightens it. "
        "$\\Delta\\text{gap}=\\text{gap}_{\\text{no-refresh}}-\\text{gap}_{\\text{full}}$.}\n"
        "\\label{tab:hardtail-refresh}\n"
        "\\begin{tabular}{lr}\n\\hline\n"
        "Quantity & Value \\\\\n\\hline\n"
        f"Instances & {len(rows)} \\\\\n"
        f"Mean certified gap, full & {mean_full:.3f}\\% \\\\\n"
        f"Mean certified gap, no-refresh & {mean_nore:.3f}\\% \\\\\n"
        f"Mean gap reduction $\\Delta$ & {statistics.mean(dgaps):.4f} pp \\\\\n"
        f"Median gap reduction $\\Delta$ & {statistics.median(dgaps):.4f} pp \\\\\n"
        f"Max gap reduction $\\Delta$ & {max(dgaps):.4f} pp \\\\\n"
        f"Instances improved / unchanged / worsened & "
        f"{len(improved)} / {len(unchanged)} / {len(worsened)} \\\\\n"
        f"Crossings to $<$1\\% / $<$0.5\\% / exact & "
        f"{to_1} / {to_05} / {to_exact} \\\\\n"
        "\\hline\n\\end{tabular}\n\\end{table}\n"
    )
    with open(base + ".tex", "w", encoding="utf-8") as f:
        f.write(tex)

    print(summary)
    print()
    print(f"Wrote:\n  {base}.csv\n  {base}.txt\n  {base}.tex")


if __name__ == "__main__":
    main()
