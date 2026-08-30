# SRPS-ALNS

Adaptive Large Neighborhood Search with **Lagrangian certification** for the
**Selective Routing Problem with Synchronization (SRPS)** — a
Lagrangian-certified heuristic that returns, for each instance, both a feasible solution and
a rigorous upper bound (hence a per-instance optimality gap).

This repository accompanies the paper *"An Adaptive Large Neighborhood Search
with Lagrangian Certification for the Selective Routing Problem with
Synchronization"* (Chouchena & Ben-Abu). The complete, claim-level
reproduction map is in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md): it
links every numerical manuscript result, table, and figure to its committed
input artifact, generator or experiment driver, and invocation.

## Install

```bash
python -m pip install -r requirements.txt    # Python 3.10+ (tested 3.10.11)
```

The core solver, bounds, and certificate verifier need only **numpy** + the
standard library; `scipy`/`statsmodels`/`matplotlib`/`pypdf` are used only by the
figure and statistics build scripts.

## Data

Benchmark instances are the public OPS suite of Riera-Ledesma &
Salazar-González (2021): <https://github.com/RieraULL/OPS-Benchmark>
(mirror: <https://zenodo.org/records/17557917>). Place the `input/` tree under
`benchmarks/ops_raw/OPS-Benchmark-master/` (gitignored — not redistributed here).
The full 660-instance index, with processor-load statistics and per-experiment
inclusion flags, is committed at [`data/instance_manifest.csv`](data/instance_manifest.csv).

## Canonical results

`results/adaptive_master.csv` is the immutable pre-refinement primary run.
`results/adaptive_master_refined.csv` is the canonical post-refinement series
used by the manuscript for all reported certified gaps and runtimes. Its
`final_cert_gap_pct` headline is mean **0.066 %** (95 % CI [0.051 %, 0.081 %]),
median 0 %, maximum 1.614 %; **446/660 (67.6 %) proven optimal** and 100 %
within 2 %.

## Reproducing the paper

The following commands recompute the manuscript outputs from the committed
canonical artifacts. The claim-level map specifies the upstream experiment
needed to rerun each artifact from the public benchmark.

| Script | Produces |
|--------|----------|
| `build_paper_stats.py` | §6.1–6.3 headline stats (incl. 95 % CI) |
| `build_bpc_subgroups.py` | §6.2 BPC A/B/C subgroup table (`tab:bpcsplit`) |
| `build_bpc_comparison.py`, `build_bpc_times.py` | §6.2 BPC split + per-group runtimes |
| `build_new_results.py` | Representative first-ever/improved entries (`tab:newresults`) |
| `build_ejection_summary.py` | Ejection-chain identity and its cohort counts |
| `build_appendix_A.py` | **superseded** — old A0–A5 ablation design, invalidated 2026-08-27; kept for history only, do not use |
| `build_ablation_summary.py` | §6.5.1 ablation (redesigned B1–B8+S, `tab:ablation`) + noise-floor MDE + B5/B7 cross-check |
| `build_sensitivity_summary.py` | §6.5.2 + §5 parameter justification |
| `run_quality_analysis.py --csv results/adaptive_master_refined.csv` | Hardness diagnostic data behind Fig. 2 |
| `build_figures.py` | both figures (`paper/figures/*.pdf`) |

To regenerate the standard derived outputs in one pass (not the long solver
campaigns), run:

```bash
python build_paper_stats.py
python build_bpc_times.py
python build_bpc_subgroups.py
python build_bpc_comparison.py
python build_figures.py
python build_new_results.py
python build_ejection_summary.py
python build_hardtail_refresh.py
python build_ablation_summary.py
python build_sensitivity_summary.py
python run_quality_analysis.py --csv results/adaptive_master_refined.csv
python analyse_operating_points.py
```

Equivalently, run `python reproduce.py --manuscript-results`.

### Re-running computational campaigns

The commands above are deterministic **recomputations** from versioned result
artifacts; they do not execute the time-budgeted solver campaigns. To rerun a
campaign from the public OPS inputs, use the commands in
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md). In particular, the main
campaign is `python run_adaptive_full.py --cold-start --save-certificates`, the
post-search certificate rebuild is
`python rebuild_bounds_certified.py --iters 3000 --workers 6`, and the Tier-2
campaigns are `python run_noise_floor.py --cores 6`,
`python run_ablation.py --cores 6`, and `python run_sensitivity_pipeline.py`.
Reruns are time-budgeted and need not be bit-identical to the archived series.

`python reproduce.py --all` additionally invokes historical course-project
stages that are deliberately not distributed in this repository. It is not the
standalone paper-reproduction command; it reports a clear missing-driver error
in a clean clone. Use `--manuscript-results` for the current paper.

The computational campaigns and their expected inputs are documented in the
claim-level map at [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md). Do not
use `build_appendix_A.py`: it is retained only as an invalidated historical
record, refuses execution, and is not a source for any current manuscript claim.

The manuscript sources are in [`paper/`](paper/): the modular submission source
is `main.tex`, with `refs.bib`, `supplementary.tex`, and `figures/*.pdf`.

## Independent verification

**Primal** (feasibility of every reported incumbent):

```bash
python run_validate_adaptive.py --csv results/adaptive_master.csv
```

**Primal + dual** (reconstructs the Lagrangian upper bound and checks it
dominates the incumbent, so each certified gap is reproducible, not trusted):

