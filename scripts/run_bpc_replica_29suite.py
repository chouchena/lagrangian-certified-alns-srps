from __future__ import annotations

import csv
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "dev_bpc_replica" / "run_bpc_replica_experiment.py"
OUT_ANALYSIS = ROOT / "results" / "analysis"


@dataclass
class RunSpec:
    stage: str
    run_id: str
    args: List[str]


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def run_cmd(cmd: List[str]) -> str:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "Command failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{p.stdout}\n"
            f"stderr:\n{p.stderr}"
        )
    for line in p.stdout.splitlines()[::-1]:
        if line.strip().startswith("CSV:"):
            return line.split("CSV:", 1)[1].strip()
    raise RuntimeError(f"Could not find CSV path in output:\n{p.stdout}")


def to_f(v: str):
    try:
        return float(v)
    except Exception:
        return None


def summarize(csv_path: Path) -> Dict[str, float]:
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig", newline="")))
    n = len(rows)
    d_obj = [to_f(r.get("delta_ref", "")) for r in rows]
    d_rt = [to_f(r.get("delta_rt_s", "")) for r in rows]
    d_gap = [to_f(r.get("delta_gap_pct", "")) for r in rows]
    f_gap = [to_f(r.get("final_gap_pct", "")) for r in rows]

    d_obj = [x for x in d_obj if x is not None]
    d_rt = [x for x in d_rt if x is not None]
    d_gap = [x for x in d_gap if x is not None]
    f_gap = [x for x in f_gap if x is not None]

    stop_counts: Dict[str, int] = {}
    for r in rows:
        s = r.get("stop_reason", "")
        stop_counts[s] = stop_counts.get(s, 0) + 1

    return {
        "n": n,
        "mean_delta_obj": (sum(d_obj) / len(d_obj)) if d_obj else 0.0,
        "mean_delta_rt_s": (sum(d_rt) / len(d_rt)) if d_rt else 0.0,
        "mean_delta_gap_pp": (sum(d_gap) / len(d_gap)) if d_gap else 0.0,
        "mean_final_gap_pct": (sum(f_gap) / len(f_gap)) if f_gap else 0.0,
        "max_final_gap_pct": max(f_gap) if f_gap else 0.0,
        "within_0p2_pct": (100.0 * sum(x < 0.2 for x in f_gap) / len(f_gap)) if f_gap else 0.0,
        "obj_wins": sum(x < 0 for x in d_obj),
        "obj_losses": sum(x > 0 for x in d_obj),
        "rt_wins": sum(x < 0 for x in d_rt),
        "rt_losses": sum(x > 0 for x in d_rt),
        "gap_wins": sum(x < 0 for x in d_gap),
        "gap_losses": sum(x > 0 for x in d_gap),
        "stops": stop_counts,
    }


def common_args() -> List[str]:
    return [
        "--workers", "4",
        "--phase-rt", "10",
        "--abs-cap", "20",
        "--gap-threshold", "0.003",
        "--lag-max-iter", "40",
        "--lag-max-time", "5",
    ]


