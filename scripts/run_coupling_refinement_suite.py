from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DUAL_RUNNER = ROOT / "dev_dual_guided" / "run_dual_guided_experiment.py"
CUT_RUNNER = ROOT / "dev_cut_guided" / "run_cut_guided_experiment.py"
SUBSET = ROOT / "configs" / "coupling_refine_subset12.csv"
ANALYSIS_DIR = ROOT / "results" / "analysis"


@dataclass
class Experiment:
    name: str
    family: str
    args: List[str]


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def _run_cmd(cmd: List[str]) -> str:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    # Prefer explicit CSV line from runner output.
    for line in proc.stdout.splitlines()[::-1]:
        line = line.strip()
        if line.startswith("CSV:"):
            return line.split("CSV:", 1)[1].strip()
    raise RuntimeError(f"Could not parse output CSV path from command output.\n{proc.stdout}")


def _to_float(v: str):
    try:
        return float(v)
    except Exception:
        return None


def _summarize_csv(path: Path) -> Dict[str, float]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    n = len(rows)
    d_obj = [_to_float(r.get("delta_ref", "")) for r in rows]
    d_rt = [_to_float(r.get("delta_rt_s", "")) for r in rows]
    d_gap = [_to_float(r.get("delta_gap_pct", "")) for r in rows]
    final_gap = [_to_float(r.get("final_gap_pct", "")) for r in rows]

    d_obj_f = [x for x in d_obj if x is not None]
    d_rt_f = [x for x in d_rt if x is not None]
    d_gap_f = [x for x in d_gap if x is not None]
    final_gap_f = [x for x in final_gap if x is not None]

    stop_counts: Dict[str, int] = {}
    for r in rows:
        s = r.get("stop_reason", "")
        stop_counts[s] = stop_counts.get(s, 0) + 1

    return {
        "n": n,
        "mean_delta_obj": (sum(d_obj_f) / len(d_obj_f)) if d_obj_f else 0.0,
        "mean_delta_rt_s": (sum(d_rt_f) / len(d_rt_f)) if d_rt_f else 0.0,
        "mean_delta_gap_pp": (sum(d_gap_f) / len(d_gap_f)) if d_gap_f else 0.0,
        "mean_final_gap_pct": (sum(final_gap_f) / len(final_gap_f)) if final_gap_f else 0.0,
        "max_final_gap_pct": max(final_gap_f) if final_gap_f else 0.0,
        "within_0p2_pct": (100.0 * sum(x < 0.2 for x in final_gap_f) / len(final_gap_f)) if final_gap_f else 0.0,
        "obj_wins": sum(x < 0 for x in d_obj_f),
        "obj_losses": sum(x > 0 for x in d_obj_f),
        "rt_wins": sum(x < 0 for x in d_rt_f),
        "rt_losses": sum(x > 0 for x in d_rt_f),
        "gap_wins": sum(x < 0 for x in d_gap_f),
        "gap_losses": sum(x > 0 for x in d_gap_f),
        "stops": stop_counts,
    }


def _experiments(common: Dict[str, str]) -> List[Experiment]:
    ca = [
        "--subset-csv", common["subset_csv"],
        "--workers", common["workers"],
        "--phase-rt", common["phase_rt"],
        "--abs-cap", common["abs_cap"],
        "--gap-threshold", common["gap_threshold"],
        "--lag-max-iter", common["lag_max_iter"],
        "--lag-max-time", common["lag_max_time"],
    ]

    return [
        Experiment("dual_control", "dual", ca + ["--tag", "suite_dual_control", "--no-dual-destroy", "--no-dual-repair", "--no-dual-feedback"]),
        Experiment("dual_full_fb", "dual", ca + ["--tag", "suite_dual_full_fb", "--dual-destroy", "--dual-repair", "--dual-feedback"]),
        Experiment("dual_full_nofb", "dual", ca + ["--tag", "suite_dual_full_nofb", "--dual-destroy", "--dual-repair", "--no-dual-feedback"]),
        Experiment("dual_destroy_only", "dual", ca + ["--tag", "suite_dual_destroy_only", "--dual-destroy", "--no-dual-repair", "--no-dual-feedback"]),
        Experiment("dual_repair_only", "dual", ca + ["--tag", "suite_dual_repair_only", "--no-dual-destroy", "--dual-repair", "--dual-feedback"]),
        Experiment("cut_control", "cut", ca + ["--tag", "suite_cut_control", "--no-cut-destroy", "--no-cut-repair"]),
        Experiment("cut_full_w035", "cut", ca + ["--tag", "suite_cut_full_w035", "--cut-destroy", "--cut-repair", "--cut-weight", "0.35"]),
        Experiment("cut_destroy_w035", "cut", ca + ["--tag", "suite_cut_destroy_w035", "--cut-destroy", "--no-cut-repair", "--cut-weight", "0.35"]),
        Experiment("cut_destroy_w020", "cut", ca + ["--tag", "suite_cut_destroy_w020", "--cut-destroy", "--no-cut-repair", "--cut-weight", "0.20"]),
        Experiment("cut_repair_w035", "cut", ca + ["--tag", "suite_cut_repair_w035", "--no-cut-destroy", "--cut-repair", "--cut-weight", "0.35"]),
    ]


