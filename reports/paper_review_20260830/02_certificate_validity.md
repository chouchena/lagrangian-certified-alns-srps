# Certificate Auditor report

## Scope
Lagrangian-bound validity, floating-point safeguarding, certificate provenance, and the independent Path-B check.

## Verdict
No certificate-validity blocker was identified. The weak-duality argument, exact per-processor DP, stored-certificate workflow, and `verify_interval_arithmetic.py --mode exact --csv` are coherent.

## Findings

### Major — disclose the historical non-monotone in-loop assignment
The in-loop driver may replace an earlier tighter bound with a later looser valid bound. This is conservative (the gap can widen, not become falsely tight), but the paper should describe it if its algorithm claims the minimum is retained.

### Minor — verifier scope should be precise
Path B independently recomputes the reported value from the raw instance and stored multipliers, without executing the search. It is independent of cached search objects, but it is not an independent solver proving a stronger bound. Use “independently verifiable” with that exact scope.

### Minor — numerical safeguard visibility
The supplement accurately describes the four floating-point floor corrections. Add a short main-text signpost to the safeguard so readers do not treat it as a cosmetic appendix detail.

## Evidence checked
- `core/ops_bounds.py`
- `verify_interval_arithmetic.py`
- `rebuild_bounds_certified.py`
- `results/certificates/`
- `results/analysis/path_b_verification_exact.csv`
- main and supplementary certificate sections

## Priority
Keep Path B as the canonical verification command and reconcile the stated in-loop bound update with the historical implementation.