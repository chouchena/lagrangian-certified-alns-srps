# Clean rebuild plan — one campaign, one artifact set, no further runs

**Status:** proposed, not started
**Supersedes:** every result artifact currently in `results/`
**Governing principle:** no speed compromises. Where a choice exists between
fast and defensible, take defensible.

---

## Why this exists

The current results are a stratigraphy of campaigns rather than a run:

```
prior beta campaigns   → results/beta_incumbents/*.pkl      (incumbents)
run_ops_bounds.py      → results/master_results.csv         (bounds, BKS-seeded)
        ↓
run_adaptive_full.py   → results/adaptive_master.csv        (reads both)
        ↓
run_bound_refine.py    → results/bound_refine_corrected.csv (separate pass)
        ↓
+ F4 = {4 instances hardcoded in analyse_operating_points.py}
        ↓
tables built from two different CSVs; operating points replayed from an
archived June-19 phase log; ablation, sensitivity and Tobit from three more
separate runs
```

Each layer is defensible alone. Together the provenance cannot be stated in one
sentence, which is precisely how two results tables came to be built from the
pre-refinement series without anyone noticing, and how a hardcoded four-instance
correction came to live inside an analysis script.

This plan replaces all of it with **one campaign from one frozen commit**,
instrumented so that every question we have asked post-hoc — and the ones we
have not thought of yet — can be answered from the logs without running
anything again.

---

## Design rules

**R1 — Nothing is inherited.** No incumbent, bound, or parameter is read from a
prior campaign. Every number in the paper traces to this campaign's own output.

**R2 — Every artifact carries its provenance.** Each output CSV embeds the git
commit, whether the tree was dirty, the full argv, the Python and package
versions, the machine, and the wall-clock start. A dirty tree aborts the run.

**R3 — Determinism where it is affordable, disclosure where it is not.** Phase
budgets are wall-clock, because a time budget is the honest operating model for
telescope scheduling and the 1 h cap is a real constraint. That makes bit-exact
reproduction impossible by construction, so: (a) every phase logs its realised
iteration count, (b) a `--replay` mode re-runs from recorded iteration counts
instead of time budgets and *is* bit-exact, (c) nothing downstream of the search
uses a wall-clock cap — refinement becomes iteration-only.

**R4 — No hardcoded corrections anywhere.** A defect gets fixed in the code path
that produced it, never patched in a dict in an analysis script.

**R5 — One master, one orchestrator.** A single `results/master.csv` and a
single `make_paper.py` that regenerates every table and figure from it. No
generator may read any other results file.

**R6 — Every experiment is pre-registered before the campaign runs.** Sample
membership, seeds, arms and sweeps are written to disk and hashed *before*
execution, so no selection can be made after seeing outcomes.

**R7 — Gates, not inspections.** Each stage ends in an automated check that
exits non-zero. A stage that cannot be gated does not advance.

---

## Stage A — Code remediation

*Nothing runs until these are done and the tree is re-frozen.*

| # | Defect | Remedy |
|---|---|---|
| A1 | `--cold-start` only redirects the incumbent directory; `run_adaptive_full.py:176` reads the inherited bound unconditionally | Compute the initial bound in-process. Delete the `master_results.csv` read path entirely — not gated behind a flag, removed. |
| A2 | Incumbents load from `beta_incumbents/*.pkl` | Remove the warm-start read path. Greedy construction only. |
| A3 | `master_*` columns propagate an earlier campaign into the output | Drop them from the schema. |
| A4 | `F4` dict hardcodes four instance corrections | Delete. The ε tolerance (A5) makes it unnecessary. |
| A5 | Flooring defect: `floor(L(μ))` can drop a profit unit | ε = 1e-9 applied at **every** flooring site. Add a module-level `floor_bound()` so there is one site, and grep-gate that no bare `math.floor` touches a bound. |
| A6 | Refinement's 600 s wall-clock cap made 4 instances non-deterministic | Iteration cap only. No time cap anywhere post-search. |
| A7 | Refinement skips zero-gap instances, so it could never catch a too-tight bound | Run refinement on **every** instance. Cost is irrelevant here; the skip existed only to save time, and it created a blind spot exactly where the flooring defect lives. |
| A8 | Ejection chain runs after the loop but replay ignores it | Log the post-loop state separately so any replay reconstructs it. |
| A9 | Seeds not recoverable per phase | Log the seed list, per-seed iteration counts and per-seed objectives for every phase. |
| A10 | PowerShell BOM broke a subset read | All readers use `utf-8-sig`; all writers use `utf-8` without BOM. Add a gate. |

