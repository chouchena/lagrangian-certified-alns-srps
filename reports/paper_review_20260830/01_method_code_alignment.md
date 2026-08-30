# Method–Code Reviewer report

## Scope
Algorithm and pseudocode alignment between the manuscript/supplement and the solver drivers and core implementation.

## Findings

### Blocker — refinement is not executed inside `run_adaptive_full.py`
The paper presents post-search refinement as part of the reported method, while `run_adaptive_full.py` ends after ejection/validation. The actual reproduction chain is separate: `run_bound_refine.py`, `build_adaptive_master_refined.py`, and `rebuild_bounds_certified.py`. This is a documentation/architecture discrepancy, not evidence that the refined results are invalid.

**Required resolution:** either integrate a documented refinement stage into the canonical driver or state consistently that refinement is a separately invoked post-search stage and ensure the reproduction command always runs it.

### Major — in-loop re-bound can replace a tighter bound
`run_adaptive_full.py` assigns the new bound rather than retaining `min(old, new)`. The code comments document that this can widen, but not invalidate, a reported certificate. The algorithm pseudocode describes monotone retention.

**Required resolution:** disclose the historical behaviour as a conservative bound-widening detail, or change the next-campaign code and rerun before using the altered rule for reported data.

### Minor — implementation/API detail
The pseudocode returns a compact conceptual tuple, while the driver returns a richer diagnostics dictionary. This is acceptable but should remain framed as pseudocode rather than literal API documentation.

## Confirmed alignment
The reviewer found the feasibility oracle, Lagrangian decomposition, destroy/repair family, simulated annealing/adaptive weights, and tier escalation consistent at the conceptual level.

## Priority
Resolve the refinement-chain description before submission; do not silently alter the historical driver and claim reproduction of the existing campaign.