def specs() -> List[RunSpec]:
    C = common_args()
    out: List[RunSpec] = []

    # Stage A (3)
    out.append(RunSpec("A", "A1_control", C + ["--tag", "A1_control", "--no-bpc-cut-destroy", "--no-bpc-cut-repair", "--no-bpc-cut-hard-filter", "--no-bpc-cut-soft-penalty"]))
    out.append(RunSpec("A", "A2_hard_only", C + ["--tag", "A2_hard_only", "--bpc-cut-destroy", "--bpc-cut-repair", "--bpc-cut-hard-filter", "--no-bpc-cut-soft-penalty"]))
    out.append(RunSpec("A", "A3_soft_only", C + ["--tag", "A3_soft_only", "--bpc-cut-destroy", "--bpc-cut-repair", "--no-bpc-cut-hard-filter", "--bpc-cut-soft-penalty"]))

    # Stage B (12) coarse grid slices
    grid_B = [
        (1, 5, 1e-5, 1e-4, 0.10, 2, 5),
        (1, 10, 1e-5, 1e-4, 0.25, 4, 5),
        (1, 20, 1e-6, 1e-4, 0.50, 8, 10),
        (2, 5, 1e-5, 1e-3, 0.10, 2, 5),
        (2, 10, 1e-5, 1e-4, 0.25, 4, 10),
        (2, 20, 1e-6, 1e-4, 0.50, 8, 10),
        (3, 5, 1e-4, 1e-3, 0.10, 2, 5),
        (3, 10, 1e-5, 1e-4, 0.25, 4, 10),
        (3, 20, 1e-6, 1e-5, 1.00, 8, 10),
        (2, 10, 1e-4, 1e-3, 0.50, 8, 5),
        (1, 10, 1e-6, 1e-5, 1.00, 4, 10),
        (3, 10, 1e-5, 1e-4, 0.50, 4, 10),
    ]
    for i, (sf, mc, ev, er, lam, age, sb) in enumerate(grid_B, start=1):
        out.append(
            RunSpec(
                "B",
                f"B{i:02d}",
                C
                + [
                    "--tag", f"B{i:02d}",
                    "--sep-freq-phase", str(sf),
                    "--max-cuts-per-round", str(mc),
                    "--epsilon-violation", str(ev),
                    "--epsilon-reject", str(er),
                    "--lambda-cut", str(lam),
                    "--cut-age-limit", str(age),
                    "--sep-budget-s-per-phase", str(sb),
                    "--bpc-cut-destroy", "--bpc-cut-repair", "--bpc-cut-hard-filter", "--bpc-cut-soft-penalty",
                ],
            )
        )

    # Stage C (8) local refinements
    grid_C = [
        (1, 10, 1e-6, 1e-5, 0.25, 4, 10),
        (1, 10, 1e-6, 1e-4, 0.35, 4, 10),
        (2, 10, 1e-6, 1e-5, 0.25, 4, 10),
        (2, 10, 1e-5, 1e-4, 0.35, 6, 10),
        (2, 20, 1e-6, 1e-5, 0.35, 6, 10),
        (2, 20, 1e-5, 1e-4, 0.50, 8, 10),
        (3, 10, 1e-6, 1e-5, 0.35, 4, 10),
        (3, 20, 1e-6, 1e-5, 0.50, 8, 10),
    ]
    for i, (sf, mc, ev, er, lam, age, sb) in enumerate(grid_C, start=1):
        out.append(
            RunSpec(
                "C",
                f"C{i:02d}",
                C
                + [
                    "--tag", f"C{i:02d}",
                    "--sep-freq-phase", str(sf),
                    "--max-cuts-per-round", str(mc),
                    "--epsilon-violation", str(ev),
                    "--epsilon-reject", str(er),
                    "--lambda-cut", str(lam),
                    "--cut-age-limit", str(age),
                    "--sep-budget-s-per-phase", str(sb),
                    "--bpc-cut-destroy", "--bpc-cut-repair", "--bpc-cut-hard-filter", "--bpc-cut-soft-penalty",
                ],
            )
        )

    # Stage D (6) robustness
    grid_D = [
        (2, 10, 1e-6, 1e-5, 0.25, 4, 10),
        (2, 10, 1e-6, 1e-5, 0.35, 4, 10),
        (2, 10, 1e-6, 1e-4, 0.25, 6, 10),
        (2, 20, 1e-6, 1e-5, 0.35, 6, 10),
        (3, 10, 1e-6, 1e-5, 0.35, 4, 10),
        (3, 20, 1e-6, 1e-5, 0.50, 8, 10),
    ]
    for i, (sf, mc, ev, er, lam, age, sb) in enumerate(grid_D, start=1):
        out.append(
            RunSpec(
                "D",
                f"D{i:02d}",
                C
                + [
                    "--tag", f"D{i:02d}",
                    "--sep-freq-phase", str(sf),
                    "--max-cuts-per-round", str(mc),
                    "--epsilon-violation", str(ev),
                    "--epsilon-reject", str(er),
                    "--lambda-cut", str(lam),
                    "--cut-age-limit", str(age),
                    "--sep-budget-s-per-phase", str(sb),
                    "--bpc-cut-destroy", "--bpc-cut-repair", "--bpc-cut-hard-filter", "--bpc-cut-soft-penalty",
                ],
            )
        )

    assert len(out) == 29
    return out