**Gate A:** `checks/check_no_inheritance.py` — greps the codebase and fails if
any run path references `master_results.csv`, `beta_incumbents`, a hardcoded
instance dict, a bare `math.floor` on a bound, or a wall-clock cap outside the
search loop.

---

## Stage A2 — Adversarial pre-validation of this plan

*Before any compute is spent.* The plan itself is an artifact and gets the same
treatment as the paper: a cold reviewer that did not write it, attacking it on
completeness of the "no more runs" promise, residual contamination, gate
adequacy, stage ordering, statistical validity, whether `--replay` can actually
deliver determinism under a stochastic parallel search, and what the monitoring
would miss.

The specific test is the plan's central claim: enumerate the questions a referee
would ask, and check each is answerable from the artifacts Stages E–G produce.
**Every question requiring a new run is a hole**, and a hole found here costs
minutes rather than days.

**Gate A2:** no BLOCKER findings outstanding. Weaknesses are either fixed or
recorded in the plan as accepted, with the reason.

---

## Stage B — Foundation verification

**This is the highest-value stage and has never been done.** Every certificate
in the paper reduces to one claim: the per-processor orienteering subproblems
are solved *exactly* by the bitmask DP. No check in the repository tests it —
they all call the same function, so a bug would be invisible to all of them.

| Step | Action |
|---|---|
| B1 | Brute-force enumerator for `O_k(μ)`, independent implementation, no shared code with `core/ops_bounds.py` |
| B2 | Exhaustive cross-check on all subproblems with \|J_k\| ≤ 10 drawn from real instances, over randomised μ including degenerate cases (all-zero, all-equal, one dominant) |
| B3 | Property tests: monotonicity in μ, correct handling of empty J_k, horizon-binding routes, elementarity, depot return |
| B4 | Weak-duality spot check: for random μ and random *feasible* primal solutions, assert `z ≤ L(μ)` |

**Gate B:** zero mismatches. If any appear, the campaign does not start — the
paper's central claim would be unsound and that must be resolved first.

---

## Stage C — Smoke validation

Small, fast, and purely about correctness of the machinery.

| Step | Action |
|---|---|
| C1 | 6 instances spanning families and α, full pipeline end to end |
| C2 | Assert every logged field is populated and typed; no silent `None` columns |
| C3 | Assert `cumul_rt` closes over `phase_rt + lag_s` per phase |
| C4 | Assert the provenance block is present and the commit matches `git rev-parse HEAD` |
| C5 | Run the same instance twice under `--replay` and assert bit-exact equality |
| C6 | Assert bound ≥ incumbent at every phase, and that refinement never loosens |

**Gate C:** all assertions pass. This is a machinery test, not a results test —
no conclusions are drawn from it.

---

## Stage D — Pre-registration and stratification

Written to `configs/preregistration.json` and **hashed before Stage E runs.**
The hash is printed in every downstream artifact.

