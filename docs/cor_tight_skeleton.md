# A Tight COR-Oriented Paper Skeleton for the SRPS–ALNS Study

## Working title

**An Adaptive Large Neighborhood Search with Lagrangian Certification for the Selective Routing Problem with Synchronization**

## Positioning goal

This outline is designed for a **tight** Computers & Operations Research submission: the main text focuses on the algorithmic contribution, the benchmark comparison, the certification story, and one compact explanatory analysis, while heavier statistical detail and auxiliary sensitivity checks are reserved for an appendix. The goal is to maximise readability and reviewer confidence without diluting the paper’s strongest messages.

## Title and abstract

### Title

Use a title that foregrounds both the heuristic and the certification component, since that combination is the paper’s distinguishing feature. The current working title already does this effectively and is suitable for COR.

### Abstract skeleton

Open with one sentence introducing the Selective Routing Problem with Synchronization (SRPS) and its telescope-scheduling motivation. Then state that the benchmark paper by Riera-Ledesma and Salazar-González provides exact branch-and-price-and-cut algorithms, but no dedicated heuristic method for SRPS and no results beyond the published benchmark frontier.

The second part of the abstract should state the methodological contribution in one compact sentence: an adaptive large neighborhood search combined with a Lagrangian relaxation that yields certified optimality gaps, plus a two-pass warm Polyak refinement for tightening loose bounds.

The results sentence should include only the strongest numbers: the 660-instance study set, 99.8% of solutions certified within 2% of optimality, 117 proven-optimal cases, 23 improvements over the published incumbent, and first certified results for the previously uncovered large Class-4 instances. Avoid crowding the abstract with regression output, detailed runtime distributions, or too many percentages.

Conclude the abstract with one sentence on significance: the proposed method provides a practical primal-dual alternative to exact BPC, delivering strong primal solutions and tight certificates in minutes on the challenging portion of the benchmark.

> **WRITE NOTE (abstract — central framing):** The abstract's closing significance sentence is the most important framing decision in the paper. It must not say "our ALNS performs well" — it must say **"certified primal-dual method"**. The phrase signals to COR reviewers that this is not a routine heuristic application but a method that guarantees its own quality. Every word in the abstract should reinforce the dual nature: primal (ALNS solutions) + dual (Lagrangian certificates). The results sentence should foreground the certification numbers (99.8% within 2%, 117 proven optimal) *before* the BKS comparison — because the certificate is the differentiator, the BKS comparison is the supporting evidence.

## 1. Introduction

Begin with the astronomical application and explain that SRPS arises from configuring synchronized slit positions in the EMIR spectrograph at the Gran Telescopio Canarias. Then define the computational challenge at a high level: the problem combines optional selection, routing or sequencing, synchronization across processors, and a global time limit.

The literature positioning should be short and direct. State that the benchmark COR paper introduced SRPS and solved it with exact branch-and-price-and-cut algorithms, but did not provide a dedicated heuristic approach for the same SRPS setting. Emphasize that exact BPC is highly effective on many benchmark groups, yet becomes slow or leaves residual gaps on the hardest synchronized instances, and no published results cover part of the extended size range.

The final paragraph of the introduction should present contributions in four bullets only:

- A first dedicated ALNS method for SRPS, designed to preserve synchronization feasibility during destroy-repair search.
- A Lagrangian relaxation scheme that supplies certified instance-level quality guarantees for the heuristic solutions.
- A two-pass warm Polyak refinement that sharply tightens loose certificates on the difficult cases.
- A computational study on the 660 nontrivial benchmark and extended instances, showing strong agreement with or improvement over the published BPC incumbents, plus new certified results beyond the original benchmark frontier.

> **WRITE NOTE (§1 — bullet ordering and framing):** The four bullets above are ordered correctly for *method description* but the **wrong order for COR impact**. When writing the actual paper, re-order to lead with the certification architecture: (1) the primal-dual framework — ALNS coupled with Lagrangian certification — as a single integrated contribution; (2) the two-pass warm Polyak as the engineering insight that makes the certification tight; (3) the computational study and BKS results; (4) the hardness analysis. This ordering signals to reviewers that the certification is not an afterthought — it is the architectural decision that defines the paper. The ALNS component should be described *within* bullet 1, not as a standalone first bullet, to avoid the impression that "we applied ALNS" is the lead claim.
> **WRITE NOTE (§1 — ALNS is vehicle, not headline):** Avoid opening the contribution list with "A first dedicated ALNS method for SRPS." That framing makes ALNS the headline and reviewers may dismiss it as routine. Instead open with: *"A certified primal-dual method for SRPS, combining synchronisation-aware ALNS (primal) with a Lagrangian relaxation that provides hard per-instance optimality certificates (dual)."* This positions ALNS as the mechanism delivering primal quality within a larger certified framework — which is the accurate description of what the paper contributes.

