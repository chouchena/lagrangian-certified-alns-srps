# Reproducibility Package + Hard-Tail UB-Refresh Evidence — Trajectory & Roadmap

*Created 2026-06-24. Addresses the two remaining "defensibility" pillars: (4) an independently
verifiable certificate pipeline, and (5) direct evidence for the in-loop UB-refresh / hard-tail claim.
Strategic assessment (agreed): the paper is on a good trajectory — a COR-grade certified primal–dual
contribution — but not yet "safe submission"; these two pillars are what move it from promising to
serious. Stop broad rewriting; focus on defensibility.*

---

## Grounding — what ALREADY exists (do NOT rebuild)

| Plan item | Status | Existing asset |
|---|---|---|
| 4.5 primal feasibility verifier | ✅ **exists** | `run_validate_adaptive.py` — loads every saved incumbent PKL from `results/beta_incumbents/`, runs **7 checks** (route bookends, job membership, route↔selected consistency, acyclicity, schedule feasibility, obj recompute) + cross-checks claimed obj vs CSV; "must pass 100% before insertion". Primitives in `validators/validate_ops_solution.py`, `core/solution_validator.py`. |
| 4.3 central results CSV | ◐ **partial** | `results/adaptive_master.csv` has obj (`alns_obj`), bound (`best_ub`), gap (`final_cert_gap_pct`), runtime, `beta_stop_reason`, `beta_phases`, BPC ref cols, status flags. |
| 4.6 incumbent artifacts | ✅ **exists** | `results/beta_incumbents/*.pkl` (routes + selected) — gitignored, on disk. |
| 4.8 reproduce tables/figures | ✅ **exists** | `build_paper_stats.py`, `build_bpc_subgroups.py`, `build_bpc_comparison.py`, `build_bpc_times.py`, `build_appendix_A.py`, `build_sensitivity_summary.py`, `build_figures.py`. |
| 4.4 certified-gap formula | ✅ **in paper** | Defined in §4.3 + §6.2 conventions + Appendix A; denominator = `UB_reported` (consistent). Validity guard documented in App A. |
| 5.1 hard-tail set | ✅ **derivable now** | `beta_stop_reason == TIERS_EXHAUSTED` = **exactly 70** instances; **0 runtime-cap stops** (clean separation). |
| 5.2 no-refresh arm | ◐ **localized change** | in-loop re-bound = `run_adaptive_full.py:245` `lagrangian_bound(..., lower_bound=best_obj, mu_init=prev_mu)`; `prev_mu=lag["best_mu"]`. A `--no-refresh` flag skips the in-loop call. |

### Genuine GAPS
- **Dual half of the verifier (4.5):** no recomputation of `L(μ)` from saved multipliers, because **μ is not persisted per instance** (only incumbents are). This is the core missing piece for a *full* certificate verifier.
- **CSV columns (4.3):** missing `lagrangian_upper_bound_raw` vs `..._reported` (current `best_ub` is raw; guard applied downstream), `num_ub_refreshes`, `num_lagrangian_iterations_total`, `seed_set` (fixed `[42,123,456,789,1337,2024]` — known, just not a column), `proven_optimal_by_lagrangian_match`, `matches_bpc_optimum`, `improves_published_bks`.
- **Instance manifest (4.2):** not built; but every column is computable now (processor-load stats incl. `max|J_k|=13` from the instance JSONs; BPC status from CSV; inclusion flags from stop-reason/subset membership).
- **Repo packaging (4.1):** not started (user is "not yet on repo stage").
- **Hard-tail experiment (5.2):** the `--no-refresh` run on the 70 instances has not been executed.

---

## Progress — 2026-06-24 (code complete; solver runs remain the user's)

The reproducibility **machinery** is now built and smoke-tested; what is left is
compute on the user's machine, not code.

- ✅ **P0.3 `--no-refresh`** — added to `run_adaptive_full.py` (also `--subset`,
  `--save-certificates`, `--tag`). Defaults reproduce the canonical run byte-for-byte.
- ✅ **P0.4 `build_hardtail_refresh.py`** — Δgap table generator (emits CSV/TXT/TEX,
  `tab:hardtail-refresh`); manuscript placement marked by a LaTeX comment in
  §"Effect of in-loop re-bounding" (both `.tex` files). No fabricated numbers.