| Item | Content |
|---|---|
| D1 | Study-set definition: all families except A and EA (\|K_j\|=1), 660 instances, listed explicitly by name |
| D2 | Instance manifest with SHA-256 of every instance file |
| D2b | Worker count, pinned at 6 and recorded. Phase budgets are wall-clock, so contention affects how many ALNS iterations fit in a phase; varying workers between the main run and the ablation/sensitivity arms would make them incomparable. |
| D3 | Master seed, and the derived per-instance seed sequence (`SEEDS = [42,123,456,789,1337,2024]` and how they map) |
| D4 | Ablation arms A0–A5, defined as code paths, with their sample |
| D5 | Sensitivity sweep: every parameter and its levels, single run per level, **no duplicates** |
| D6 | Sample design: ablation and sensitivity get **separate, independent samples** — the current design reuses the same 30 instances, and its measured effects (0/30, 1/30, 1/30) sit below its own baseline noise of 0.0045 pp. **Stratify on structural properties only** — family, $n$, $\alpha$, $\|K_j\|$. Never on a prior run's outcome: `build_regime_sample.py` stratifies on previously certified gaps, which would select today's sample using yesterday's results and contaminate the design even though no old number reaches the paper. |
| D7 | Operating-point regimes κ = 1, 2, 3, extracted from the main campaign by the prefix property — no separate runs |
| D8 | Tobit specification, fixed in advance, and the series it is estimated on |

**Sample sizing — by power calculation, not by guess.** The current 30-instance
design reports effects of +0.002 pp for arms A2, A4 and A5 against a measured
baseline noise of 0.0045 pp between two runs of the *same* configuration. Those
effects are below the design's own resolution, and each rests on a single
differing instance out of 30.

Before sizing, compute the detectable effect: draw the paired per-instance
differences **from Stage E's own output** — never from a prior campaign, which
would size the new experiment on old outcomes — estimate their standard
deviation, and solve for the *n* that resolves each arm's observed effect at
80% power. Stage E precedes Stage G, so this ordering costs nothing.

Two outcomes are possible and both are acceptable:

- **The effect is resolvable at feasible *n*.** Size to it. A1 (+0.022 pp,
  10 of 30 instances differing) is in this class.
- **No feasible *n* resolves it.** Then the honest report is "this component's
  effect is below what a benchmark of this size can resolve", not a table of
  0.002 pp deltas presented as measurements. Running 40 hours to fail to detect
  a null is not rigour, it is expense.

State the detectable effect size in the paper either way. That is what turns the
ablation from a list of numbers into a claim a referee can evaluate.

**Gate D:** `checks/check_prereg.py` — the manifest hashes resolve, samples are
disjoint where they must be, no instance appears in a sample it should not, and
the file is committed before Stage E starts.

---

## Stage E — Main campaign

| Parameter | Value |
|---|---|
| Instances | 660 (the full study set) |
| Start | cold; greedy construction only |
| Initial bound | computed in-process |
| Phase budget | 300 s | 
| Absolute cap | 3600 s |
| Workers | **6, fixed for every experiment in the campaign** |
| Seeds | as pre-registered |

**Logging per phase** — everything already added plus what Stage A adds:
`phase`, `tier`, `obj`, `ub`, `raw_ub`, `stall_run`, `obj_improved`, `gap_pct`,
`seeds`, `seed_list`, `seed_iters`, `seed_objs`, `best_seed`, `alns_iters`,
`n_new_best`, `n_improve`, `n_accept_worse`, `d_weights`, `r_weights`,
`d_weights_best`, `r_weights_best`, `d_usage`, `r_usage`, `n_best_events`,
`first_best_s`, `last_best_s`, `best_trace`, `lag_s`, `lag_iters`,
`lag_converged`, `phase_rt`, `cumul_rt`, `event`.

**Why this list matters:** every post-hoc question we hit this session —
regime extraction, runtime decomposition, operator behaviour on stalled phases,
the search/dual split — was answerable only because a field happened to exist.
This list is chosen so the next such question does not require a re-run.

**Outputs:** `results/master.csv`, `results/master_phases.csv`,
`results/master_manifest.json`.

### E-mon — self-monitoring while it runs

A campaign of this length must not be inspected only at the end. Discovering at
hour 80 what was visible at hour 2 is the failure mode this stage exists to
prevent. `checks/monitor_campaign.py` runs alongside and writes
`results/monitor/<ts>.json` on every poll.

