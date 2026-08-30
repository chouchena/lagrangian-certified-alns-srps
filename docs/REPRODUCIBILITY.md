# Manuscript result reproduction map

This is the authoritative traceability index for the current manuscript. Each
reported numerical result, table, and figure has (1) a committed input artifact,
(2) committed code that either reruns the experiment or recomputes the result,
and (3) an exact command below. The current-paper reproduction route is
`python reproduce.py --manuscript-results`; it uses only the standalone drivers
in this repository. “Recompute” means deterministic regeneration
from the versioned result artifacts; “rerun” means repeat the computational
experiment from the public OPS benchmark.  A rerun can vary in wall-clock
iteration counts because the primary search is time-budgeted, so it is not
expected to be bit-identical.

`reproduce.py --all` is a legacy course-project protocol and additionally names
companion-workspace drivers that are intentionally not distributed here. It is
not a clean-clone paper-reproduction command; absent legacy drivers cause an
explicit error.

## Prerequisites

Install the Python dependencies with `python -m pip install -r requirements.txt`.
Obtain the public OPS benchmark as described in the repository README and place
its `input/` tree below `benchmarks/ops_raw/OPS-Benchmark-master/`.  The compact
MIP check additionally needs CPLEX 22.1.1 and a compatible Python 3.8–3.10 API.

## Primary and verification results

| Manuscript result | Versioned input | Reproduction code and command | Mode |
| --- | --- | --- | --- |
| Abstract, §6.1, `tab:mainresults`, certificate-tier counts, runtime and post-refinement effect | `results/adaptive_master.csv`, `results/bound_refine_corrected.csv`, `results/adaptive_master_refined.csv` | `python build_paper_stats.py` | Recompute |
| Fig. `fig:certtiers` and Fig. `fig:hardness` | `results/adaptive_master_refined.csv` | `python build_figures.py` | Recompute |
| `tab:bpcsplit` and all BPC coverage/comparison counts | `results/adaptive_master_refined.csv`, `results/analysis/bpc_times.csv` | `python build_bpc_times.py`; then `python build_bpc_subgroups.py` | Recompute |
| Representative entries in `tab:newresults` and all reported first-ever/improved counts | `results/adaptive_master_refined.csv` | `python build_new_results.py`; `python build_paper_stats.py` | Recompute |
| Ejection-chain identity, its $12/660$ reach, and the three dependent optimality proofs | `results/adaptive_master_refined.csv` | `python build_ejection_summary.py` | Recompute |
| 660 certificate validity and 660 x 55 exact re-sums | `results/certificates/`, `results/analysis/path_b_verification_exact.csv` | `python verify_interval_arithmetic.py --mode exact --csv` | Recompute / independent verification |
| Four floating-point safeguarding corrections | `results/bound_refine_corrected.csv`, `results/adaptive_master_refined.csv` | `python fix_refine_floor.py`; then `python build_adaptive_master_refined.py` | Recompute |
| Independent compact-MIP comparison | `results/exact/` | Companion-workspace driver: `python dev_exact/run_exact.py --subset configs/exact_small_nonzero.csv --time-limit 180 --threads 6 --tag small30` | Archived result; rerun additionally needs CPLEX and the companion driver |
| Main 660-instance solver campaign | Public OPS input | `python run_adaptive_full.py --cold-start --save-certificates`; then `python build_adaptive_master.py --adaptive results/adaptive_full_<timestamp>.csv` | Rerun |
| Post-search refinement and certificate persistence | Primary output plus public OPS input | `python rebuild_bounds_certified.py --iters 3000 --workers 6` | Rerun / certificate rebuild |

The primary and refined CSVs are deliberately separate. The manuscript uses
the **post-refinement** series; the primary series remains versioned because it
is the source for primal-only and before-refinement analyses.

The `dev_exact/`, `dev_bpc_replica/`, and `dev_dual_guided/` directories are
course-project companion material and are intentionally not included in this
public solver repository. Their historical commands remain recorded only to
identify the archived derivations. The standalone paper reproduction route,
`python reproduce.py --manuscript-results`, does not depend on them.

## Mechanism, ablation, and sensitivity results

| Manuscript result | Versioned input | Reproduction code and command | Mode |
| --- | --- | --- | --- |
| In-loop re-bound census, `tab:hardtail-refresh` | `results/adaptive_full_*hardtail_H0.csv`, `results/adaptive_full_*hardtail_H1a.csv` | `python build_hardtail_refresh.py --h0 <H0.csv> --h1a <H1a.csv>` | Recompute |
| Hard-tail H0 rerun | `results/hard_tail_70.csv`, public OPS input | `python run_adaptive_full.py --subset results/hard_tail_70.csv --save-certificates --tag hardtail_H0` | Rerun |
| Hard-tail H1a rerun | `results/hard_tail_70.csv`, public OPS input | `python run_adaptive_full.py --subset results/hard_tail_70.csv --no-refresh --tag hardtail_H1a` | Rerun |
| Tier-2 noise floor | `results/analysis/noise_floor_20260828_1744.csv` | `python run_noise_floor.py --cores 6` | Rerun |
| B1–B8+S ablation, `tab:ablation`, MDE, cross-checks, and all supplementary ablation counts | `results/analysis/ablation_b1b8s_20260829_0319.csv`, Tier-2 CSV, `results/bounds_certified.csv` | `python run_ablation.py --cores 6`; then `python build_ablation_summary.py` | Rerun then recompute |
| Parameter-sensitivity table | `results/sensitivity/*.csv` | `python run_sensitivity_pipeline.py`; then `python build_sensitivity_summary.py` | Rerun then recompute |
| Hardness diagnostic behind Fig. `fig:hardness` | `results/adaptive_master_refined.csv` | `python run_quality_analysis.py --csv results/adaptive_master_refined.csv` | Recompute |
| Refinement iteration-cap table | `results/refine_sweep_1000.csv`, `results/bound_refine_corrected.csv`, `results/refine_sweep_5000.csv` | `python run_bound_refine.py --iters 1000 --max-time 1200 --workers 6 --limit 60`; repeat with `--iters 3000` and `--iters 5000` | Rerun |
| Operating-point table and replay analysis | `archive/results_interim/adaptive_full_20260619_0917_phases.csv`, `results/adaptive_master.csv`, `results/bound_refine_corrected.csv` | `python analyse_operating_points.py` | Recompute |

The phase trajectory required for the operating-point replay is retained under
`archive/results_interim/` because it is a raw input to a current reported
result, not merely a development archive.  It is intentionally named in the
command above rather than selected by a timestamp glob.

## Non-numerical and external facts

The benchmark-family taxonomy and original BPC claims are source-attributed to
Riera-Ledesma and Salazar-González (2021); they are not newly generated results.
The fixed ALNS parameter table and algorithms are implementation specifications.
Their executable counterparts are `run_adaptive_full.py`, `run_ablation.py`,
and the modules under `core/`.

## Integrity checks

Before relying on regenerated output, run `python build_paper_stats.py` and
confirm its headline values against `docs/claims_audit.md`.  The independent
certificate check must report no failures.  `build_ablation_summary.py` rejects
incomplete noise-floor or ablation inputs, and the final recorded artifacts
contain 70 and 400 rows respectively.  Historical A0–A5 output and
`build_appendix_A.py` are explicitly invalidated and excluded from this map.

For the complete deterministic recomputation and independent-certificate pass,
use `python reproduce.py --manuscript-results`. This command deliberately does
not rerun the time-budgeted solver campaigns or the licensed CPLEX comparison;
those invocations are listed above and must be explicitly requested.