# Known issues

Recorded so they are not rediscovered. Neither affects the validity of any
published certificate: every reported upper bound is a valid upper bound, and
both issues make reported gaps *wider* than necessary, never narrower.

## 1. The in-loop re-bound can replace a tighter bound with a looser one

`run_adaptive_full.py`, in the re-bound block:

```python
new_ub = math.floor(lag["upper_bound"])
...
ub = new_ub          # assignment, not min(ub, new_ub)
```

The initial bound is `min(independent_orienteering, group_decomposition)` from
`core/ops_bounds.best_upper_bound`. The in-loop refresh computes a *Lagrangian*
bound, a different relaxation family, and on some instances the first refresh
returns a larger value. Because the assignment is unconditional, that looser
value replaces the tighter initial bound.

Measured on the canonical 660-instance run:

| quantity                                | value    |
|-----------------------------------------|----------|
| instances where reported ub > initial ub | 10       |
| mean gap overstated on those             | 0.044 pp |
| effect on the 660-instance mean          | 0.0007 pp |
| reported maximum gap                     | 1.965 %  |
| maximum under `min(ub, new_ub)`          | 1.860 %  |

The fix is `ub = min(ub, new_ub)`; both quantities are valid upper bounds, so
the minimum is valid and never looser. It is **deliberately not applied** to the
archived driver: the published results were produced without it. Algorithm 1
states the monotone update used by post-search refinement; the main text now
discloses that the historical in-loop driver differs. Apply the fix only with a
newly labelled campaign, or as a documented reporting-level correction if the
numbers are regenerated.

Note that the paper's Appendix A already documents the symmetric safeguard in
the other direction (never reporting a bound below an independently proven
optimum), so the precedent for a reporting-level correction exists.

## 2. The dual budget does not transfer at a fixed runtime cap

Raising the subgradient budget tightens the Lagrangian bound when the dual is
measured in isolation. It does not improve end-to-end results at the solver's
3600 s per-instance cap, and it is worth recording why, because the isolated
measurement is genuinely positive and misleading on its own.

Measured 2026-08-26 on a cold 660-instance run, stopped at 50 instances
(`archive/dual_budget_1000x300/`):

* At `lag_max_iter=1000, lag_max_time=300`, dual time is taken from the primal
  search. Grouping by dual work done: 0 iterations -> mean dz -0.24; 1..2000 ->
  -1.00; >=2000 -> **-4.50**. Seven instances lost proven-optimal status against
  one gained; runtime rose to 1.21x canonical.
* At `lag_max_iter=1000, lag_max_time=60`, wall-clock is unchanged from
  canonical, but the subgradient runs at only ~2.6 iterations/second on the
  large instances, so 60 s buys ~156 iterations -- fewer than the existing
  200-iteration cap. The iteration cap was never the binding constraint there.

So the extra iterations are available only on small, fast instances, which are
already closed by the construction fast path or the 0.3 % threshold, and are
unavailable on the hard instances where headroom exists.

Warm-start probes of the same change looked strongly positive (-0.49 pp, 4/4
improved). That is a confound: warm-starting fixes `z` at the canonical optimum,
so no primal work is needed and dual time is free. It measures the dual in
isolation, not the solver.

## 3. Invalidated A0–A5 ablation builder

`build_appendix_A.py` supported the superseded A0–A5 ablation design. It is not
a source for any current manuscript result and deliberately refuses execution.
Use `build_ablation_summary.py` for the redesigned B1–B8+S study.
