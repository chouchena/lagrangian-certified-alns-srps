# Ablation redesign — specification for review

**Status:** completed 2026-08-29: 400/400 runs (10 arms $\times$ 40
instances). The authoritative derived report is
`results/analysis/ablation_summary_20260830_0013.txt`.
**Supersedes:** `run_ablation.py`'s A0–A5 design (stopped mid-run 2026-08-27).

---

## Why the previous design is being replaced

Three defects, all measured rather than suspected:

1. **The sample could not discriminate.** 19 of its 30 instances stop in phase 1
   (10 at `UB`, 19 at `GAP<0.3%`), and tier escalation, UB refresh and every
   stall-triggered mechanism act only *after* phase 1. On those instances A0,
   A2, A3 and A5 are the same code path. Exactly **one** instance was
   `TIERS_EXHAUSTED` — the population where those mechanisms live.
2. **The arms miss the method's defining feature.** No arm tested the adaptive
   operator weights, the simulated-annealing acceptance, the destroy pool, or
   the ejection chain. The paper is titled "An *Adaptive* Large Neighborhood
   Search" and contained no evidence the adaptivity does anything.
3. **Arms were scored against a bound they had removed the machinery to
   produce.** A3/A5 disable the re-bound, then were measured against A0's
   refreshed bound. Fixed separately (`cert_gap_own_pct`), but it invalidated
   the reported A3/A5 numbers.

---

## Sample

**40 instances, common to every arm**, drawn from the 268 that run more than
one phase (of 660). Stratified:

| stratum | n | rationale |
|---|---|---|
| hard tail (`TIERS_EXHAUSTED`) | 20 | of 70; where stall-triggered mechanisms act throughout |
| multi-phase, closes at `GAP<0.3%` | 20 | of 198; mechanisms act but the instance still closes |

Within each stratum, stratify on **structural properties only** — family, $n$,
$\alpha$ — never on a prior run's gap or objective.

**Known exposure.** Membership uses `beta_phases > 1` and `beta_stop_reason`
from a prior campaign, so the sample is chosen using earlier *outcomes*. The
criterion is "instances where the mechanisms can act", not "instances where the
mechanisms look good". It is not derived from any ablation-arm result and is a
scope limitation of the completed study.

---

## Arms — 10 configurations

| id | configuration | isolates |
|---|---|---|
| A0 | full method | baseline (top of range) |
| B1 | uniform random operator choice (no adaptive weights, no $\sigma$ scoring, no decay) | the "A" in ALNS |
| B2 | greedy acceptance (reject all worsening moves) | simulated annealing |
| B3 | destroy pool → `destroy_random` only | destroy diversity |
| B4 | repair pool → `_repair_profit` only | repair diversity |
| B5 | no ejection chain | post-loop improvement |
| B6 | no tier escalation | destroy-size adaptation |
| B7 | no in-loop re-bound | dual refresh on stall |
| B8 | single seed | multi-start |
| **S** | **all of B1–B8 simultaneously** | **total value of the apparatus** |

---

## Comparisons

Bounds are **fixed from `results/bounds_certified.csv`** — every instance has a
certified bound with a deposited multiplier vector. No arm computes its own
initial bound, and no `adaptive_master.csv` read remains.

Two effects per arm, both paired per instance:

```
marginal(X) = gap(B_X) - gap(A0)          "what does removing X cost?"
total       = gap(S)   - gap(A0)          "what does the apparatus buy?"
```

and the diagnostic that neither alone provides:

```
sum of marginals   vs   total
```

If they agree, components are independent and each earns its place. If
`sum(marginal) << total`, the components are **redundant** — each covers for the
others, and the algorithm can be simplified. That is a publishable finding and
the previous design could not detect it.

Each arm reports both channels:
- `cert_gap_pct` — against the common certified bound (**primal** effect)
- `cert_gap_own_pct` — against the bound the arm itself held (**certificate**
  effect; the only meaningful one for B6/B7)

---

## Completed results and reporting

The hard-tail disjoint-seed Tier-2 replicate measured mean
$|\Delta|=0.0360$ pp. Under the explicitly stated comparability assumption,
this gives a two-sided $\alpha=0.05$, 80\%-power MDE of $0.0839$ pp for each
$n=20$ stratum; it is not an ablation-internal replicate estimate. Repair-pool
diversity (B4) is the only large marginal effect: removing it costs
$2.49$--$2.50$ pp in each stratum. The all-off arm S costs $2.51$--$2.53$ pp.
B2 is $+0.0995$ pp on the hard tail; remaining mean effects are at or below
the MDE. B7 ties A0 on the fixed-common-bound primal outcome by design and
must not be interpreted as evidence against in-loop re-bound efficacy. The
separate 70-instance H0/H1a census estimates a 0.2643 pp mean reduction in
pre-refinement certificate gap, with identical objectives on all 70 instances.

## Reporting

**Stratified, never pooled.** B6 and B7 cannot act on non-stalling instances —
there they are bit-identical to A0 by construction, and that identity is
verified rather than assumed. Reporting a mean across both strata would dilute
a hard-tail mechanism across instances where it never fires, which is precisely
how tier escalation came to read as "+0.002 pp, apparently useless".

Every table states each arm's population. The text must not average across
strata.

**A null result is a finding, not a footnote.** If a component shows no effect
where it can act, the paper says so and either removes it, scopes it to a
subpopulation, or justifies it on non-performance grounds. Reporting a
near-zero effect and silently keeping the component is what the current draft
does and it will not survive review.

---

## Budget

400 runs (10 x 40). Sample mean 1068 s (hard tail 1284 s, closing 852 s).
118.7 core-hours -> **~20 h at 6 workers**. Cap aligned to the main campaign's
3600 s; only 8 of 268 discriminating instances exceed 1800 s and none exceeds
3600 s.

Costed conservatively: every arm is priced at A0's runtime, though B8 and S do
less work per phase.

---

## Known limitations, stated in advance

- **Power.** Twenty instances per stratum resolve the large B4/S effects but
  not effects near 0.02 pp. The reported 0.0839 pp MDE is conditional on
  variance comparability with the Tier-2 hard-tail replicate.
- **No ablation-internal replicate.** The $0.0360$ pp hard-tail Tier-2 estimate
  is the relevant imported noise reference. The $0.005$ pp sensitivity duplicate
  came from a different 30-instance sample and is not used as the ablation noise
  floor.
- **Insertion candidate cap $c$ is untested**, as is the refinement stage
  (covered separately by the 280 -> 446 figure).
- **Interactions beyond S are untested.** Only the all-off configuration probes
  joint effects; pairwise interactions are not covered.