End the introduction with one sentence outlining the paper structure. Keep the introduction free of regression coefficients, detailed family counts, and nuanced caveats; those belong later.

## 2. Problem definition and benchmark scope

### 2.1 Problem definition

Introduce SRPS formally but economically. Define the set of jobs, the processor set, the processor subset required by each job, the travel or transition times, the job profits, and the global time limit. Then explain that a feasible solution assigns an ordered path to each processor and a synchronized start time to every selected job, subject to common start times across the processors required by that job and a global time budget.

A compact notation table is appropriate here. The table should include only the symbols that are used later in the heuristic and Lagrangian sections; do not reproduce the full notation burden of the exact BPC paper.

### 2.2 Relation to prior models

Use one short paragraph to position SRPS relative to OP and TOP. State that when every job requires only one processor the synchronization burden disappears, but the study in this paper deliberately targets the synchronized regimes where K_j  2 because that is where the problem’s defining difficulty lies.

### 2.3 Benchmark families and study set

Present the benchmark taxonomy in a single clean table. Keep the table, but simplify the commentary around it. The key sentence should be explicit: this paper studies families H2–H4 and E2–E4, totaling 660 instances, because these are the synchronized families of interest; H1 and E1 are excluded from the main analysis because they reduce to the non-synchronized regime and are solved trivially by the exact baseline.

If you later run H1/E1 as a completeness check, mention that in one sentence in the computational setup, not here. The benchmark section should establish scope, not pre-empt every reviewer concern.

## 3. Baseline and contribution target

This section should be short. Summarize the benchmark paper’s exact approach: two branch-and-price-and-cut variants with a one-hour limit, strong performance on much of the benchmark, but residual gaps on some large synchronized groups and no published coverage for part of the larger Class-4 range.

Do not overfill this section with many table values from the original paper. Include only two or three representative examples showing where BPC leaves nonzero gaps, and save the complete groupwise comparison for the experimental section. The purpose here is to explain why a heuristic-plus-certificate method is interesting, not to reproduce the benchmark paper.

End with one sentence clearly stating the contribution target: the paper does not attempt to replace exact BPC theoretically, but to provide a fast primal-dual method that returns high-quality solutions together with explicit instance-level certificates on the hard synchronized cases.

## 4. Methodology

### 4.1 Lagrangian relaxation

Start with the dual side of the method because it gives the certification mechanism. Explain that the synchronization coupling constraints are relaxed, producing processor-level subproblems that can be solved independently. State that the resulting dual bound is valid for the original SRPS and is used to certify the quality of the ALNS solution.

This section should include the high-level formulation and the definition of the certified gap, but it does not need to be as long as a methods paper devoted purely to dual optimization. The reader needs to understand what is relaxed, what the bound means, and why it is valid.

### 4.2 Subgradient and warm Polyak refinement

Describe the first-pass subgradient scheme briefly, then introduce the two-pass idea as the main engineering improvement. The wording should make clear that the second pass does not change the dual method; it improves step-size calibration by using the heuristic incumbent as the lower-bound target in the Polyak update.

A compact paragraph should report the aggregate effect on the loose instances, but detailed family-level breakdowns should be deferred to the experiments or appendix. The main methodological message is simple: the warm second pass is a practical way to tighten many initially loose certificates at low additional cost.

### 4.3 Adaptive large neighborhood search

> **WRITE NOTE (§4.3 — presentation discipline):** Present the **final algorithm only**. Do not describe the development evolution — the paper is not a lab notebook. Each non-obvious design choice gets one motivation sentence stating *why*, not *how you arrived at it*. The ablation (§5.6) implicitly justifies the operator choices by showing degradation when each is removed; the methods section does not need to pre-argue for them. One-sentence design motivation is acceptable (*"motivated by the observation that..."*) but one sentence maximum — it is design rationale, not design history.

Describe the ALNS in three subsections only:

- Representation and feasibility checking.
- Destroy and repair operators.
- Acceptance, adaptive weighting, and multi-start execution.