- ✅ **P1 verifier `scripts/verify_certificates.py`** — 7 primal checks + dual
  reconstruction. New primitive `core.evaluate_lagrangian(inst, mu)` recomputes
  `L(μ)` at a stored μ; round-trip is exact (`|Δ|<1e-6` vs `lagrangian_bound`).
  Runs in **stored** mode (checks the reported μ) or **rederive** mode (independent
  bound, used until a μ-persisting canonical run exists). Smoke-tested: 4/4 pass,
  primal + bound-dominance hold.
- ✅ **μ persistence** — `run_adaptive_full.py --save-certificates` writes
  `results/beta_certificates/<inst>.pkl` (`best_mu`, raw/reported UB, refresh count,
  Lagrangian-iter total, seed set). Dir gitignored (regenerable, like incumbents).
- ✅ **P2 columns (partial)** — `beta_raw_ub`, `beta_num_ub_refreshes`,
  `beta_num_lag_iters`, `beta_no_refresh` now emitted by the run.

## Update — 2026-06-24 (compute runs EXECUTED; both pillars closed)

- ✅ **P1 verification COMPLETE.** Full `--rederive-only` run of all 660:
  **660/660 pass** — `pass_primal` 660 (feasibility + objective recompute),
  `pass_bound` 660 (incumbent ≤ independently re-derived `L(μ)`), `csv_obj_match`
  660 "match" (on-disk incumbents reproduce the cited `adaptive_master.csv`
  objectives). Artifact: `results/verification_report.csv` (+ log), committed.
  Go/No-Go gate: **GO.**
- ✅ **P3 hard-tail experiment COMPLETE.** H0 (full) vs H1a (no in-loop refresh)
  on the 70, free bound, identical warm starts:
  mean certified gap **0.955% → 0.691%**, mean Δ **+0.264 pp** (median +0.196,
  max +1.457); **53/70 improved**, 11 unchanged, 6 marginally worse (primal
  run-to-run noise; the bound can only tighten); 22 cross below 1%, 16 below 0.5%.
  `tab:hardtail-refresh` + paragraph in §6.5 of both `.tex`; data + generated table
  committed. Wording chosen: "consistent and, on the hardest instances, substantial."
- ✅ **μ persistence used** — H0 ran with `--save-certificates` (70 certs in the
  gitignored `beta_certificates/`). Stored-mode verification reproduces the bound
  exactly; the committed report uses rederive mode (stronger, fully independent).
- **Lessons baked into the code:** `--rederive-only` (avoid cross-run cert
  contamination — diagnosed live), `--save-suffix` (experiment arms never overwrite
  canonical incumbents), `csv_obj_match` (separate feasibility from provenance).
- **No incumbent-integrity issue:** H0's apparent "11 improved / 3 regressed" were
  vs the *non-adaptive* `master_results.csv`; vs `adaptive_master.csv` all 70 match.

**Nothing compute-side remains for these two pillars.** Optional follow-ups:
a canonical re-run with `--save-certificates` to ship stored μ for all 660 (the
rederive report already certifies them); P2 boolean optimality-flag columns.

---

## Prioritized execution sequence (with Go/No-Go gates)

### P0 — runnable NOW, no solver run (assistant can do immediately)
1. **`results/hard_tail_70.csv`** — derive the 70 `TIERS_EXHAUSTED` instances + their family/n/α/gap/phases from `adaptive_master.csv`. Operationalises §5.1.
2. **`data/instance_manifest.csv`** — full 660 index with processor-load stats (|K|=55, mean/max |J_k|, max|K_j|), BPC status, and inclusion flags (main / ablation-30 / sensitivity-30 / hard-tail-70). Built from instance JSONs + `adaptive_master.csv`.
3. **`--no-refresh` flag** in `run_adaptive_full.py` (skip the in-loop `lagrangian_bound` re-bound; keep the single initial bound) — the H1a arm. Code only, no run.
4. **`build_hardtail_refresh.py`** (table generator, runs once results exist) + the manuscript-table skeleton `tab:hardtail-refresh`.

