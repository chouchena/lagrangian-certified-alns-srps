# Reproducibility & Provenance Reviewer report

## Scope
Claim-to-artifact-to-command traceability for the current manuscript.

## Findings

### Major — clean-clone scope needs an explicit boundary
`reproduce.py --all` lists course/development stages whose source directories may be ignored or maintained in the companion workspace. Do not describe that command as the standalone paper reproduction path unless each referenced stage is committed here or the dependency is documented and guarded.

### Major — README should separate recomputation from reruns
The README now points to `docs/REPRODUCIBILITY.md`, but it should conspicuously explain that `--manuscript-results` recomputes from committed artifacts, while full solver campaigns are time-budgeted reruns needing the public OPS input (and CPLEX for the compact-MIP check).

### Major — prevent accidental legacy ablation use
`build_appendix_A.py` is invalidated in prose but still executable. Add a runtime refusal directing users to `build_ablation_summary.py`, or relocate it to an explicitly archival directory.

### Minor — certificate-store naming
The canonical 660-certificate store and the legacy/exploratory beta store should be labelled prominently so the 70-instance checker is not mistaken for the paper-wide Path-B verifier.

### Minor — figures
The map states the generator and outputs; a small figure manifest would make label-to-file mapping machine-readable.

## Confirmed strength
`docs/REPRODUCIBILITY.md` maps the main results, BPC table, figures, ejection result, Path B, hard-tail census, Tier 2, ablation, sensitivity, refinement sweep, and operating-point replay to artifacts and commands. The operating-point phase log is now retained as an input.

## Priority
Clarify repository boundaries and block obsolete script execution before public release.