def main() -> None:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    ts = stamp()

    runs = specs()
    py = sys.executable

    manifest_rows = []
    summary_rows = []

    t0 = time.perf_counter()
    for i, rs in enumerate(runs, start=1):
        cmd = [py, str(RUNNER)] + rs.args
        print(f"[{i}/{len(runs)}] {rs.run_id}")
        out_csv = run_cmd(cmd)
        out_path = Path(out_csv)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        stats = summarize(out_path)

        manifest_rows.append(
            {
                "stage": rs.stage,
                "run_id": rs.run_id,
                "output_csv": str(out_path.resolve()),
                "cmd": " ".join(cmd),
            }
        )
        summary_rows.append(
            {
                "stage": rs.stage,
                "run_id": rs.run_id,
                "n": int(stats["n"]),
                "mean_delta_obj": round(stats["mean_delta_obj"], 6),
                "mean_delta_rt_s": round(stats["mean_delta_rt_s"], 6),
                "mean_delta_gap_pp": round(stats["mean_delta_gap_pp"], 6),
                "mean_final_gap_pct": round(stats["mean_final_gap_pct"], 6),
                "max_final_gap_pct": round(stats["max_final_gap_pct"], 6),
                "within_0p2_pct": round(stats["within_0p2_pct"], 3),
                "obj_wins": int(stats["obj_wins"]),
                "obj_losses": int(stats["obj_losses"]),
                "rt_wins": int(stats["rt_wins"]),
                "rt_losses": int(stats["rt_losses"]),
                "gap_wins": int(stats["gap_wins"]),
                "gap_losses": int(stats["gap_losses"]),
                "stops": ";".join(f"{k}:{v}" for k, v in sorted(stats["stops"].items())),
            }
        )

    wall_min = (time.perf_counter() - t0) / 60.0

    manifest_path = OUT_ANALYSIS / f"bpc_replica_manifest_{ts}.csv"
    summary_path = OUT_ANALYSIS / f"bpc_replica_summary_{ts}.csv"
    report_path = OUT_ANALYSIS / f"bpc_replica_report_{ts}.txt"
    pareto_path = OUT_ANALYSIS / f"bpc_replica_pareto_{ts}.csv"
    rec_path = OUT_ANALYSIS / f"bpc_replica_recommendation_{ts}.md"

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        w.writeheader()
        w.writerows(manifest_rows)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    # Pareto-ish shortlist by (mean_delta_gap_pp, max_final_gap_pct, mean_delta_rt_s)
    ranked = sorted(summary_rows, key=lambda r: (r["mean_delta_gap_pp"], r["max_final_gap_pct"], r["mean_delta_rt_s"]))
    top = ranked[:8]

    with pareto_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(top[0].keys()))
        w.writeheader()
        w.writerows(top)

    lines = [
        f"BPC replica 29-run suite report ({ts})",
        f"Runs completed: {len(summary_rows)}",
        f"Total wall-clock: {wall_min:.1f} min",
        "",
        "Top-5 by gap objective:",
    ]
    for r in ranked[:5]:
        lines.append(
            f"  {r['run_id']} (stage {r['stage']}): "
            f"dGap={r['mean_delta_gap_pp']:+.4f}pp, "
            f"maxGap={r['max_final_gap_pct']:.4f}%, "
            f"dRT={r['mean_delta_rt_s']:+.1f}s, dObj={r['mean_delta_obj']:+.3f}"
        )

    # Stage winners
    lines.append("")
    lines.append("Stage winners:")
    for stage in ["A", "B", "C", "D"]:
        srows = [r for r in summary_rows if r["stage"] == stage]
        srows.sort(key=lambda r: (r["mean_delta_gap_pp"], r["max_final_gap_pct"], r["mean_delta_rt_s"]))
        b = srows[0]
        lines.append(
            f"  Stage {stage}: {b['run_id']} "
            f"(dGap={b['mean_delta_gap_pp']:+.4f}pp, maxGap={b['max_final_gap_pct']:.4f}%, dRT={b['mean_delta_rt_s']:+.1f}s)"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    best = ranked[0]
    rec = [
        f"# BPC Replica Recommendation ({ts})",
        "",
        f"Recommended run_id: **{best['run_id']}** (stage {best['stage']})",
        "",
        "## Metrics",
        f"- mean_delta_gap_pp: {best['mean_delta_gap_pp']:+.6f}",
        f"- max_final_gap_pct: {best['max_final_gap_pct']:.6f}",
        f"- mean_delta_rt_s: {best['mean_delta_rt_s']:+.6f}",
        f"- mean_delta_obj: {best['mean_delta_obj']:+.6f}",
        f"- within_0p2_pct: {best['within_0p2_pct']:.3f}",
        "",
        "Use the manifest row for this run_id to reproduce exact CLI parameters.",
    ]
    rec_path.write_text("\n".join(rec) + "\n", encoding="utf-8")

    print(f"Manifest: {manifest_path}")
    print(f"Summary : {summary_path}")
    print(f"Report  : {report_path}")
    print(f"Pareto  : {pareto_path}")
    print(f"Rec     : {rec_path}")


if __name__ == "__main__":
    main()
