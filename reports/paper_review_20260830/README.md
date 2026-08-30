# Specialized paper-review panel — 2026-08-30

The following workspace agents are reusable, read-only specialists. They were
run independently against the main paper, supplementary material, code, and
available artifacts. Reports record review findings; they are not accepted
changes or evidence beyond the sources they cite.

| Agent | Specialty | Report |
| --- | --- | --- |
| Method–Code Reviewer | Algorithms, pseudocode, and implementation alignment | `01_method_code_alignment.md` |
| Certificate Auditor | Lagrangian validity, numeric safeguarding, stored certificates, and Path B | `02_certificate_validity.md` |
| Experiment & Statistics Reviewer | Experimental design, noise, ablation, sensitivity, and inference | `03_experiment_statistics.md` |
| Reproducibility & Provenance Reviewer | Inputs, scripts, documented commands, and clean-clone boundaries | `04_reproducibility_provenance.md` |
| Literature & Claims Reviewer | Novelty, terminology, attribution, and comparison calibration | `05_literature_claims.md` |
| Journal Clarity Reviewer | COR presentation, notation, captions, structure, and supplement integration | `06_journal_clarity.md` |

## Triage

1. Reconcile the reported refinement workflow with the historical driver;
   preserve historical results while making the separate refinement stage
   explicit.
2. Clarify the fixed-bound ablation estimand and the conditional/conservative
   use of its Tier-2 noise-derived MDE.
3. Make clean-clone boundaries and the obsolete ablation guard unambiguous.
4. Narrow terminology and comparative claims, then improve notation and
   supplementary-material navigation.

The agent definitions are stored under `.github/agents/` and are available from
the workspace agent picker.