| # | Watch | Action on trip |
|---|---|---|
| E-mon1 | **Invariants on every completed instance**: bound ≥ incumbent; gap in [0, 100); stop reason recognised; every logged field populated and typed; `cumul_rt ≈ phase_rt + lag_s` per phase | **Abort the campaign.** An invariant violation means the artifact is unusable; continuing burns days producing it. |
| E-mon2 | **RT projection, size-weighted**. A naive `elapsed/completed x remaining` is a false-positive generator: instances are processed in ascending $n$ within each family, and per-instance cost is steeply superlinear in $n$ (measured: 3.6 s at $n{=}100$ rising to 61.8 s at $n{=}150$). Extrapolating the largest block across the whole run tripped a +43% drift warning in the first hour of a campaign that was healthy. Project from a cost model fitted on completed instances and applied to the $n$-distribution of those remaining. | Warn at ±25%, escalate at ±50% against the **size-weighted** projection only. |
| E-mon3 | **Hang detection**: any worker with no phase-log write for > 2× the absolute cap | Dump the worker's stack, record the instance, abort. Silent hangs are how a 20 h run becomes a 40 h run. |
| E-mon4 | **Distributional drift**: running mean/median gap and proven-optimal rate against the pilot's, by family and α | Warn only. This is a health signal, never a stopping rule — see E-mon6. |
| E-mon5 | **Resource**: free disk, memory per worker, thermal/CPU throttling | Warn early; a full disk mid-campaign loses the log, not just the run. |

**E-mon6 — monitoring is diagnostic, never adaptive.** No interim result may
change the campaign: not the parameters, not the sample, not the stopping rules,
not which instances are retained. Watching outcomes accumulate and then adjusting
anything is how a pre-registration becomes decorative. The only permitted
responses are *continue*, *abort*, or *fix a defect and restart from scratch* —
never *adjust and carry on*. Monitor output is written to a separate directory
and is not an input to any generator.

**E-mon7 — checkpoint and resume.** Per-instance results are flushed as they
complete, and a resume must re-verify the git commit, the pre-registration hash,
and the instance manifest before continuing. A resume whose provenance does not
match the original refuses to run — otherwise resumability quietly recreates the
mixed-campaign problem this whole plan exists to eliminate. A resumed campaign
records every interruption in its manifest.

**E-mon8 — the supervision wiring, concretely.**

A monitor that greps only for progress markers is silent through a crashloop, a
hung worker, and an OOM kill — and silence looks exactly like "still running".
The filter must cover every terminal state, so it is built as one alternation
over progress *and* the failure signatures worth acting on:

```
tail -f results/campaign_out.txt | grep -E --line-buffered \
  "wall=|FINAL:|ABORT|INVARIANT|DRIFT|HANG|Traceback|Error|FAILED|assert|Killed|OOM|MemoryError"
```

`--line-buffered` is not optional: without it matches sit in grep's buffer and
arrive in bursts, or never. `checks/monitor_campaign.py` emits the `ABORT`,
`INVARIANT`, `DRIFT` and `HANG` lines from E-mon1–E-mon5, so a single stream
carries both the campaign's own output and the supervisor's verdicts.

Escalation, by severity rather than by volume:

| Condition | Response |
|---|---|
| `INVARIANT` / `ABORT` | Stop the campaign immediately, push a notification, do not attempt repair in place |
| `HANG` | Dump the stack, record the instance, stop |
| `DRIFT` beyond ±50% | Push a notification with the restated ETA; the campaign continues — a schedule change is not a defect |
| Progress markers | Logged only, never pushed. A multi-day run must not notify on progress or the alerts become noise and get ignored precisely when one matters. |

Notifications are for conditions that need a human who may have walked away:
an abort, a hang, a materially changed ETA, and completion. Nothing else.

