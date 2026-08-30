---
name: project-roadmap
description: Full trajectory for the SRPS-ALNS COR paper — status, manuscript state, reproducibility map, and next actions
metadata:
  type: project
---

# SRPS-ALNS COR Paper — Trajectory

Last updated: 2026-06-22 (full LaTeX manuscript drafted)

## Status snapshot

| Phase | Scope | Status |
|-------|-------|--------|
| A | Algorithm gate (selection, 660-run, validation, QA) | ✓ DONE |
| B | Experiments (sensitivity, ablation) | ✓ DONE |
| C | Paper content (skeleton, numbers, **LaTeX manuscript**) | ✓ DONE (draft) |
| D | Production (lit review, co-author review, submission) | ◐ IN PROGRESS |

The paper now exists as a **complete LaTeX draft**, not just a skeleton. Remaining work is
literature review depth, co-author review, and submission mechanics.

## The manuscript (deliverable)

- **`paper/main_standalone.tex`** — single self-contained file (figures as native pgfplots/TikZ,
  bibliography inline as `thebibliography`). Upload-to-Overleaf ready, no external assets.
- **`paper/main.tex` + `paper/refs.bib` + `paper/figures/*.pdf`** — modular version (now in sync).
- Both files share: BKS-free Algorithm 1 (θ*=incumbent), references **before** appendices,
  `placeins` float guards, `\resizebox` on wide tables, ORCID for Y. Ben-Abu.
- All tables/figures/appendices filled with adaptive-canonical numbers; abstract written.

## Reproducibility map (every paper number ← a committed script)

- `build_paper_stats.py` → §6.1–6.3 headline (cert tiers, BEAT/TIE/GAP, runtime, first-ever)
- `run_quality_analysis.py --csv results/adaptive_master.csv` → §6.5.3 + Appendix B (Tobit/LR)
- `build_appendix_A.py` → §6.5.1 ablation + Appendix A
- `build_sensitivity_summary.py` → §6.5.2 + §5 parameter justification
- `build_bpc_comparison.py` + `build_bpc_times.py` → §6.2 (incl. BPC per-group times from the PDF)
- `build_bpc_subgroups.py` → §6.2 A/B/C subgroup table (`tab:bpcsplit`), validity-guarded; replaces
  the old 2-way split and absorbs the former `tab:runtime`
- `build_figures.py` → both figures

Canonical data: `results/adaptive_master.csv` column `final_cert_gap_pct` (adaptive loop).
`master_results.csv` (old non-adaptive solver) is retired — do not cite.

## Next actions (priority order)

1. **Enhance literature review and references (Step 8) — TOP PRIORITY.**
   **Progress 2026-06-24: bibliography 7 → 12** (all Crossref-verified). Full plan, themes, and the
   mandatory verify-before-insert protocol are in **`docs/literature_roadmap.md`**.
   ⚠️ Every reference handed to us so far has had **fabricated metadata** (good title, invented
   authors/venue/DOI) — verify each candidate on Crossref before inserting; update BOTH
   `paper/refs.bib` AND the inline `thebibliography` in `paper/main_standalone.tex`.
   Remaining trajectory (target ~18–25): deepen Lagrangian-in-heuristics / matheuristics,
   OP/TOP metaheuristic breadth, optimality-certification refs, and telescope/observation-scheduling
   application context. Weave into §1, §2.1, §3, §4.
2. **Algorithm 2** (synchronisation-aware insertion) pseudo-code box — optional but reviewer-friendly.
3. **Co-author review pass** (David + Yuval).
4. **Submission prep**: cover letter, COR formatting check, data/code availability statement with a
   public-repo URL, confirm the §6.1 hardware line is the actual experiment machine.

## Resolved decisions / standing facts

- **QA canonical** = `adaptive_master.csv` (adaptive); `master_results.csv` retired.
- **BKS-free**: verified the canonical runs never used the published BKS as the Polyak θ*
  (`run_adaptive_full.py` uses `lower_bound=best_obj`); BKS is used only for the BEAT/TIE/GAP labels.
  Algorithm 1 and §4.2/§4.3 corrected accordingly.
- **Headline numbers**: mean cert 0.133%, 42.9% (283/660) proven optimal, 100% within 2%, max 1.965%;
  BEAT/TIE/GAP 24/425/12; 196 first-ever; median runtime 5.1 min.
  (Validity guard: UB never below a known feasible obj; flips ED_n045_008_a75_024 from exact to
  0.068%, so 283 not 284. First-ever 196 = BPC-unreported + no BKS; 3 partial-group blanks grouped w/ C.)

**Why:** experiments are complete and the manuscript is drafted; the paper's remaining gap is
scholarly depth (literature/references) plus co-author review and submission mechanics.