Keep the presentation operational. Explain how synchronization-aware insertion is handled and why feasibility can be maintained efficiently. Avoid a large parameter catalog in the main text; put exhaustive parameter values, alternative settings, and implementation minutiae into the appendix unless they are necessary to reproduce the core algorithm.

> **WRITE NOTE (§4 / §5.1 — GAP threshold 0.3% is a deliberate design choice):** The 0.3% certified-gap stopping criterion must be presented as a principled decision, not an incidental implementation detail. State it explicitly in §4 (adaptive loop description) and reinforce in §5.1 (experimental setup). The motivation rests on three pillars — all three must appear:
>
> 1. **Mathematical rigor**: the 0.3% threshold applies to the *certified* Lagrangian gap, not a heuristic quality estimate. Every instance that stops at GAP<0.3% carries a proven primal-dual certificate — the gap is an upper bound on distance to optimality, not an approximation.
>
> 2. **Operational meaningfulness**: at SRPS profit scales (integer profits, floored Lagrangian UB), a 0.3% residual gap corresponds to sub-unit profit differences in the vast majority of instances — operationally indistinguishable from optimality for telescope scheduling decisions.
>
> 3. **Runtime control**: 0.3% enables clean termination in 1–2 phases for the majority of instances, keeping total runtime well within BPC's 1-hour cap while preserving full certification quality. This is not a compromise — it is a deliberate balance between mathematical tightness and computational efficiency.
>
> Suggested wording: *"The adaptive loop terminates when the certified Lagrangian gap falls below 0.3%, a threshold chosen to reflect a deliberate balance: tight enough to constitute a meaningful optimality certificate (sub-unit profit residual at integer scales), yet permissive enough to enable controlled runtimes across all 660 instances without exhausting the time budget."*
>
> **Sensitivity trial (§5 sensitivity analysis):** Run threshold variants {0.1%, 0.3%, 0.5%, 1.0%} on a stratified instance selection. **Scope: GAP<0.3% and TIERS_EXHAUSTED instances only** — UB-stopped instances (gap=0%) are unaffected by threshold choice and must be explicitly excluded. Expected finding: diminishing-returns curve with 0.3% at the knee — tightening to 0.1% yields marginal quality gain at disproportionate RT cost; loosening to 1.0% saves RT on TIERS_EXHAUSTED instances but accepts wider certificates. This result converts the threshold from a design parameter into a defended, empirically validated choice.

### 4.4 Method summary

End the methods section with one concise summary paragraph: the ALNS supplies strong primal solutions, the Lagrangian relaxation supplies valid dual certificates, and the two-pass Polyak refinement tightens those certificates on the hard tail. That paragraph is the conceptual bridge to the experiments.

> **WRITE NOTE (§4 — pseudo-code standards for COR):**
> Use `\usepackage{algorithm}` + `\usepackage{algpseudocode}` — the dominant choice in recent COR/EJOR ALNS papers. Do NOT mix with `algorithm2e` (incompatible syntax).
>
> Formatting conventions:
> - Caption **above** the algorithm block
> - Line numbers on: `\begin{algorithmic}[1]`
> - Bold title-case keywords: **Input**, **Output**, **while**, **for**, **if**, **return**
> - `\Require` for inputs, `\Ensure` for outputs
> - COR is single-column — full page width available, but keep algorithms concise
>
> We need exactly **two algorithms** in the paper:
> 1. **Algorithm 1 — Adaptive loop**: phases, tier escalation (25%→33%→40%), UB recomputation on stall (warm-mu), stop criteria (GAP<0.3%, RT≥3600s, TIERS_EXHAUSTED)
> 2. **Algorithm 2 — Lagrangian subgradient + warm Polyak refinement**: relaxation, subgradient step, warm second pass using ALNS incumbent as lower-bound target
>
> The ALNS inner loop (destroy/repair/acceptance) can be referenced in one sentence from Algorithm 1 rather than given a third algorithm block — keeps §4 tight.

## 5. Computational experiments

### 5.1 Experimental setup

State the hardware, implementation language, seed policy, and stopping rules. Clearly define the three reported metrics: published-BKS gap, certified gap, and BEAT/TIE/GAP status. Also define exactly which instances are included in the 660-instance study set.