**Gate E:** every instance terminates with a recorded stop reason; no crashes;
provenance block matches Stage D's hash; no E-mon1 trip; the monitor log is
archived with the results as evidence the campaign ran clean.

---

## Stage F — Refinement

Runs on **all 660** (see A7), iteration-capped only, against each instance's own
final incumbent. Writes `results/master_refined.csv` as a **superset** of
`master.csv`, preserving both series explicitly:
`search_ub`, `search_gap_pct`, `refined_ub`, `refined_gap_pct`, `final_ub`,
`final_gap_pct`, `refine_iters`, `refine_s`.

**Naming is load-bearing.** The current `baseline_*` / `final_*` split is what
let two tables silently use the wrong series. Columns are now named for what
they are, and `check_claims.py` asserts which series each table used.

**Gate F:** refinement never loosens a bound; `final_ub = min(search_ub,
refined_ub)` holds for every row; every row has `refine_iters > 0`.

**Convergence must be reported, not assumed.** Measured on the certified
rebuild: refinement runs the full 3000 iterations on essentially every
instance and converges on **4 of 81** (the prior campaign: 14 of 376). The
reported bound is therefore a *truncated subgradient iterate, not a dual
optimum* -- the method is still descending when the cap cuts it off. Log
`refine_converged` per instance, report the rate, and state the cap as an
engineering choice rather than a convergence criterion. This is also the
honest answer to "why not more iterations", and it is stronger than
implying the dual is solved.

---

## Stage G — Derived experiments

All from the same frozen commit, all in one sweep, no separate campaigns.

| Experiment | Source |
|---|---|
| G1 Operating points κ=1,2,3 | Extracted from `master_phases.csv` by the prefix property. **The bound is the one recorded at the stopping phase**, not the completed run's — *and* refinement is re-run against the **truncated incumbent**, not the final one (see note). |
| G2 Ablation A0–A5 | 120 pre-registered instances, arms as code paths |
| G3 Sensitivity sweep | 120 pre-registered instances, one run per level |
| G4 Hard-tail re-bound (H0 vs H1a) | The TIERS_EXHAUSTED subset of the main campaign, plus one no-refresh arm |
| G5 CPLEX cross-check | **Time-matched**: CPLEX gets the same core-seconds our method used on each instance, not a flat 180 s × 6 threads |
| G6 Tobit | Estimated on **both** series, both reported |

**G1 method — DECIDED: paired extraction, not independent regime campaigns.**

Regimes are read from the main campaign's phase log rather than run separately.
Three independent campaigns would cost ~70 h and, more importantly, would be
*statistically weaker*: they introduce run-to-run variance between the regimes,
contaminating the very comparison the table makes. Paired extraction has zero
inter-regime variance by construction.

This is reviewer-safe only with all four of the following. Replay without them
is how the previous operating-points table acquired a real defect that stood
until an adversarial review found it:

1. **Structural justification.** `stop_at_stall` enters only the termination
   test; the search is untouched. This is a property of the code, checkable by
   reading it, not a statistical assumption.
2. **Both channels corrected.** The bound is read at the stopping phase, and
   refinement is re-run against the truncated incumbent. Crediting a truncated
   run either the completed run's bound or its refinement is the defect.
3. **No claim of exactness.** Phase budgets are wall-clock, so a κ-run is a
   prefix up to iteration jitter. Say that; do not say "exact".
4. **Validation at scale.** 60 instances executed independently at κ=1 and κ=2
   (~3 h), with the agreement reported as a result. The existing evidence is
   n=4, which is an anecdote. This converts the prefix property from an
   assertion into a measurement at 4% of the cost of full independence.

Budget: ~8 h regime refinement + ~3 h validation ≈ 11 h, against ~70 h for
independent campaigns that would answer a weaker question.