```bash
python scripts/verify_certificates.py            # all 660; writes results/verification_report.csv
```

Runs in **stored-μ** mode when per-instance multipliers are present
(`results/beta_certificates/`, produced by `--save-certificates`), otherwise in
**rederive** mode — an *independent* sub-gradient bound, the stronger check for a
referee. `core.evaluate_lagrangian(inst, mu)` recomputes `L(μ)` at a stored
multiplier vector (exact round-trip vs `lagrangian_bound`).

**Note:** the two commands above check an exploratory 70-instance hard-tail
subset (`results/beta_certificates/`). They are not paper-wide certificate
verification. The canonical 660-instance store is `results/certificates/`
(tracked), and the required paper-wide verification is the Path-B command below.

## Path B — independent numerical re-derivation (all 660 certificates)

The strongest available check on the reported certified gaps: for every one of
the 660 study instances, reload the raw benchmark file and the certificate's
stored multipliers (`results/certificates/<instance>.pkl`) — nothing else — and
independently re-derive `L(μ)`, with **no dependence on any cached or
production object**.

```bash
python verify_interval_arithmetic.py --mode exact --csv   # all 660, ~30s
python verify_interval_arithmetic.py --mode exact --stratified 3   # 54-instance stratified smoke test
```

`--mode exact` converts every float64 input to its exact decimal value
(`Decimal(x)`, not the lossy `Decimal(str(x))`) and sums in 80-digit precision
under directed rounding (`ROUND_CEILING`), giving a rigorous upper bound on
`L(μ)` rather than a repetition of the float64 computation used by the search.
The per-processor orienteering DP's selected job subset is independently
re-summed in exact arithmetic and checked against the DP's own reported value.

**Result:** all 660 certificates are valid at **zero** tolerance under this
independent re-derivation (none require the ε=1e-9 floor safeguard described in
Appendix A), and the per-processor exact re-sum matches the DP's reported total
on every one of the 660×55 subproblems checked (maximum discrepancy: 0.0).
Full per-instance output: `results/analysis/path_b_verification_exact.csv`
(committed). See Appendix A, Algorithm 2, for the formal procedure.

## Hard-tail in-loop re-bound experiment

Isolates the contribution of the *in-loop* Lagrangian re-bound on the 70
hard-tail (`TIERS_EXHAUSTED`) instances, using a free bound in both arms:

```bash
python run_adaptive_full.py --subset results/hard_tail_70.csv --save-certificates --tag hardtail_H0   # H0: standard, re-bound active
python run_adaptive_full.py --subset results/hard_tail_70.csv --no-refresh        --tag hardtail_H1a  # H1a: control, no in-loop re-bound
python build_hardtail_refresh.py    # -> results/analysis/hardtail_refresh_<ts>.{csv,txt,tex}
```

`run_adaptive_full.py` with no flags reproduces the canonical 660-instance run.

## Tier 2 — hard-tail noise floor + redesigned ablation (B1–B8+S)

Measures the run-to-run noise floor on the 70 hard-tail instances (A0 vs A0',
disjoint seed sets, gap stop disabled), then a stratified 40-instance
(20 hard-tail + 20 closing) ablation over 10 configurations (A0, B1–B8, S)
against fixed certified bounds. Design: `docs/ABLATION_DESIGN.md`.

```bash
python run_noise_floor.py --cores 6        # -> results/analysis/noise_floor_<ts>.csv (70 rows)
python run_ablation.py --cores 6           # -> results/analysis/ablation_b1b8s_<ts>.csv (400 rows)
python build_ablation_summary.py           # -> results/analysis/ablation_summary_<ts>.{csv,txt}
```

`build_ablation_summary.py` auto-detects the latest complete CSV for each
input (row-count checked: 70 for noise floor, 400 for the ablation) and
regenerates every number in §6.5.1/Appendix~A's ablation subsection: the
pooled per-arm×stratum table, the noise-floor-derived minimum detectable
effect, the per-family/per-size exploratory breakdown, and the B5/B7
cross-check against `build_hardtail_refresh.py`'s census and the ejection-chain
identity.

## Repository layout

```
adapters/   OPS instance/solution model + feasibility oracle
core/        ALNS search, operators, bounds (ops_bounds.py), post-processing
validators/  independent feasibility checker (7 checks)
scripts/     verify_certificates.py (certificate verifier, 70-instance hard-tail subset)
verify_interval_arithmetic.py   Path B: exact re-derivation of all 660 certificates
build_*.py   table/figure/stat generators (one per manuscript artifact)
run_*.py     experiment drivers (adaptive run, ablation, sensitivity, validation)
data/        instance_manifest.csv
results/     adaptive_master.csv, hard_tail_70.csv, analysis/, certificates/ (gitignored incumbents; certificates/ and path_b_verification_exact.csv are committed)
paper/       LaTeX manuscript + refs + figures
docs/        roadmaps (literature, reproducibility, COR revision)
```

## Citing

See [`CITATION.cff`](CITATION.cff). Update the article volume/pages/DOI on
acceptance.

## License

Released under the [MIT License](LICENSE).

---

*Development notes (session state, trajectory) live in
[`RESTART.md`](RESTART.md) and [`memory/project_roadmap.md`](memory/project_roadmap.md).*