def _runner_for(family: str) -> Path:
    return DUAL_RUNNER if family == "dual" else CUT_RUNNER


def main() -> None:
    if not SUBSET.exists():
        raise FileNotFoundError(f"Missing subset CSV: {SUBSET}")

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()

    common = {
        "subset_csv": str(SUBSET),
        "workers": "4",
        "phase_rt": "120",
        "abs_cap": "240",
        "gap_threshold": "0.003",
        "lag_max_iter": "120",
        "lag_max_time": "20",
    }

    exps = _experiments(common)
    py = sys.executable

    manifest_rows = []
    summary_rows = []

    t0 = time.perf_counter()
    for i, exp in enumerate(exps, start=1):
        cmd = [py, str(_runner_for(exp.family))] + exp.args
        print(f"[{i}/{len(exps)}] {exp.name}")
        out_csv = _run_cmd(cmd)
        out_path = Path(out_csv)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        stats = _summarize_csv(out_path)

        manifest_rows.append({
            "experiment": exp.name,
            "family": exp.family,
            "output_csv": str(out_path.resolve()),
            "cmd": " ".join(cmd),
        })

        summary_rows.append({
            "experiment": exp.name,
            "family": exp.family,
            "n": stats["n"],
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
        })

    wall_min = (time.perf_counter() - t0) / 60.0

    manifest_path = ANALYSIS_DIR / f"coupling_refinement_manifest_{stamp}.csv"
    summary_path = ANALYSIS_DIR / f"coupling_refinement_summary_{stamp}.csv"
    report_path = ANALYSIS_DIR / f"coupling_refinement_report_{stamp}.txt"

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        w.writeheader()
        w.writerows(manifest_rows)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    by_name = {r["experiment"]: r for r in summary_rows}
    dual_base = by_name.get("dual_control")
    cut_base = by_name.get("cut_control")

    lines = [
        f"Coupling refinement suite report ({stamp})",
        f"Subset: {SUBSET}",
        "Common runtime knobs: phase_rt=120s, abs_cap=240s, lag_max_iter=120, lag_max_time=20s",
        f"Experiments run: {len(summary_rows)}",
        f"Total wall-clock: {wall_min:.1f} min",
        "",
        "Top experiments by mean_delta_gap_pp (lower better):",
    ]

    top_gap = sorted(summary_rows, key=lambda r: r["mean_delta_gap_pp"])
    for r in top_gap[:5]:
        lines.append(
            f"  {r['experiment']}: dGap={r['mean_delta_gap_pp']:+.4f}pp "
            f"dRT={r['mean_delta_rt_s']:+.1f}s dObj={r['mean_delta_obj']:+.3f} "
            f"maxGap={r['max_final_gap_pct']:.4f}%"
        )

    lines.extend(["", "Dual family deltas vs dual_control:"])
    if dual_base is not None:
        for name in ["dual_full_fb", "dual_full_nofb", "dual_destroy_only", "dual_repair_only"]:
            if name not in by_name:
                continue
            r = by_name[name]
            lines.append(
                f"  {name}: "
                f"dGap {float(r['mean_delta_gap_pp']) - float(dual_base['mean_delta_gap_pp']):+.4f}pp, "
                f"dRT {float(r['mean_delta_rt_s']) - float(dual_base['mean_delta_rt_s']):+.1f}s, "
                f"dObj {float(r['mean_delta_obj']) - float(dual_base['mean_delta_obj']):+.3f}"
            )

    lines.extend(["", "Cut family deltas vs cut_control:"])
    if cut_base is not None:
        for name in ["cut_full_w035", "cut_destroy_w035", "cut_destroy_w020", "cut_repair_w035"]:
            if name not in by_name:
                continue
            r = by_name[name]
            lines.append(
                f"  {name}: "
                f"dGap {float(r['mean_delta_gap_pp']) - float(cut_base['mean_delta_gap_pp']):+.4f}pp, "
                f"dRT {float(r['mean_delta_rt_s']) - float(cut_base['mean_delta_rt_s']):+.1f}s, "
                f"dObj {float(r['mean_delta_obj']) - float(cut_base['mean_delta_obj']):+.3f}"
            )

    lines.extend([
        "",
        "Notes:",
        "  - This suite is a fast-screen design for iterative refinement; use the same manifest",
        "    and re-run selected finalists on full30/full660 budgets for publication claims.",
        "  - Summary CSV is ready for downstream ablation/sensitivity plotting and hypothesis tracking.",
    ])

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Manifest: {manifest_path}")
    print(f"Summary : {summary_path}")
    print(f"Report  : {report_path}")


if __name__ == "__main__":
    main()