**On G1 — the part that cannot be replayed.** Two channels make a truncated run
worse, and only one can be read off a log. The *search bound* at the stopping
phase is recorded, so that channel is free. The *refinement* channel is not:
refinement's tightness depends on the incumbent used as its Polyak reference,
and a truncated run holds a lower incumbent than the completed one. Crediting a
truncated run the refinement value computed against the final incumbent
overstates it — and because refinement's bound usually dominates the search
bound, this is where essentially all the remaining optimism lives. Correcting it
requires **re-running refinement against each truncated incumbent**, which is a
real experiment, not a replay. Budget it: 660 instances × 2 regimes.

The prefix property justifies extraction, but phases are wall-clock
budgeted, so a κ-run is a prefix only up to scheduling noise. State it that way:
"the recorded state at the stopping phase, which a κ-run reproduces up to the
iteration jitter of a wall-clock budget", and cite the `--replay` mode as the
deterministic version. Do not claim "exact".

**On G6.** The current text calls the post-refinement re-estimation a loss of
"precision"; α actually falls from p = 7e-20 to p = 0.079. Report both
estimations side by side and say plainly which series supports which claim.

**Gate G:** each experiment writes its own provenance block; each reads only
`master.csv` / `master_phases.csv` / `master_refined.csv`.

---

## Stage H — Verification and falsification

| Check | Content |
|---|---|
| H1 | Primal feasibility of all 660 incumbents, re-validated from the instance files |
| H2 | Bound re-derivation for **every** proven-optimal instance — not a subset. The current claim "every one of the 226 was re-derived" covers 131. |
| H3 | Falsification suite: no bound below its own incumbent, below an external BKS (461), or below a BPC-proved optimum (245) |
| H4 | Monotonicity: refinement never loosens |
| H5 | Independence audit: assert no reported number depends on `bks` — grep plus a runtime taint check |
| H6 | Replay determinism: sample 30 instances, re-run under `--replay`, assert bit-exact |

**Gate H:** all clean, with counts printed. Any failure blocks publication of
the affected claim.

---

## Stage I — Analysis and generation

One orchestrator, `make_paper.py`, regenerates **every** table and figure from
`master_refined.csv` and writes them as `.tex` fragments that `main.tex`
`\input`s. No table is hand-typed.

**Gate I:** `checks/check_tables.py` regenerates every fragment and diffs
against what is committed. Any drift fails. This is the gate that would have
caught Tables 4 and 5.

---

## Stage I2 — Claims: derived from results, then challenged by them

**No sentence carrying a number is written before the number exists.** The
existing paper was written, then checked. This inverts that: results first,
claims derived from them, claims attacked, prose written only from what
survives.

### I2.1 — The claims register

Every claim in the paper gets an entry in `paper/claims.yaml`:

```yaml
- id: C-042
  text: "refinement raises the number of instances certified optimal from X to Y"
  generator: make_paper.py::refinement_gain      # the code that produces it
  source: results/master_refined.csv
  series: refined                                # search | refined | both
  population: study-660                          # exactly who it speaks for
  value: {before: X, after: Y}
  falsifier: checks/claims/C042_test.py          # fails if the claim is false
  challenges: [scope, series, stratum, alternative, perturbation]
  status: pending | survived | narrowed | withdrawn
```

**Gate I2a:** every sentence in `main.tex` containing a numeral resolves to a
register entry, and every entry's `value` regenerates from its `generator`. A
number in the prose with no register entry fails the build.

### I2.2 — Derivation

Claims are written **from** the data summary, not ported from the current
manuscript. The current text is treated as a source of *questions*, not of
answers: for each existing claim, ask "does the new data support this?" and
write whatever the data supports, which may be a different sentence, a narrower
one, or none.

### I2.3 — Challenge

Each claim is attacked along five axes. A claim that fails an axis is narrowed
or withdrawn, never softened with a hedge.