### P1 — certificate verifier (the single most important item)
- Extend the existing primal verifier into `scripts/verify_certificates.py`: keep the 7 primal checks; **add dual recomputation** — load saved μ, solve each per-processor orienteering DP exactly (`core/ops_bounds.py`), reconstruct `L(μ)`, assert `z_inc ≤ UB_reported`, recompute the gap, diff against `adaptive_master.csv`. Emit `results/verification_report.csv` (pass_profit / pass_bound / pass_gap / pass_all).
- **Prerequisite:** persist μ per instance. Two options:
  - (a) add μ-dump to `run_adaptive_full.py` and do a **canonical re-run** (full certificate package: incumbent + μ + raw/guarded bound) — clean but ~hours of compute on the user's machine;
  - (b) deterministic re-derivation in the verifier (re-run `lagrangian_bound` with the fixed seeds) — no separate run, but it re-solves the dual rather than checking a stored μ.
- **Go/No-Go:** GO if all 660 pass primal feasibility + the bound recomputes ≥ incumbent within tolerance. NO-GO if any certificate cannot be reproduced → investigate before any submission.

### P2 — complete the central results CSV
- Add the missing columns (raw vs guarded bound, refresh count, Lagrangian-iteration totals, seed, the three boolean optimality flags). Most are emitted during the P1 canonical re-run; the booleans derive from existing data.
- **Go/No-Go:** GO if every manuscript number regenerates from this CSV via the `build_*` scripts.

### P3 — hard-tail UB-refresh experiment (the evidence)
- Run **H0 (full)** vs **H1a (no in-loop refresh)** on the 70 hard-tail instances; optionally **H1b (final-only re-bound, equalized Lagrangian budget — Design B, stronger)**.
- Compute Δgap = gap_norefresh − gap_full per instance; report mean/median/max reduction, #improved/#unchanged/#worsened, and threshold crossings (→<1%, →<0.5%, →exact). Fill `tab:hardtail-refresh` (+ a distribution table).
- **Compute estimate:** the 70 are the slowest (they exhaust all tiers); with the 6-worker harness, ~hours per arm on the user's machine — **this is the user's run**.
- **Go/No-Go (decides the paper wording, do NOT force it):**

| Experiment result | Manuscript wording |
|---|---|
| large reduction, many improved | "materially tightens certificates on the hard tail" |
| small but consistent | "modestly but consistently tightens" |
| only a few outliers | "occasionally sharpens the hardest certificates" |
| no meaningful effect | **remove the claim**; present refresh as a safeguard/engineering feature |

### P4 — manuscript edits (after P1/P3 land)
- §6.1: the **"Reproducibility and certificate verification"** paragraph (only once the verifier exists and passes).
- Appendix A: one sentence — "the verification script recomputes every reported certificate from the saved incumbent and multiplier files; no table value is entered manually."
- §6.5 (Effect of in-loop re-bounding): replace narrative with the `tab:hardtail-refresh` results + evidence-matched wording.
- Appendix ablation: add the cross-reference clarifying A3 ≈ 0 is by construction and the real effect is in `tab:hardtail-refresh`.
- §4.2 / Appendix A: confirm one denominator everywhere; state BPC's primal–dual gap is a side-by-side indicator, not an identical definition (already partly in §6.2 ¶2).

---

## Decisions needed from the user before P1/P3
1. **Verifier μ source:** canonical re-run that saves μ (clean, slow) **(recommended)** vs deterministic re-derivation (fast, re-solves dual)?
2. **Hard-tail arms:** H0 vs H1a only, or also H1b? And **Design A** (same settings) vs **Design B** (equalized Lagrangian effort — stronger but needs the budget-matched variant)?
3. **Repo scope (4.1):** full public source repo (preferred for COR) vs reproducibility archive only? (User previously said "not yet on repo stage.")

## Definition of done
- `verify_certificates.py` passes on all 660 (primal + dual); `verification_report.csv` archived.
- Every manuscript number regenerable from `adaptive_master.csv` (+ subset CSVs) via `build_*`.
- Hard-tail table populated; wording matches the evidence band.
- Reproducibility paragraph + appendix sentence added (only because implemented).