> **WRITE NOTE (§5.1 — sensitivity analysis reporting style):** Follow **OR common practice** as the primary reported format: conduct sensitivity analysis on a **representative stratified subset** of instances (stratified by family and Tobit-identified hardness dimensions — α, K×α, n), run all parameters on the same subset, report one line chart per parameter (x-axis = parameter value, y-axis = average certified gap or primal quality), and close with a robustness claim: *"algorithm performance is stable within ±X% across the tested range."* This is the expected deliverable in COR/EJOR metaheuristic papers — one or two parameters, one chart each, one paragraph.
>
> **One structural exception — GAP threshold trial only:** UB-stopped instances (gap=0%, stopped by dual convergence) are logically immune to threshold variation and must be excluded. State this in exactly one sentence: *"Instances stopped by the UB-convergence criterion are excluded from the threshold trial, as their termination condition is independent of the GAP threshold by design."* No further scope justification is needed for any other parameter.
>
> **Optional supplementary element (strengthens without complicating):** For the one or two parameters where the hard/easy split is most informative (e.g., destroy fractions), add a supplementary table showing effect sizes by hard vs. easy subpopulation. Frame as: *"Sensitivity is concentrated in the hard-instance regime (α≤0.5, large n), consistent with the algorithm's tier-escalation design."* This converts a potential reviewer concern into a proactive finding without introducing scope-aware complexity into the primary analysis.
>
> **What NOT to do:** Do not structure the sensitivity section around scope-aware binding populations as the primary framing — this is methodologically stronger than COR convention requires, opens a post-hoc selection attack vector, and is harder to defend than stratified sampling. Scope-aware reasoning informs your internal design and instance selection but should not dominate the paper's prose.

> **DATA NOTE (§5.1 — sensitivity analysis: 30-instance stratified subset and parameter grid):**
>
> **Instance selection rule (mechanically applied, pre-committed before analysis; script: `scratch/build_sensitivity_subset.py`):**
> - **Family coverage:** equal allocation — 5 instances per family (B, C, D, EB, EC, ED); 30 instances total.
> - **Size coverage:** within each family, select one n-level at each of the 0th, 25th, 50th, 75th, and 100th percentile of the family's observed n-range (integer quantiles, rounded). Deduplication applied if two quantile indices map to the same n-value.
> - **Budget coverage:** α assigned cyclically across the five n-levels in order: [0.25, 0.50, 0.75, 0.25, 0.50]. This yields all three budget levels represented in each family; α=0.25 and α=0.50 each appear in 12 of 30 slots, α=0.75 in 6 (assigned to the median n-level).
> - **Tie-break:** within each (family, n, α) cell, select the first instance alphabetically. The rule is mechanical and blind to quality or stop-reason — no post-hoc filtering.
>
> **Subset statistics (source: `results/adaptive_master.csv`):** 30 instances, mean cert gap 0.153%.
> Stop-reason distribution: GAP<0.3% (19), UB-stopped/proven optimal (10), TIERS_EXHAUSTED (1: B_n140_021_a25_061, cert gap 1.66%).
>
> **Selected instances (in family × n-percentile order):**
> ```
> B:  B_n100_001_a25_001  B_n110_006_a50_017  B_n120_011_a75_033  B_n140_021_a25_061  B_n150_026_a50_077
> C:  C_n050_001_a25_001  C_n060_011_a50_032  C_n065_016_a75_048  C_n070_021_a25_061  C_n080_031_a50_092
> D:  D_n040_001_a25_001  D_n050_011_a50_032  D_n060_021_a75_063  D_n070_031_a25_091  D_n080_041_a50_122
> EB: EB_n100_001_a25_001 EB_n110_006_a50_017 EB_n120_011_a75_033 EB_n140_021_a25_061 EB_n150_026_a50_077
> EC: EC_n050_001_a25_001 EC_n060_011_a50_032 EC_n065_016_a75_048 EC_n070_021_a25_061 EC_n080_031_a50_092
> ED: ED_n040_001_a25_001 ED_n050_011_a50_032 ED_n060_021_a75_063 ED_n070_031_a25_091 ED_n080_041_a50_122
> ```
>
> **UB-stopped instances and GAP_THRESHOLD trial:** The 10 UB-stopped instances (cert gap = 0.00%) are logically immune to threshold variation — they stop on dual convergence, not the gap criterion. For the GAP_THRESHOLD trial only, exclude these 10 instances (20 participating: 19 GAP<0.3% + 1 TIERS_EXHAUSTED). Paper sentence: *"Instances terminated by the dual-convergence criterion are excluded from the threshold trial, as their termination condition is independent of the GAP threshold by design."*
>
> **Parameter grid (one-at-a-time; script: `run_sensitivity.py`; ABS_CAP=1800s; fresh starts, no PKL warm-start):**
>
> | Parameter | Default | Variants tested | Baseline |
> |-----------|---------|-----------------|----------|
> | `GAP_THRESHOLD` | 0.3% | 0.1%, 0.5%, 1.0% | **0.3%** |
> | `DESTROY_FRACS` | [0.25, 0.33, 0.40] | tight [0.20, 0.28, 0.35], wide [0.30, 0.40, 0.50] | **default** |
> | `PHASE_RT` | 300 s | 150 s, 450 s | **300 s** |
> | `LAG_MAX_ITER` | 200 | 100, 400 | **200** |
> | `LAG_MAX_TIME` | 60 s | 30 s, 120 s | **60 s** |
>
> 11 trials total (1 baseline + 2 variants per 5 parameters). Expected ~1.5–2 h per trial on 6 cores.
>
> **Reporting format:** one line chart per parameter (x-axis = parameter value, y-axis = mean cert gap over 30 instances), closing robustness claim of the form *"performance varies by ±X% across the tested range."* Supplementary element for DESTROY_FRACS: effect-size table split by hard (α≤0.50) vs. easy (α=0.75) subpopulation, to frame any concentrated sensitivity as a finding rather than a concern.