| Axis | The question |
|---|---|
| **Scope** | Is the claim universal while the evidence is a sample? Does "every", "always", "no instance" actually hold over the full population, or only the tested subset? |
| **Series** | Does it hold on the search series *and* the refined series? If only one, the sentence must name which — this is exactly how two tables came to report the wrong one. |
| **Stratum** | Is the aggregate effect driven by one family, one $\alpha$, or a handful of instances? Report the stratum breakdown; an effect resting on 1 of 30 instances is not an effect. |
| **Alternative** | Is there a competing explanation the data cannot separate? Mechanisms asserted over associations get demoted to associations. |
| **Perturbation** | Does it survive a different seed set, a different sample draw, or the `--replay` re-run? |

### I2.4 — Adversarial pass

The `manuscript-adversary` agent runs against the **new** artifact set, cold,
with the register as its target list, and is told not to trust
`checks/check_claims.py` — that gate is written by the same process that writes
the claims and can encode the same error.

**Gate I2b:** every register entry is `survived`, `narrowed` or `withdrawn` —
none `pending` — and no withdrawn claim appears in the prose.

---

## Stage J — Documentation and repo

| Item | Content |
|---|---|
| J1 | `reproduce.py` rewritten to orchestrate **this** campaign, stage by stage, with `--list` doubling as the protocol appendix |
| J2 | `README.md`: entry points, expected runtimes, hardware, exact commands |
| J3 | `DATA_PROVENANCE.md`: instance sources with hashes; BKS extraction method and its role (comparison only, never input) |
| J4 | Repo made **public** before submission; the data-availability statement's URL must resolve |
| J5 | Archive prior campaigns under `archive/` with a README stating they are superseded and not used by any reported number |
| J6 | Project notes updated to describe the new single-source layout. Development scaffolding (agent definitions, session notes, `dev_*/`, `archive/`) is excluded from the published export -- see `checks/check_no_attribution.py`. |

**Gate J:** a clean clone, followed by `python reproduce.py --all`, reproduces
every table from scratch on a machine with no prior state.

---

## Caveat → remedy traceability

| Issue found | Stage |
|---|---|
| Incumbents inherited from prior campaigns | A2, R1 |
| Initial bound inherited and BKS-seeded | A1, H5 |
| `--cold-start` incomplete | A1 |
| `F4` hardcoded corrections | A4 |
| Flooring defect | A5, B4 |
| Refinement skip rule blind to too-tight bounds | A7 |
| Refinement wall-clock cap → non-determinism | A6, R3 |
| Tables built from the wrong series | F (naming), I (gate) |
| Operating points froze the dual bound | G1 |
| "Every one of 226 re-derived" was 131 | H2 |
| Ablation effects below design resolution | D6 |
| Duplicate sensitivity run tabulated selectively | D5 |
| Tobit α not significant post-refinement | G6 |
| CPLEX not time-matched | G5 |
| Prefix property asserted "exact" | G1, R3 |
| Ejection chain omitted from replay | A8 |
| Bitmask DP never tested | **B** |
| Seeds not recoverable | A9, D3 |
| BOM breakage | A10 |
| `reproduce.py` orchestrates the wrong paper | J1 |
| Repo private while cited | J4 |
| Samples stratified on prior outcomes | D6 |
| Sizing drawn from a prior campaign | D5 |
| Claims ported rather than re-derived | **I2** |
| Prose written before the numbers exist | I2.2 |
| Overclaims surviving because nobody attacked them | I2.3, I2.4 |
| Problems discovered only after a multi-day run | E-mon |
| Interim results influencing the campaign | E-mon6 |
| Resume silently mixing campaigns | E-mon7 |
| Truncated runs credited the final incumbent's refinement | G1 |

---

## What this does not do

- It does not make the campaign bit-exact reproducible as executed. Wall-clock
  phase budgets preclude that. `--replay` closes the gap for anyone who wants
  determinism; the disclosure is explicit rather than hidden.
- It does not re-derive the BPC baseline. Those figures remain extracted from
  the published paper, and the extraction is documented in J3.
- It does not guarantee the headline survives. The self-seeded measurement
  suggests the bound side is safe (446 either way), but cold incumbents are
  untested at scale. Stage C's pilot is where that surfaces.
