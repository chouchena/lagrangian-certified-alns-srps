# Session state — SRPS-ALNS
<!-- Updated by Copilot at each checkpoint. -->

**Saved:** 2026-08-30
**HEAD:** `4b9cee8` (`docs: complete submission audit corrections`)
**Branch:** `master`

## Current status

The numerical campaign and manuscript integration are complete. No experiment
is running. The current paper uses `results/adaptive_master_refined.csv` as the
canonical post-refinement 660-instance series. Tier-2 noise-floor evidence,
the redesigned B1--B8+S ablation (400/400 runs), the 70-instance hard-tail
re-bound census, sensitivity summaries, and Path-B certificate verification
have been completed and integrated.

## Verified evidence

| Item | Status | Authoritative artifact |
| --- | --- | --- |
| Canonical 660 results | Complete | `results/adaptive_master_refined.csv` |
| Path-B numerical verification | 660/660 valid at zero tolerance | `results/analysis/path_b_verification_exact.csv` |
| Tier-2 hard-tail noise floor | Complete; mean $|\Delta|=0.0360$ pp | `results/analysis/noise_floor_20260828_1744.csv` |
| B1--B8+S ablation | Complete; 400/400 runs | `results/analysis/ablation_summary_20260830_0013.txt` |
| Re-bound census | Complete; mean certificate-gap reduction 0.2643 pp, objectives tie 70/70 | `results/analysis/hardtail_refresh_20260830_0013.txt` |
| OAT sensitivity | Complete; refinement-independent objective-value cross-check added 2026-08-30 (`03d668d`) | `results/analysis/sensitivity_summary_20260830_0656.csv` |
| Main manuscript build | Complete; 39 pages | `paper/main.tex` |
| Supplement build | Complete; 11 pages | `paper/supplementary.tex` |

## Submission tasks remaining

1. Suggested-reviewer section in `paper/cover_letter.md` is optional (not a
   COR/Elsevier submission requirement) and is populated with three
   citation-grounded candidates as a non-blocking courtesy. If kept, the
   corresponding author should verify affiliation/email/COI; it may also be
   submitted as-is or removed with no effect on submission validity.
2. Repository is public at the stated URL as of submission (2026-08-30);
   keep it in sync with the committed manuscript state through review.
3. Execute and record one fresh-clone validation of
   `python reproduce.py --manuscript-results` after installing requirements and
   public OPS inputs. `reproduce.py --all` remains a deliberately non-standalone
   legacy course-project protocol.
4. Perform a final PDF visual pass for table legibility, overfull boxes,
   captions, and bibliography metadata. The direct `pdflatex`/`bibtex` process
   is the available build route; `latexmk` cannot run because Perl is absent.
5. `paper/main.tex` now includes a Declaration of competing interest and
   `paper/highlights.txt` (5 bullets, COR/Elsevier format) has been added as a
   separate submission file. Confirm both against the journal's current
   submission-system upload checklist before finalizing.

## Guardrails

- Do not change the historical in-loop update in `run_adaptive_full.py` without
  a new, explicitly labelled campaign; it is retained for historical-result
  reproduction.
- Do not use `build_appendix_A.py`: it intentionally exits because the old
  A0--A5 ablation is invalidated.
- Keep fixed-common-bound B7 ablation outcomes separate from the re-bound
  census, which estimates certificate-tightening efficacy.
- Keep untracked monitoring helpers and timestamped derived outputs out of any
  broad commit unless intentionally releasing them.

## Recovery

The six independent specialist reports are indexed in
`reports/paper_review_20260830/README.md`; their reusable definitions are in
`.github/agents/`. The claim-level reproduction map is
`docs/REPRODUCIBILITY.md`.