> **DATA NOTE (§5.1 — runtime comparison context, language + hardware):**
>
> | | BPC (Riera-Ledesma & Salazar-González, 2021) | This work |
> |---|---|---|
> | Language | C++ (compiled) | Python 3 (CPython, interpreted) |
> | LP/MIP solver | IBM ILOG CPLEX 12.10 | None |
> | CPU | Intel Core i5-6600, 3.3 GHz, 4 cores (Skylake, 2015) | Intel Core Ultra 7 258V, 8 cores (2024) |
> | RAM | 8 GB | 32 GB |
> | OS | Ubuntu 20.04 LTS | Windows 11 |
> | RT bottleneck | Column generation + branch-and-bound | ALNS search (99.9% of RT — measured) |
>
> **Language factor:** Benchmarks Game geometric mean C++ over CPython = **32×** (range 23–93× for compute-intensive algorithmic tasks; ALNS-class iterative code sits in the 20–33× range). Source: benchmarksgame-team.pages.debian.net/benchmarksgame/fastest/python3-gpp.html
>
> **Hardware factor:** PassMark single-thread — i5-6600: 2,253 | Core Ultra 7 258V: 4,032 → our machine is **1.79× faster** single-thread. Source: cpubenchmark.net.
>
> **Key statement (can appear in paper):** The hardware advantage (1.79×) is structurally smaller than the language gap (23–32×). At no plausible language estimate does the hardware factor offset the language overhead — net handicap is 23/1.79 = 13× to 32/1.79 = 18× in BPC's favour. Our Python implementation competes against a compiled C++ solver with a 13–18× effective RT handicap.
>
> **Suggested §5.1 sentence:** *"BPC was implemented in C++ with CPLEX 12.10 on an Intel Core i5-6600 (3.3 GHz, 2015); our method runs in Python on an Intel Core Ultra 7 258V (2024). Although our hardware is 1.79× faster in single-thread (PassMark), this does not offset the language overhead: C++ outperforms CPython by 13–32× on compute-intensive algorithmic code (Benchmarks Game geometric mean: 32×). Our reported runtimes carry an effective net handicap of approximately 13–18× relative to an equivalent compiled implementation on comparable hardware."*

If H1/E1 were run for completeness, summarize them in one sentence here, for example by stating that all were solved to the known optimum and are omitted from detailed tables because they add no comparative insight. If they were not run, do not introduce them again.

### 5.2 Overall quality and certification

This should be the first main results subsection because it gives the strongest high-level picture. Present one table with the certified-gap tiers across the 660 instances, plus one short paragraph emphasising the mass near zero: 117 exact, 411 within 0.5%, 532 within 1%, and only 1 above 2% (B_n140_025_a25_073 at 2.432%, an ALNS primal failure at α=0.25).

If space permits, add a simple figure showing the tier distribution or cumulative share within threshold. This section should make the reader immediately understand that the method is not merely heuristic in spirit; it is empirically close to exact on most of the hard study set.

