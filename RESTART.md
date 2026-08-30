# RESTART — SRPS-ALNS COR Paper
*Last updated: 2026-06-24. Read this first every new session.*

**Full trajectory → `memory/project_roadmap.md` · COR revision plan → `docs/cor_revision_roadmap.md`
· reproducibility/verification → `docs/reproducibility_roadmap.md`**

---

## Where we are

Experiments **done**; **complete LaTeX manuscript** drafted; the two defensibility pillars are now
**closed** (independent verification + hard-tail refresh evidence). Remaining: co-author review and
submission mechanics.

- **Certificate verification (referee-grade):** full independent `--rederive-only` run —
  **660/660 pass** (feasibility + bound dominance + objectives match `adaptive_master.csv`).
  `scripts/verify_certificates.py` → `results/verification_report.csv`.
- **Hard-tail in-loop re-bound evidence:** H0 vs H1a on the 70 → mean gap **0.955%→0.691%**
  (Δ +0.264 pp, 53/70 improved). `tab:hardtail-refresh` in §6.5. Reproduce: `run_adaptive_full.py
  --subset results/hard_tail_70.csv [--no-refresh] --save-suffix _x` then `build_hardtail_refresh.py`.
- **References:** now **23**, all Crossref-verified (see `docs/literature_roadmap.md`).
- **Repo:** `requirements.txt`, `CITATION.cff`, MIT `LICENSE`, reproduction README in place.

- Paper algorithm: the **adaptive loop** (multi-seed ALNS in runtime-budgeted phases + in-loop
  warm-Polyak Lagrangian re-bounding). Certified primal–dual method.
- Canonical results: **`results/adaptive_master.csv`**, column **`final_cert_gap_pct`**.
  The old non-adaptive `master_results.csv` is **retired — do not cite**.

## The manuscript (in `paper/`)

- **`paper/main_standalone.tex`** — SINGLE self-contained file (TikZ figures + inline bibliography).
  This is the one to upload to Overleaf; no external assets needed.
- **`paper/main.tex` + `paper/refs.bib` + `paper/figures/*.pdf`** — modular version, kept in sync.
- Both: BKS-free Algorithm 1 (θ*=incumbent), references **before** appendices, `placeins` float
  guards, `\resizebox` wide tables, ORCID 0000-0002-6983-5730 for Y. Ben-Abu.
- Compiles on Overleaf (pdfLaTeX). No LaTeX toolchain installed locally — cannot compile here.

## Headline numbers (all script-derived)

mean cert **0.133%** · median 0.046% · max **1.965%** · **42.9% (283/660) proven optimal** ·
94.1% within 0.5% · **100% within 2%** · BEAT/TIE/GAP **24/425/12** · **196 first-ever** ·
median runtime **5.1 min** (max 40.8). Hardness: α dominant; residual via **α×distance** + n×K.

Validity guard (applied in `build_paper_stats.py`, `build_figures.py`, `build_bpc_subgroups.py`):
a certified UB is never reported below a known feasible objective. This flips the single
instance `ED_n045_008_a75_024` (adaptive UB underran the BPC-proven optimum by 1) from
"proven optimal" to 0.068% — hence 283 not 284. First-ever is 196 (BPC-unreported + no BKS);
3 blank-BKS instances from partially-solved BPC groups are ambiguous, grouped with C by footnote.
§6.2 now uses the A/B/C subgroup table (`build_bpc_subgroups.py`): A 245 (A1 241 / A2 4) ·
B 112 (B1 15 / B2 93 / B3 4) · C 300, framed as no/positive/principal contribution.

## Reproducibility — every number ← a committed script

| Script | Produces |
|--------|----------|
| `build_paper_stats.py` | §6.1–6.3 headline → `results/analysis/paper_stats_*.txt/json` |
| `run_quality_analysis.py --csv results/adaptive_master.csv` | §6.5.3 + App B (Tobit/LR) |
| `build_appendix_A.py` | §6.5.1 ablation + App A |
| `build_sensitivity_summary.py` | §6.5.2 + §5 parameter justification |
| `build_bpc_comparison.py`, `build_bpc_times.py` | §6.2 (BPC split + per-group times) |
| `build_bpc_subgroups.py` | §6.2 A/B/C subgroup table (`tab:bpcsplit`, validity-guarded) |
| `build_figures.py` | both figures (`paper/figures/*.pdf`) |

## Literature review + references — now at 18 (in target band)

References grew **7 → 12 → 18** (all Crossref-verified; see `docs/literature_roadmap.md`). The 18 are
inside the ~18–25 target band and cover SRPS/exact, OP/TOP metaheuristics + ALNS, synchronised/
prize-collecting routing, Lagrangian/subgradient/matheuristics, and the telescope-scheduling
application. **Both** `paper/refs.bib` and the inline `thebibliography` in `paper/main_standalone.tex`
are in sync; lint passes (cites==bibitems==refs.bib, both `.tex` identical cite-sets). Only open
sub-theme is Phase C (certification-in-heuristics) — left out to avoid fabrication risk, non-blocking.
Protocol for any further refs: **verify each on Crossref before inserting; never fabricate metadata.**

Then: Algorithm 2 (sync-aware insertion, optional) · co-author review · submission (cover letter,
data/code-availability statement w/ public-repo URL, confirm §6.1 hardware is the experiment machine).

## Standing facts (resolved this session)

- **BKS-free**: canonical runs never used published BKS as θ* (`run_adaptive_full.py` uses
  `lower_bound=best_obj`); BKS only labels BEAT/TIE/GAP. Algorithm 1 + §4.2/§4.3 corrected.
- **Runtime vs BPC** (§6.2): BPC's 1-hour limit is a *cap*; per-group, BPC is ~8× faster on the
  easy/solved groups (we claim no advantage there), we are ~2.5× faster on the hard groups and the
  only solver on the 300 it never reports.
- Repo cleaned: legacy non-adaptive scripts in local `archive/` (gitignored); `master` branch.

## Git

On `master`. The `paper/` manuscript bundle, generators, roadmaps, and this RESTART were committed
in the 2026-06-22 manuscript commit (see `git log`). `archive/` and `results/beta_incumbents/` are
gitignored (kept locally).
