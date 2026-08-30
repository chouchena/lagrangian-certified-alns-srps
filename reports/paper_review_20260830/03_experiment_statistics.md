# Experiment & Statistics Reviewer report

## Scope
Ablation, Tier-2 noise floor, sensitivity, refinement, CPLEX comparison, and statistical language.

## Findings

### Major — distinguish the fixed-bound ablation from the re-bound mechanism
B7 is scored with a common fixed certificate, so it tests the primal/stop-reason channel but cannot estimate its certificate-tightening effect. The manuscript should state this explicitly beside the B7 null and retain the 70-instance re-bound census as the dual-effect evidence.

### Major — noise-floor transfer is conservative but conditional
The 0.036 pp hard-tail noise estimate uses disjoint 3-seed arms, whereas the ablation uses six seeds per arm and includes a closing stratum. The current MDE should be described as conditional and conservative, not as a direct variance estimate for every arm/stratum.

### Major — keep subgroup patterns exploratory
The family-by-stratum cells are small. The supplement labels them hypothesis-generating; the main text should not elevate B1/B2 concentration patterns to confirmatory findings.

### Minor — sensitivity and hardness limitations
The OAT sensitivity study does not estimate interactions. The censored-regression analysis should remain diagnostic, with its heavy zero mass and series choice stated clearly.

### Minor — comparison framing
The compact CPLEX run is a limited external check, not a controlled runtime benchmark. Reiterate the hardware/time-limit distinction where runtimes are tabulated.

## Strengths
The final B1–B8+S design has stratified reporting, a declared fixed-bound estimand, completed 400/400 rows, no duplicate keys/errors, and an explicitly measured Tier-2 scale.

## Priority
Revise interpretation and disclosure; no new experiment is implied by these findings.