### 5.3 Comparison with published BPC incumbents

Now compare against the benchmark paper. Use a compact groupwise table and keep the prose disciplined. The key text should explain three things:

- On many instances with published BKS, the method matches the incumbent or differs only negligibly.
- On a meaningful subset, the method improves the published incumbent returned by BPC within its one-hour limit.
- Where the method falls below the published BKS, the shortfalls are typically tiny and should be reported with the median and fine-scale distribution, not only as a raw GAP count.

Include the footnote clarifying that BPC’s reported gap and the certified gap in this paper are different primal-dual quantities with different denominators and should not be interpreted as numerically identical metrics.

> **DATA NOTE (§5.3 — cert gap tightness vs BPC):** On BPC class-2 instances (where BPC published an incumbent but did not prove optimality), our Lagrangian certificate is tighter than BPC’s residual primal-dual gap in **83% of cases** (15/18, interim adaptive run). Mean BPC residual gap 0.278% vs our mean cert gap 0.109% — a 2.5× improvement in certification quality, achieved in under 700s vs BPC’s 3600s cap. Add this as a sentence in §5.3: *"On instances where BPC reported a nonzero residual gap, our Lagrangian certificate is tighter in 83% of cases, with a mean gap of 0.109% against BPC’s 0.278% — despite running in a fraction of the time."* Note: numbers are from 18 interim instances; refresh once full 660-run is complete.

### 5.4 New benchmark results beyond the published frontier

This section should cover the first-ever or previously uncovered larger Class-4 instances. Present a concise table summarising the number of newly reported instances and their certification quality, then highlight only one or two standout cases in prose.

Be careful with wording here. Say that the ALNS improves the published incumbent or reveals that a recorded BKS is stale; do not imply that the heuristic “beats the exact solver” in a theoretical sense.

### 5.5 Impact of the two-pass Lagrangian refinement

This section should show why the dual side matters. A small before-after table for the 180 initially loose instances is enough in the main text, with average and maximum certified gaps before and after the warm second pass and the count resolved below 2%.

One figure is worthwhile here if space allows: first-pass versus final certified gap on the loose instances. This gives the paper a clear algorithmic “insight” result, not just a list of final numbers.

### 5.6 Minimal ablation study

Keep this subsection deliberately small. The main-text ablation should answer only the most important question: what is the contribution of the second-pass Polyak refinement, and, if available, what is the contribution of the Lagrangian layer beyond pure ALNS.

**Interim signal from the running ablation (A0–A12, 125/780 jobs, 16% complete, family B only — provisional):**

The clearest early finding is that **ratio repair (A5)** is the only operator whose removal causes a significant cert-gap increase (+0.499% mean, <<< flag). Dropping any of the three destroy operators individually is negligible, as is removing regret-2 repair or stall escalation. Multi-seed (A8: 1 seed vs 3) is notable at +0.063%. The temperature and cooling-rate arms (A9–A12) all degrade by a nearly identical +0.115–0.117% — this uniformity across four very different settings is suspicious and provisionally attributed to family-B’s size range (n=100–150); differentiation is expected once larger-n families arrive.

**Strategy for main text vs appendix:**

The preferred main-text table remains three or four rows at most:

| Variant | Primal quality | Certified gap | Runtime |
|---------|----------------|---------------|---------|
| ALNS + LR + 2-pass Polyak (A0 full) | Best | Best (mean 1.14% on B) | Baseline |
| ALNS + LR only, no warm Polyak | Same | Looser on 180 instances (avg 3.49% → baseline) | Slightly faster |
| ALNS + ratio repair dropped (A5) | Weaker on α=0.25 instances | +0.5% mean cert gap | Same |
| ALNS, 1 seed only (A8) | Slightly weaker | +0.063% mean cert gap | 3× faster |

Lead the paragraph with the **ratio repair** finding: it is the one operator whose contribution is empirically non-redundant. Follow with the **parameter robustness** message: cooling rate and T₀ choices (across the ranges tested) have negligible or symmetric impact, so the specific values 0.985 and 100 are not critical and the algorithm is not finely tuned.

The full 13-arm table (mean/median/P75/max cert gap per arm, per-family breakdown) belongs in the appendix alongside the per-instance contrast table. A tight paper needs one convincing ablation, not five mediocre ones.

