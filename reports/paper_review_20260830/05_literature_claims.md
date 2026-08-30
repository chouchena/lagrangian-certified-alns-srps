# Literature & Claims Reviewer report

## Scope
Novelty, terminology, BPC/CPLEX comparison, limitations, and conclusion calibration. This review uses local sources only and does not certify literature exhaustiveness.

## Findings

### Major — make the novelty claim singular and narrow
The draft alternates among “first SRPS-specific metaheuristic,” “first certified primal–dual heuristic,” and broader statements about related synchronised-routing problems. Use one qualified, implementation-specific formulation throughout: an ALNS-based SRPS heuristic coupled with in-loop Lagrangian certification and per-instance verifiable gaps.

### Major — retain a sharp distinction between terms
“Primal–dual heuristic,” “primal–dual approximation algorithm,” and “Lagrangian-certified heuristic” need one stable definition. Avoid language that could imply an approximation ratio or complementary-slackness guarantee.

### Major — compare coverage/quality, not speed
BPC CPU times and the Python solver’s contended wall-clock times are not a controlled comparison. The prose contains caveats, but the table/abstract should foreground coverage, incumbent quality, and certification instead of inviting speed conclusions.

### Minor — validation-set scope
The 241/245 recovery rate is strong evidence on instances BPC closed. Describe it as validation on known-optimum instances, not proof that the primal is validated uniformly across open cases.

### Minor — CPLEX scope
Call the 30-instance, 180-second, six-thread compact-MIP run an external sanity check, not a baseline-performance comparison.

## Priority
Narrow and standardize claims before any submission; no claim should rely on a literature search not recorded in the repository.