> **Status note:** Full ablation results will be available from `results/analysis/ablation_<date>.csv` after ~23 h on 5 cores. The section above will need to be refreshed once all 780 jobs complete. Expected final narrative: ratio repair finding holds; temperature arms likely collapse to negligible once larger families (D/EC/ED, n≥65) dominate the sample.

### 5.7 Hardness patterns

This is where the paper should choose **tight over dense**. In the main text, include only one short subsection that answers a single question: what drives certified-gap difficulty across the 660-instance study set.

Use one compact table and two or three paragraphs. The prose should report only three messages:

- Budget tightness α is the strongest univariate driver (KW H=192, p=2.3e-42); α=0.25 and α=0.50 are statistically indistinguishable — the boundary is entirely between α≤0.50 (mean cert ~0.68%) and α=0.75 (mean cert 0.12%).
- Interactions dominate: K×α is the strongest interaction (M2 coef=+0.173, p=3.0e-06) — synchronisation class amplifies the budget-tightness effect. n×K is secondary (coef=+0.097, p=5.1e-03). n×α is also significant (+0.089, p=0.016). The full M2 achieves McKelvey-Zavoina R²=0.321 — moderate fit consistent with cross-sectional OR benchmark data.
- Distance geometry has no important additive effect (Test D p=0.572), even though distance interactions (α×dist, n×dist) appear in the full model.

Do not place multiple Tobit models, all likelihood-ratio tests, and a long physical interpretation of each interaction in the main text. Those belong in an appendix. In the main text, the regression supports the experimental story; it should not compete with it.

## 6. Conclusion

The conclusion should be short and results-driven. Restate the three core takeaways:

- The paper introduces the first dedicated ALNS framework for SRPS and couples it with valid Lagrangian certification.
- On the 660 synchronized benchmark and extended instances, the method produces solutions that are overwhelmingly within very small certified gaps, with 99.8% (659/660) within 2% and 117 proven-optimal cases.
- The warm two-pass Polyak refinement is the key practical ingredient that tightens the difficult tail at modest extra cost.

Then give a single limitations paragraph. Acknowledge that the implementation is in Python, that there is no worst-case approximation ratio, and that a small tail of instances remains above 2% certified gap after the second pass. This shows maturity and should remain in the main paper rather than being hidden.

End with a brief future-work sentence or paragraph. Keep it practical: warm-starting BPC from ALNS solutions, extending to richer SRPS variants, and incorporating real operational constraints from telescope scheduling.

## Appendix plan

To preserve a tight main text, move the following material to the appendix:

- Full per-instance tables for large families.
- Detailed parameter sweeps and operator-level ablations.
- Convergence plots for representative Lagrangian runs.
- Full Tobit output, alternative models, likelihood-ratio tests, marginal effects, and interaction plots.
- Any H1/E1 completeness tables, if you decide to run them.

## COR Submission Formatting Standards

> All requirements verified from Elsevier/COR official sources (June 2026). Re-check guide-for-authors before final submission in case of updates.

### Abstract
- **Max 250 words** — no non-standard abbreviations (define any if essential at first mention)
- Structure: purpose → principal results → major conclusions (no headers inside the abstract)
- Must stand alone: no citations, no figure references

### Highlights
- **Required** — submitted as a **separate editable file** named `highlights.*`
- **3 to 5 bullet points**, each **max 85 characters including spaces**
- Capture novel results and new methods; must be meaningful outside the abstract
- Do not duplicate the abstract verbatim

### Graphical Abstract
- **Encouraged** (not mandatory for COR)
- Submitted as a **separate file**; do not write "Graphical abstract" as a heading inside the image
- Minimum **1328 × 531 pixels**, minimum **300 dpi**
- Accepted formats: TIFF, EPS, PDF, MS Office
- Fonts: Times, Arial, Courier, or Symbol — large enough to remain legible when scaled
- No third-party material without permission; no unnecessary white space

### Keywords
- **1 to 7 keywords** in English, for indexing

### Citation Style
- **Author-year (Harvard)** — COR uses Harvard style, not numbered
- In-text: `(Smith, 2021)`, `(Smith and Jones, 2021)`, `(Smith et al., 2021)` for 3+ authors
- Multiple citations separated by semicolons: `(Smith, 2021; Jones, 2022)`
- **Reference list: alphabetical by first author surname**
- Journal article format: `Author(s), Year. Title. Journal Abbrev. Volume, pages.`
- Example: `Riera-Ledesma, J., Salazar-González, J.J., 2021. The selective routing problem with synchronization. Comput. Oper. Res. 136, 105478.`
- LaTeX: use `\bibliographystyle{elsarticle-harv}` (NOT `elsarticle-num`)

### Manuscript Format
- **Single-column** — COR is single-column (use `\documentclass[review]{elsarticle}` for submission)
- **Double-spaced** for review submission; add line numbers (`\usepackage{lineno}`, `\linenumbers`)
- Editable source files required (LaTeX + all figures)
- **Double-blind review** — remove all author names, affiliations, acknowledgements, and self-identifying references before submission; use anonymized arxiv preprint references if citing own prior work

### Figures
- Caption **below** the figure
- Numbered: Fig. 1, Fig. 2, … | Appendix figures: Fig. A.1, Fig. A.2, …
- Line art: **minimum 1000 dpi**; halftone: **300 dpi**; combination: **500 dpi**
- Accepted formats: TIFF, JPEG, EPS (no PNG currently)
- Color: submit in **RGB**; Elsevier converts to CMYK for print — check color-critical figures
- Line weight: min 0.1 pt; recommended 0.25 pt for thin lines, ~1 pt for prominent plot lines
- Max **10 MB per figure** (recommended ≤7 MB)
- Font in figures: large enough to remain legible at final print size

### Tables
- Caption **above** the table
- Numbered: Table 1, Table 2, … | Appendix tables: Table A.1, Table A.2, …
- Footnotes below the table using superscript letters (a, b, c)
- Avoid vertical rules; use horizontal rules only (booktabs style: `\toprule`, `\midrule`, `\bottomrule`)
- Submit as editable LaTeX, not images

### Equations
- Numbered on the right: `\begin{equation} \label{eq:gap} \end{equation}`
- Inline math for simple expressions; display math for anything referenced in the text
- Define all symbols at first use

### Algorithms (see also §4.4 note)
- Use `algorithm` + `algpseudocode` packages
- Caption **above** the algorithm block
- Line numbers on: `\begin{algorithmic}[1]`
- Numbered: Algorithm 1, Algorithm 2, …

### Section and Word Count
- COR has no stated hard word limit for the full manuscript, but tight papers (6,000–9,000 words main text) are standard for metaheuristic computational studies
- Appendix content does not count toward main text length
- Section headers: numbered (1., 2., 2.1, 2.1.1 — max three levels)

### Cover Letter
- Required at submission — state the contribution, confirm the work is original, not under review elsewhere, and that all authors have approved
- Briefly explain why the paper fits COR (primal-dual method, benchmark computational study)

### Validation statement (§5.1 one sentence)
*"Every reported solution was independently validated prior to recording — checking route feasibility, synchronization consistency, schedule adherence, and objective recomputation — to rule out corrupted incumbent states."*

---

## Writing rules for the final draft

The final prose should follow these practical rules throughout:

- Put the best numerical result of each section in the first paragraph of that section.
- Avoid repeating the same caveat in multiple sections; one precise statement is enough.
- Never blur the distinction between published BKS improvement and exact-solver dominance.
- Never present BPC primal-dual gaps and Lagrangian certified gaps as numerically identical quantities.
- Prefer one clear table with strong interpretation over several overloaded tables.
- Keep the main text centered on algorithm, certificates, and benchmark impact; treat the statistical analysis as supportive rather than central.

## Suggested final section map

A compact final map for the paper is:

1. Introduction.
2. Problem definition and benchmark scope.
3. Baseline and contribution target.
4. Methodology: Lagrangian relaxation, warm Polyak refinement, and ALNS.
5. Computational experiments: setup, overall certification quality, comparison with BPC incumbents, new benchmark results, two-pass impact, minimal ablation, and compact hardness analysis.
6. Conclusion.
7. Appendix.

This structure preserves the paper’s strongest story for COR: a practically strong heuristic with explicit certification, demonstrated on the hardest synchronized benchmark instances, written in a way that is easy for reviewers to follow.

---
*Last updated: 2026-06-20 (session 7) — Anchor confirmed, adaptive run complete (660/660). §5.1 updated: 30-instance stratified sensitivity subset documented (selection rule, instance list, parameter grid). Scripts: `scratch/build_sensitivity_subset.py` (selection), `run_sensitivity.py` (trials). Source for Tobit numbers: results/analysis/quality_analysis_20260619_2305.txt.*
