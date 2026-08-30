# COR Revision Roadmap — addressing the reviewer-style assessment

*Created 2026-06-22. Turns the virtual-assistant first-reaction review of `paper_skeleton.md`
into a prioritized, trackable execution plan toward a COR-ready draft.*

**Overall verdict from the review:** the skeleton is unusually mature; the main risks are
**framing, over-density, and a few missing "glue" pieces** — not core technical content.

Legend — Priority: **P0** (blocks a credible draft) · **P1** (needed for submission quality) ·
**P2** (polish). Status: ☐ todo · ◐ partial · ✓ done.

---

## STATUS UPDATE — 2026-06-22: full LaTeX manuscript drafted

The skeleton has been converted into a **complete elsarticle manuscript** in `paper/`
(`main_standalone.tex` single-file + `main.tex`/`refs.bib`/`figures/` modular, now in sync). Done
since this roadmap was written: abstract (B1), formal model (B3), Algorithm 1 (B4), tables filled,
both figures generated (`build_figures.py`), appendices A/B populated, framing/tone sweep (A1–A4),
density pass (C2–C4), float placement fixed (`placeins`), references moved before appendices,
ORCID added, and the dual reframed **BKS-free** (θ*=incumbent; B10 + the BKS-input correction).

**The single most important remaining content task is the literature review and references**
(Step 8 below): the manuscript has only **7 references** and thin §2.2/§3.2 reviews. This is now
the top priority before co-author review and submission. See `memory/project_roadmap.md` →
"Next actions #1" for the coverage list and the requirement to update *both* `refs.bib` and the
inline `thebibliography` in `main_standalone.tex`.

Remaining after lit review: Algorithm 2 (B5, optional), co-author review, submission mechanics
(cover letter, data/code-availability statement, hardware-line confirmation).

---

## A. Framing & tone (P0 — the highest-leverage fixes)

| ID | Action | Target | Pri | Status |
|----|--------|--------|-----|--------|
| A1 | Enforce the **"complete primal–dual method"** narrative everywhere; every mention of ALNS performance must anchor to the certificate / UB-refresh, never to "beating BPC" or "nice heuristic". Sweep for slippage ("our ALNS improves on…", "the heuristic is not just fast"). | global | P0 | ✓ (OBS 9 reframed; "heuristic is not just fast" removed; performance anchored to certificate) |
| A2 | **Soften BPC comparison tone.** Lead with "agreement + certification at far lower time"; move the "stale BKS" narrative to a short subsection/appendix with conservative wording. Avoid anthropomorphising the exact solver. | §6.2, §6.3 | P0 | ✓ (2026-06-23: paper repositioned **complementary, not competing** — prose speed/"beat" language softened, "beat" status tag → "improved", per-subgroup speed ratios kept in the table but removed from prose; stale-BKS narrative now sits in §6.3 *New certified results on open instances*; non-comparability reminder retained in §6.2) |
| A3 | **Discipline the conceptual caveats in final prose:** (i) "cert_gap=0%" → "proven optimal" only when UB_lag is known tight, else "meets the Lagrangian UB, consistent with optimality"; (ii) "complete primal–dual method" never drifts to "exact"/"optimal"; (iii) "beats BPC" → "improves on the published incumbent / finds a better feasible solution". | global | P0 | ✓ (ii)(iii) done. **(i) DECLINED** — a feasible solution equal to a *valid* Lagrangian UB is provably optimal (weak duality: obj≤OPT≤UB_lag=obj); "proven optimal" for the cert=0 instances is correct, not an overclaim. **UPDATE 2026-06-23:** the validity guard found one instance (`ED_n045_008_a75_024`) whose *reported* UB was below the BPC-proven optimum (an invalid bound, wrongly counted as proven optimal); corrected to 0.068\%, so **283 not 284 (42.9\%)**. The principle stands; the guard now enforces it in `build_paper_stats.py`/`build_figures.py`/`build_bpc_subgroups.py` |
| A4 | **Primal vs dual metric separation:** any table with both must header them "BPC primal–dual gap" vs "Our Lagrangian certificate"; add a one-sentence non-comparability reminder immediately before each such table. | §6.2 | P0 | ✓ (headers renamed in both §6.2 tables; non-comparability reminder added before the table) |
| A5 | **Python-as-limitation placement:** mention environment once in §6.1 (done) + one brief "engineering, not algorithmic" note in §7. Do **not** over-emphasise (invites a C++ rewrite demand). | §6.1, §7 | P1 | ✓ (2026-06-23: anchored cross-method runtime-comparability paragraph added to §6.1 — BPC i5-6600/CPLEX 12.10 \[verified p8 of their PDF\] vs our 258V; HW ~1.8× favours us but the interpreted-Python/no-commercial-solver penalty is >1 order of magnitude, so **net not in our favour, times conservative**; §7 one-liner retained. Our own C++ DP accelerator was purged so the handicap framing is clean) |

---

## B. Missing structural pieces (P0/P1 — required content that doesn't exist yet)

| ID | Action | Target | Pri | Status |
|----|--------|--------|-----|--------|
| B1 | **Abstract** — focused, primal–dual-led, scale (660 / 6 families / K=2–4), 2–3 headline stats (100% within 2%, 43% optimal, runtime vs BPC 1h), hardness as a single clause. | top | P0 | ✓ inserted (user draft, numbers verified vs `build_paper_stats.py`; relaxation phrase corrected to "joint-service coupling") |
| B2 | **Intro closing paragraph** — journal-style prose "problem + contribution + structure" (currently only bullets/notes). | §1 | P0 | ☐ |
| B3 | **Formal SRPS model** — compact math formulation (variables, constraints, objective; difference-constraint or arc-flow form) + one sentence relating it to BPC's arc-flow SRPS-1. §2.1 currently only verbal feasibility. | §2.1 | P0 | ☐ |
| B4 | **Algorithm 1** — pseudocode for the full primal–dual solver (inputs; outer adaptive loop + stop conditions; calls to ALNS, Lagrangian re-bound, tier escalation, certification). Consolidates §4.3/§4.4/§5.6. | §5.6 | P0 | ✓ inserted (user draft, verified vs `run_sensitivity.py`; fixed: added tier reset, per-phase granularity, μ symbol) + black-box descriptions |
| B5 | **Algorithm 2** — synchronisation-aware insertion (3^K enumeration + feasibility oracle). | §5.3 / App | P1 | ✓ (2026-06-23: `alg:insert` added at the END of §5 so the solver stays Algorithm 1 and insertion is Algorithm 2; described + forward-`\ref`'d from §5.3; top-$c$ detour candidates × Cartesian product × longest-path check — matches `adapters/ops_adapter.py`) |
| B6 | **Complexity / cost subsection** — cost per insertion (f(K, |selected|)), per Lagrangian iteration, why manageable at benchmark scale. Synthesises the scattered O(2^|J_k|·|J_k|), 3^K remarks. | §5 or §4 | P1 | ☐ |
| B7 | **Experimental protocol paragraph** — which BPC results are verbatim-from-literature vs recomputed; how CPU-hour budgets are matched (BPC 1h); explicit "no per-instance tuning". | §6.1 | P1 | ◐ (hardware done; protocol prose missing) |
| B8 | **Scalability figure + real-world paragraph** — median runtime vs n (B/EB); tie to GTC/EMIR (typical n, time limits, why 5–10 min solves matter). | §6.5 / §1 | P1 | ☐ |
| B9 | **Conclusions limitations paragraph** — one crisp paragraph separating algorithmic vs engineering vs theoretical limitations; explicit "not exact, no global approximation guarantee"; positions BPC warm-start future work. | §7 | P1 | ◐ (bullets exist) |

---

## C. Density — move detail to appendices (P1 — make the main text feel like a focused COR paper)

| ID | Action | Target | Pri | Status |
|----|--------|--------|-----|--------|
| C1 | **Compress the dual story:** crisp ~1-page §4.1–4.3 with a single dual-flow schematic; push Polyak-calibration / primal–dual-coupling mechanistic paragraphs to App B, referenced once from §4.4. | §4 | P1 | ◐ deferred — §4 was just expanded for the correctness fix (B10); mechanistic paragraphs already live in App B.5. A dual-flow *schematic* (figure) is still worth adding; full compression judged unnecessary |
| C2 | **Trim §6.5.1 ablation main text** to 3–4 takeaways + one small table (A0 vs A1 vs A3 vs A4); move per-family / per-instance signals, `<<<` flags, scope notes entirely to Appendix A. | §6.5.1 → App A | P1 | ✓ main text now = 4-row table + condensed takeaways; 6-row aggregate, per-arm stop-reason table, per-family Δ, per-instance signals all in Appendix A |
| C3 | **Trim §6.5.3 hardness main text** to 2–3 findings + one cross-impact table; defer M1/M2/M4, LR tests, coefficient tables to App B; drop "reporting model" econometrics phrasing from main body. | §6.5.3 → App B | P1 | ✓ main = 3 findings + 1 cross-impact table (Tobit/LR detail already in App B); "reporting model" → "primary specification" in OBS 15 |
| C4 | **Frame App B as "diagnostic/supporting"**, not "full statistical detail / reporting model" — core contribution is algorithmic, not statistical methodology. | App B + refs | P1 | ✓ App B retitled "(Diagnostic / Supporting)" with a framing sentence; "reporting model" removed |

---

## D. Editorial / consistency (P2)

| ID | Action | Target | Pri | Status |
|----|--------|--------|-----|--------|
| D1 | **Terminology lock:** always "certified gap"/"Lagrangian certificate" (never bare "gap"); always "6 benchmark families (K=2,3,4)" with the H1/E1 exclusion stated once; consistent "processors"/"telescopes" (no "vehicles" in main text). | global | P2 | ✓ (2026-06-23: 2 bare "mean gap"→"mean certified gap" in §6.2; one metaphorical "fill that gap" reworded; remaining bare "gap" are correctly BPC's *primal–dual* gaps or figure labels. Families consistently "six … (K=2,3,4)" with exclusion stated in abstract/§1/§3. "vehicle"/"machine" appear only in VRP-literature references and reference titles — no SRPS entity mislabeled; "machinery" benign) |
| D2 | **Instantiate every WRITE NOTE / OBS directive into actual prose**, then delete the meta blocks (e.g., denominator mismatch, A3 scope limitation must appear as sentences, not reminders). | global | P1 | ✓ (2026-06-23: grep of `paper/` for WRITE NOTE / OBS / TODO / FIXME / placeholder / red-text → **none remain** in either `.tex`; the manuscript is meta-block-free) |
| D3 | **Data/code availability statement** — promise a public repo (URL footnote), summarise contents (solver, experiment driver, analysis scripts). Replace internal script names (`build_paper_stats.py`, `adaptive_master.csv`) in prose with a single availability statement; keep script citations only in our internal provenance, not the manuscript body. | §7 / dedicated | P1 | ☐ |

---

## Draft-assembly order (suggested execution sequence)

1. **B1 Abstract** + **B2 Intro paragraph** (set the frame) — *abstract awaiting user draft*
2. **B3 Formal model** (unblocks a proper §2)
3. **B4 Algorithm 1** (+ B6 complexity) — *Algo 1 awaiting user draft*
4. **A1–A4 framing/tone sweep** across the whole skeleton
5. **C1–C4 density pass** (move detail to appendices)
6. **B7 protocol**, **B8 scalability+application**, **B9 limitations**
7. **D1–D3 editorial + availability statement**, then strip all WRITE NOTE/OBS blocks
8. **B5 Algorithm 2** (with the pseudocode step)

---

## Validation findings (independent check of assistant proposals, 2026-06-22)

Checked the candidate abstract, Algorithm 1, and black-box descriptions against the actual code.

- **B10 [P0 — DONE] Dual section described the wrong relaxation.** §4.1 (and the abstract draft) said
  the method relaxes the *synchronisation/timing* constraints (multipliers λ, dual "maximised by ascent").
  The implementation (`core/ops_bounds.py:lagrangian_bound`) relaxes the **joint-service coupling**
  y_j ≤ x_{j,k} with multipliers **μ_{j,k}**, giving L(μ)=Σ_j max(0,b_j−Σ_k μ_{j,k})+Σ_k O_k(μ),
  a valid UB **minimised** by subgradient descent. **Fixed** §4.1, §4.2, §4.4, Appendix B.5 Link 4,
  Algorithm 1, abstract, and the Polyak numerator (L(μ)−θ*). Symbol unified to μ (ALNS smoothing λ=0.8
  in §5.4 is a distinct, unrelated constant — left as-is).
- **B11 [P1 — open] Complexity nit:** per-processor DP is O(2^{|J_k|}·|J_k|²) (corrected in §4.1);
  ensure the §B6 complexity subsection uses this.
- Abstract numbers, 3^{|K_j|} insertion, BPC "up to n=60" — all verified correct.

- **B12 [P0 — DONE (reframe); P1 data task open] Validation-vs-contribution split + fair runtime.**
  The "97.4% match-or-improve" and "5.1 min vs 1-hour" headlines were unfair: 241 of those are trivial
  ties on instances BPC *already proved optimal* (certificate redundant there), and the 1 hour is BPC's
  *cap*, not its solve time. **Reframed** abstract, §6.2, OBS 6/6b around: (a) **validation** — 245
  BPC-optimal instances, we recover the optimum on 241/245 (98.4%); (b) **contribution** — 415 BPC-open
  instances (gap or unreported), where all 24 incumbent-improvements and all 199 first-ever certified
  solutions live (mean cert 0.173%, 100% within 2%). Speed claim restricted to the hard/open regime.
  **Data task DONE:** `build_bpc_times.py` parses BPC Tables 2–5 → `results/analysis/bpc_times.csv`
  (E-variant OA gap cross-validated against our data on 72/72 reported groups). Per-group runtime
  comparison now in §6.2. **Key honest finding:** BPC's limit is genuinely 1 CPU-hour (confirmed p9),
  and the OA column is the *average per-instance* time. On the 45 groups BPC solves, **BPC is ≈8×
  faster** than us (37 s vs 300 s) and already optimal — no advantage to us there. Our speed win is
  only on the 27 hard groups (478 s vs 1201 s, ≈2.5×) and the 300 instances BPC never reports.
  This replaces the earlier blanket "5.1 min vs 1-hour" claim.
  **SUPERSEDED 2026-06-23:** the 2-way validation/contribution split was replaced by a **3-way A/B/C
  subgroup table** (`build_bpc_subgroups.py` → `tab:bpcsplit`): A 245 (A1 241 / A2 4) · B 112
  (B1 15 / B2 93 / B3 4) · C 300, framed as no/positive/principal contribution. `tab:runtime` was
  folded into this single table (BPC's 0.19% residual gap on B kept as a sentence). First-ever
  199→196 (3 partial-group blanks regrouped with C by footnote). Explicit speed ratios removed from
  prose, kept in the table; "when to use which" usage guidance added.

## Awaiting user input — none outstanding
- **B1** abstract — ✓ received & integrated
- **B4** Algorithm 1 — ✓ received & integrated

Next (2026-06-23): A1–A4 framing/tone sweep ✓ and C2–C4 density pass ✓ are done; §6.2 restructured
to the A/B/C subgroup table and the paper repositioned complementary-not-competing, with the runtime
comparability paragraph (A5) added. **Remaining top priority is the literature review + references**
(only 7 refs; §2.2/§3.2 thin) — see `memory/project_roadmap.md` → "Next actions #1". Then Algorithm 2
(B5), B2 intro paragraph, B6/B7/B8/B9, and D1–D3 (terminology lock, strip meta-blocks, availability statement).

---

## Reviewer-block responses (2026-06-23) — applied to BOTH `main_standalone.tex` and `main.tex`

Four reviewer-style critique blocks were assessed and addressed. All fixes are exposition/calibration;
no new experiments were run. Every change verified lint-clean (env balance, braces, math, refs).

**Block 1 — Relevance & novelty.** Lowest risk; "first … for SRPS" is correctly scoped and defensible
(SRPS is narrow; only exact BPC exists). ✓ Narrowed the one over-broad clause in §3: "…optimality
gaps for SRPS **or closely related orienteering-type problems**" → scoped to SRPS plus a hedged "we
are not aware … though we make no claim to an exhaustive survey." Complement-to-BPC framing and
method-not-application positioning already in place. **Open:** the real defence is the lit-review
expansion (7 refs → ~25–40), still the standing top priority.

**Block 2 — Formulation & certification (the danger block).** ✓ The "O(2^{|J_k|}) is impossible at
n=150" red flag is **empirically false**: measured max |J_k| = 13 across all 660 instances, flat in n
(|K|=55 processors, |K_j|∈{2,3,4}); §4.1 now states this + "exact, no pruning". ✓ New **Appendix A**
(`app:formulation`): SRPS model (vars + feasibility (i)–(iii)), explicit relaxation/decomposition,
Proposition + full weak-duality proof, exact O_k(μ) + tractability, and an honest validity-guard
subsection. §2 points to it. Empirical facts from `core/ops_bounds.py` + the 660 instance JSONs.

**Block 3 — Algorithmic contribution (self-contradiction).** ✓ Real contradiction removed: prose
claimed in-loop re-bound is "the main reason"/"turns ALNS into a certified solver", but ablation A3
("no UB refresh") = +0.000. Root cause: the ablation **fixes the UB from A0** (isolates primal), so
A3 is ~0 by construction. Reframed: **the Lagrangian bound certifies; the in-loop refresh sharpens it
on the hard tail**; §4.4/§6.5 overclaims rescoped; ablation §App-A intro now states the fixed-bound
caveat. ("main reason"/"turns the ALNS" → 0 occurrences.) Optional future: with/without-rebound
mini-experiment on the 70-hardest, each using its own bound.

**Block 4 — Computational evidence.** ✓ Six wording/calibration edits: (1) added "the substantive
comparison is objective value and certified coverage, not runtime" to §6.2; (2) "BPC reports no
solution" now hedged via a footnote (no *published* result under the 1-h campaign; not "no solution
exists"), abstract softened; (3) "stale or mis-recorded published value" → neutral reviewer wording,
table tag `stale BKS`→`published BKS` (stale/mis-recorded → 0); (4) the four A2 one-unit misses
explained as **heuristic primal search, not bound failure**.

**Block 5 — Robustness/statistics (over-weighted).** ✓ **Closed by existing work — no edit needed**
(2026-06-23). The recommendation (keep hardness in the appendix, reduce main text to one paragraph,
frame as diagnostic) was already satisfied by the C3 density pass: §6.5 main text is two short
paragraphs + Figure 2, explicitly *"diagnostic rather than a core methodological contribution; full
model detail relegated to the appendix"*; all Tobit/LR/coefficient tables sit in Appendix B, all
sensitivity/ablation tables in Appendix A. The two underlying risks are mitigated elsewhere: the
"padding unless certification is rock solid" risk is answered by **Appendix A (block 2)** + the
script-derived reproducibility, and the "30-instance ablation too small for strong claims" risk by
the **block-3 reframe** (strong ablation claims removed). Optional-but-declined cosmetic merge of the
two §6.5 paragraphs into one.

## References pass (2026-06-23/24)

Bibliography **7 → 12**, all Crossref-verified. Every candidate reference supplied to us arrived with
**fabricated metadata** (real title, invented authors/venue/year/DOI) — caught and corrected the
Afifi entry and all 5 proposed additions (Pisinger 2025, Voigt 2025, Polyak 1969, Sakarya 2025,
Lianes 2021). In-text anchors added in §2.1, §3 (Broader routing), §4.2 (Subgradient). Full plan,
the verify-before-insert protocol, and the remaining trajectory (target ~18–25) are in
**`docs/literature_roadmap.md`**. This is the standing top-priority pre-submission task and the real
defence of the block-1 "first *for SRPS*" claim.

---

*Cross-ref: experiment/writing status in `memory/project_roadmap.md`; format constraints in
`docs/cor_tight_skeleton.md` (NOTE: stale as of 2026-08-28 — superseded by Section E below);
content source in `docs/paper_skeleton.md`.*

---

## E. Structural reorganization — Perplexity full remarks (2026-08-28)

*Supersedes `docs/cor_tight_skeleton.md`'s length/structure guidance (that file is 2+ months
stale). Target: ~26–32pp main text + a single coherent supplement (S1–S5), not a collection of
unrelated attachments.*

**STATUS (2026-08-29): executed.** Appendix A (SRPS model/Lagrangian/DP/numerical-safeguard
detail) and Appendix B (full ablation family/size breakdown, full sensitivity table, refinement
iteration-cap table, replayed-stopping-rule Table 7) removed from `main.tex` and moved to
`supplementary.tex` (new §5 Lagrangian-bound derivation + §6 extended computational results).
Main text condensed to a single "Ablation, sensitivity, and hardness summary" subsection
(pooled `tab:ablation` kept, headline paragraph, MDE, pointers to supplement for the
per-family/per-size/cross-check detail). E3.1 (post-search-refinement repetition) and E3.2
(primal-dual-coupling repetition) both consolidated; E3.3 (BPC-complementarity) was already
correctly scoped (verified via grep, no change needed). Result: main.tex 50pp → 39pp (36pp
excluding references); supplementary.tex 5pp → 10pp. Still somewhat above the 26–32pp target
(36pp main-text-only) — the remaining gap is mostly format overhead (algorithm listings,
table/figure floats) rather than uncut prose; further reduction would mean cutting into
Introduction/Discussion prose, which was not done without a separate review pass. Safety
snapshot of the pre-restructure state: git tag `v1.2-pre-E1E4-restructure`.

**Reviewer-safe rule for what stays vs moves:** *"If a reviewer must read it to decide whether
the method is correct, novel, or empirically supported, keep it in the main paper. If a reader
needs it to reimplement, reproduce, audit, or explore the method in depth — but can still assess
the paper without it — put it in the supplement or repository."*

### E1. What must stay in main text (non-negotiable)

Problem definition + synchronization structure; concise SRPS formulation; formal Lagrangian
relaxation definition; main validity proposition/proof (the certificate proof **must not** move
entirely to a supplement — "a certified method cannot defer its certification argument entirely
to a supplement"); certified-gap definition; feasibility oracle description (concise); ALNS
architecture + synchronization-aware insertion idea; main algorithm pseudocode (shortened); main
computational setup; main benchmark table; simplified BPC comparison table; main validation
against known optima; key limitations; data/code availability statement.

### E2. Target section-by-section structure (~26–32pp)

| # | Section | Target length | Move to supplement |
|---|---|---|---|
| 1 | Introduction | 2.5–3pp | Extended literature survey → **cut, not moved** |
| 2 | SRPS + formulation | 3–4pp | Full SRPS-1 model, variable/constraint listing → **S1** |
| 3 | Lagrangian certification | 4–5pp | Full algebraic derivation, expanded weak-duality proof, bitmask DP recurrence, complexity analysis, expanded floating-point/numerical notes → **S2** |
| 4 | Synchronization-aware ALNS | 4–5pp | Full operator implementation rules, full parameter table, ejection-chain mechanics, detailed feasibility-oracle pseudocode, detailed insertion pseudocode → **S3** |
| 5 | Computational results | 7–9pp | Full per-instance 660-row table, extended sensitivity tables, full ablation tables, CPLEX run logs/model settings, additional per-family/n/α/seed plots, detailed statistical model output → **S4** |
| 6 | Discussion + conclusion | 2–3pp | — |
| — | Reproducibility | — | Certificate-file schema, multiplier precision, verification instructions, repo commit ID, reproduction commands, checksums → **S5** |

**Retain in main, condensed:** Table 3 (660-instance headline summary), Table 4 (BPC coverage,
simplified), Table 5 (representative new/improved certified solutions, ~3 entries), Table 6
(in-loop rebounding effect on hard tail), one compact parameter table, Figures 1–2.

**Likely move:** Table 7 (replayed stopping rules) → supplement, unless runtime-policy design
becomes a claimed central contribution.

**Never typeset in the supplement — repository/data archive only:** full certificate vectors μ
(describe structure, don't list values), full verification logs (summary stats only + supplement
instructions).

### E3. What to cut entirely, not move (repetition, not content)

| ID | Repetition found | Appears in | Action |
|---|---|---|---|
| E3.1 | Post-search refinement re-justified 5+ times (runs after primal; doesn't alter incumbent; post-search μ still valid; doesn't compete with primal effort; tightens cert not objective) | §4.3, 4.4, 4.5, 6.1, 6.7, 6.8, conclusion | State once in §4.3 (2–3 paragraphs); report empirical consequence once in §6 ("refinement raises proven optima from 280→446 without changing any incumbent"); one interpretive sentence in §7. Est. saves 1.5–2.5pp. **Cross-ref: `cor_revision_roadmap.md` §A/C already did a related density pass in June — verify this specific repetition wasn't reintroduced by the P1/P2/R2 amendment sessions.** |
| E3.2 | Narrow primal-dual coupling (incumbent enters dual only via Polyak target θ*=z*, multipliers don't guide insertion/destroy/adaptation) repeated as full subsection + Algorithm 1 comments + elsewhere | Method section, Algorithm 1 | State once, e.g. a boxed "Design choice" paragraph |
| E3.3 | "Complements rather than replaces BPC" | Abstract, intro, results, discussion, conclusion | Keep only in abstract + end of intro + discussion/conclusion |
| E3.4 | Long defensive prose anticipating objections (hardware comparisons, stopping-rule replay, refinement admissibility, "not fitted retrospectively") | Scattered | Shorten to concise, evidence-led statements — "a shorter presentation often appears more confident and more publishable" |

### E4. Suggested wording for the data-availability / cover-letter statement

> "Additional technical material is provided in the Online Supplementary Material, including the
> complete SRPS formulation, detailed proof steps, pseudocode for the feasibility and insertion
> procedures, full parameter settings, extended robustness experiments, and complete per-instance
> computational results. The accompanying reproducibility archive contains the source code,
> benchmark-processing scripts, incumbent solutions, Lagrangian multiplier certificates, and a
> standalone certificate verifier."

---

## F. Simulated COR reviewer report — full remarks (2026-08-28)

*Simulated recommendation: **Major Revision** (not reject). High confidence. Covers a different,
more numerically/methodologically adversarial angle than the June virtual-assistant review in
Sections A–D above. Status column reflects independent verification done in today's session only
— items marked "claimed done, not re-verified today" reflect the conversation summary's account
of prior P1/P2/R2 amendment sessions and should be spot-checked before relying on them.*

**Overall evaluation table (simulated reviewer):** Originality — Strong. Relevance to COR —
Strong. Methodological soundness — Promising, needs clarification. Computational study —
Extensive, not yet fully persuasive. Reproducibility — Claimed, not sufficiently demonstrated.
Writing — Generally strong but over-argued/repetitive (cf. Section E3 above). Recommendation —
Major revision.

| ID | Major comment | Required revision | Status |
|---|---|---|---|
| F1 | Lagrangian relaxation exposition mixes two distinct operations (dualising joint-service vs. relaxing synchronisation in subproblems) without one explicit relaxed feasible set $\mathcal{X}^{rel}$ stated before the decomposition | Define $\mathcal{X}^{rel}$ explicitly; prove (1) every SRPS-feasible solution ∈ $\mathcal{X}^{rel}$, (2) each penalty term nonnegative, (3) SRPS objective ≤ L(μ), (4) decomposition is exact. Promote "both operations only enlarge feasible region / add nonneg penalty" from an Appendix-A aside to a central main-text proposition | ✅ **Verified 2026-08-30** — directly confirmed in current `main.tex` §3 (`sec:lagrangian`): `$\mathcal{X}^{\mathrm{rel}}$` is explicitly defined before the decomposition, and `Proposition~\ref{prop:main_valid}` states all four required parts (a)-(d) with a full proof, in the main text (not an appendix aside) |
| F2 | Synchronization feasibility oracle lacks a formal, reproducible specification (graph nodes? common-start representation? travel/service/depot/idle encoding? cycle detection? horizon enforcement? source/completion nodes? divergent per-processor travel paths?) | Formal subsection or algorithmic pseudocode: (1) precedence graph construction, (2) exact arc-weight definition, (3) longest-path recurrence, (4) cycle-detection method, (5) feasibility criterion, (6) complexity in served-jobs/processor-routes terms. A worked 2-processor example showing implicit waiting | ✓ **DONE 2026-08-28** — Algorithm S2 (`\textsc{LongestPathScheduleCheck}`) added to `supplementary.tex`, covering all 6 requested items + a worked 2-processor example. `main.tex`'s oracle prose rewritten to match: found and fixed a real prose/code mismatch — old text described an explicit "synchronisation arc" mechanism that doesn't exist in `adapters/ops_adapter.py::compute_schedule`; the actual mechanism is a single shared node per job receiving multiple incoming arcs (one per required processor), with the max-relaxation enforcing the common start time. Complexity corrected from the old (wrong) $O(\lvert J\rvert\cdot\lvert K\rvert)$ to $O(\lvert\textit{selected}\rvert)$, matching $\lvert K_j\rvert$ being bounded (2-4), not scaled by the total processor count $\lvert K\rvert=55$. Both files compile clean (46pp main, 4pp supplement) |
| F3 | "First certified primal-dual solver for SRPS" novelty claims carry high evidentiary burden | Soften throughout: "to the best of our knowledge" consistently; distinguish (a) heuristic reporting a bound, (b) heuristic with a theoretically valid bound, (c) independently re-evaluable certificates, (d) certified-ratio approximation algorithm (paper does NOT provide (d) — say so). Suggested replacement wording given in full remarks | ✅ **Verified 2026-08-30** — "to the best of our knowledge" appears exactly 3× in current `main.tex` (abstract-adjacent intro, contribution list, conclusion opening), consistent with the summary's claimed fix. The (a)-(d) distinction itself was not re-derived word-for-word today; the softening pattern is confirmed present |
| F4 | Certificate deposit/verification protocol undocumented: what's deposited, precision, format, is verifier independent of solver, numerical precision/rounding/tolerance, how is stored-μ precision guaranteed not to alter ⌊L(μ)+ε⌋ | Reproducibility+verification subsection: repo URL/DOI, certificate file-content spec, μ format/precision, one-instance + full-benchmark verify commands, statement of verifier/solver code independence, per-instance table (ID, incumbent, final UB, cert gap, initial/in-loop/refinement provenance, runtime split, checksum) | ✓ **substantially addressed today via Path B** — `verify_interval_arithmetic.py` (independent re-derivation from raw benchmark file + stored μ only, no cached objects), README "Path B" section with exact commands, `results/analysis/path_b_verification_exact.csv` committed. **Still open:** explicit checksums/hashes for certificate files; whether verifier counts as fully "independent implementation" (it reuses `orienteering_dp_with_selection` from the same codebase, not a from-scratch reimplementation) — this exact caveat was flagged during today's Path B discussion |
| F5 | ε=1e-9 floor safeguard is not automatically a rigorous numerical guarantee unless total arithmetic error is bounded below ε for every evaluation; different hardware/BLAS/summation order could differ | Either (1) implement directed rounding / interval arithmetic / rational multipliers / high-precision decimal / explicit conservative error bound, or (2) explicitly weaken claim to "numerically safeguarded certificate" with documented empirical validation + residual assumption stated | ✓ **DONE today, option (1), strongest form** — Path B exact/directed-rounding mode (`Decimal(x)` exact conversion + `ROUND_CEILING` summation): 660/660 valid at **zero** tolerance, 0/660×55 DP-subset discrepancies. Paper's Appendix A rewritten (Algorithm 2 + findings), replacing the old "we have not implemented that" sentence. Path A (theoretical worst-case bound) explicitly considered and declined as unnecessary given Path B's stronger empirical result |
| F6 | BPC comparison: hardware/implementation confounding (Python/6-workers vs compiled CPLEX/older CPU), "no reported BPC result" ambiguity, need common-platform head-to-head | Remove/reframe direct time-ratio in principal table, or add calibration-normalized comparison; carry the "no published result under 1h campaign ≠ unsolvable" qualification into main text; acknowledge missing common-hardware BPC comparison as a limitation, not just a caveat | ✅ **Verified 2026-08-30** — current `main.tex` §5 ("Experimental setup") contains the explicit hardware-confound paragraph ending "We therefore make no hardware-normalised speed claim: if anything the comparison is not in our favour"; the "no reported BPC solution" footnote in Table~\ref{tab:bpcsplit}'s discussion explicitly states this "does not assert that no feasible solution exists or that the exact method could not find one under a different setup." Both required qualifications are present in main text, not just a caveat |
| F7 | Ablation doesn't yet isolate each of ≥5 components (greedy construction, sync-aware insertion, ALNS destroy-repair, in-loop re-bound, refinement, ejection chain) — specific questions on insertion vs simpler rule, adaptive-operator gain, adaptive-destroy-tier gain | Systematic ablation table (variant × mean obj loss × mean cert gap × proven-optimal × runtime × notes); explicitly distinguish full-rerun vs logged-trajectory-inferred vs analytically-evaluated | ✓ **DONE 2026-08-29** — redesigned B1–B8+S ablation executed in full: 40-instance stratified sample (20 hard-tail + 20 closing), 400/400 jobs, 0 errors, committed (`results/analysis/ablation_b1b8s_20260829_0319.csv`). Numeric per-component summary table (`tab:ablation`) now in `main.tex`'s "Ablation, sensitivity, and hardness summary" subsection, with full per-family/per-size breakdown, MDE, and B5/B7 cross-check in the Supplementary Material (reproducible via `build_ablation_summary.py`). Sync-aware insertion itself is not ablated (it is a correctness requirement for SRPS feasibility, not a tunable heuristic choice, so a "without it" arm would not produce valid solutions) — everything else on the reviewer's list (destroy-repair diversity, adaptive-operator weights, destroy-tier escalation, in-loop re-bound cross-check, ejection-chain identity) is covered |
| F8 | Stochastic evaluation too limited — single seed-cycle run per instance; need multi-seed replication distinguishing deterministic cert validity (no replication needed once μ fixed) from stochastic primal-search quality (replication required) | 10–30 independent seed replicates on a stratified subset (small/med/large n, each \|K_j\|, line/Euclidean, each α, hard-tail); report mean/SD of objective, cert gap, runtime distribution, probability of matching best run; don't interpret effects below noise floor | ✓ **DONE 2026-08-29** — Tier 1 (420 pairs, complete) + Tier 2 noise floor (70/70 hard-tail instances, disjoint A0/A0′ seed sets, complete) both finished and embedded in the paper. Tier 2 measured mean \|Δ\|=0.036pp (median 0, max 0.942pp), used directly as the ablation's detectability scale bar (MDE=0.084pp at n=20/stratum) — the reviewer's exact ask, closing the loop between F8 and F7 |
| F9 | Internal inconsistencies: refinement iteration budget (3000) not stated until App B.2; "no instance reaches the cap" wording awkward; group counts (245+112+300+3=660) not reconciled in main narrative until a footnote; "certificate alone" wording on 226 instances overstates independence from primal validator; "exactness of the dual bound" conflates bound validity with dual optimality (bound is valid but generally not dual-optimal — subgradient is truncated) | State full refinement budget (iteration cap, time cap, convergence criterion, same-cap-for-all?, warm-start source, same subgradient schedule?) in main computational setup; reconcile group totals immediately in-text; reword "certificate alone" → "feasible solution + matching Lagrangian UB, without a corresponding BPC proof reported in the baseline"; reword "exactness of the dual bound rests on..." → "validity ... relies on exact per-processor subproblem solution; tightness depends on truncated subgradient optimization" | ✅ **Verified 2026-08-30** — all four sub-items confirmed directly against current `main.tex`: (1) the 3000-vs-200 iteration budget is stated in-line in §3's "Post-search certificate refinement" subsubsection, not deferred to an appendix; (2) group-count reconciliation ("$412$ in groups B and C plus three partially-solved instances", summing with Group A's 245 to 660) is in the main results-section prose (§5.4), not only a table footnote; (3) the phrase "certificate alone" does not appear anywhere in current `main.tex`; (4) the phrase "exactness of the dual bound" does not appear anywhere in current `main.tex` either — both problematic phrasings are already absent |

### F-minor. Minor/editorial comments (not independently triaged yet)

Abstract too dense (too many numbers/mechanism details for one paragraph — trim to: problem+gap,
method, main result, BPC complementarity, reproducibility); "processor" terminology may confuse OR
readers used to "vehicle/agent/resource" (define early, or use "resource" for the telescope
application); missing formal definition of α (budget tightness) in main text; ambiguous global
time-limit semantics (common horizon from t=0? per-route own start? differing depot departure
times?) — feasibility definition should settle this explicitly; benchmark geometry (line vs
Euclidean: symmetric distances? travel=distance? job-specific service time?) underspecified;
"primal-dual" terminology should be explicitly scoped once as "Lagrangian-heuristic sense" (not a
complementary-slackness / proven-ratio primal-dual approximation scheme); **Algorithm 1 notation
issues** — `InitialUpperBound` combines "independent orienteering" + "group decomposition" but
the latter isn't formally introduced; `GreedyProfitFirst` needs pseudocode/definition;
`EjectionChain` mechanics not introduced until the appendix; `UB ← ⌊L⌋` conflicts with the later
ε-tolerance discussion (**NOTE: conversation summary claims R2 already fixed this specific point —
"UB ← min(UB, ⌊L(μ)+ε⌋) with tightened flag" — spot-check this landed correctly given today's
Path B work touches the same formula**); gap formula should guard against UB=0; initial upper
bound $UB_0=\lfloor\min\{UB_{indep},UB_{group}\}\rfloor$ needs formal definition, validity proof,
and per-component activation-frequency reporting (155 instances close before ALNS/subgradient
steps); Tobit regression claimed in abstract but not reported further in body — either present the
full model (dependent-variable construction, censoring rule, covariates, coefficients, SEs,
diagnostics) or remove the abstract claim; Figure 2 caption ("α=0.75 collapses gaps across all
families") should explain *why* larger α → looser budget, not leave it to reader inference;
"all within 2%" headline should be reinforced as a certified upper bound on relative suboptimality
(UB in the denominator), not an empirically observed error vs. known optimum.

### F-experiments. Requested additional experiments

**Essential:** (1) independent certificate verification on all 660 deposited certs, stating
verifier/solver code independence — **✓ done via Path B today**, with the from-scratch-vs-shared-DP
caveat noted in F4. (2) Multi-seed stochastic replication (10–30 seeds) on a stratified subset +
hard tail — **✓ done 2026-08-29**, Tier 1 + Tier 2 both complete, see F8. (3) Ablation of sync-aware insertion vs a
cheaper/simpler alternative — **not started, and likely not applicable**: sync-aware insertion is a
correctness requirement for SRPS feasibility (a non-sync-aware insertion would produce infeasible
solutions), not an optional heuristic choice, so this specific ablation as literally requested may
not be a well-posed experiment; a defensible substitute would compare candidate-cap $c$ values,
which remains untested (§ABLATION_DESIGN.md "known limitations"). (4) Ablation of adaptive search
(operator selection, destroy-tier escalation) vs static variants — **✓ done 2026-08-29**, B1
(uniform operator choice) and B6 (no tier escalation) both included as arms in the redesigned
ablation, isolated per-stratum. (5) Formal initial-bound analysis + per-component
activation-frequency reporting — **not started**. (6) Expand CPLEX/MILP validation beyond 30
instances with a stratified sample — **not started**.

**Desirable:** primal-vs-certificate-tightness-over-time plot/table; runtime decomposition
(greedy/ALNS/in-loop-rebound/refinement/verification) — **partially available** (Path B timing:
~26s for 660 exact-mode; per-arm `rt_s` already logged in Tier 2's noise-floor CSV, not yet
aggregated into a dedicated runtime-decomposition table); scalability experiment beyond published
benchmark sizes, or explicit statement that scalability is demonstrated only over the established
benchmark; small illustrative telescope-scheduling example for accessibility.

### F-decision. Simulated decision letter summary

Major Revision. Required before resubmission: formalize relaxed model + bound-validity proof
(F1 — **verified**); fully specify the feasibility oracle (F2 — **done**); document a standalone certificate-verification
workflow (F4 — largely done); strengthen numerical safeguards for safe upper bounds (F5 — **done**,
strongest form); add stochastic replications + targeted ablations (F7/F8 — **done 2026-08-29**); clarify
experimental comparison protocol/limitations (F6 — **verified**); revise overstrong novelty/statistical claims
(F3 — **verified**, Tobit item in F-minor still open); address listed consistency/presentation issues (F9 — **verified**, F-minor). Also
done 2026-08-29, not requested by this simulated review but flagged separately in Section E: the
full main-text/supplement structural reorganization (~26–32pp target).

---

*Section E/F added 2026-08-28. F1, F2, F3, F5, F6, F9, E, F7, F8, G1.8 verified/done as of 2026-08-30.
Remaining genuinely open: F4's from-scratch-verifier caveat, F-minor items (Tobit, terminology,
Algorithm 1 notation), F-experiments (5) and (6), and G-section items not yet cross-checked
(G1.9, G2.6-2.7, G2.12-2.15) — these need either new experiments/analysis or a dedicated prose pass,
not a quick grep-based spot-check.*

---

## G. Simulated COR editorial decision + referee report #2 (2026-08-28)

*A second, independent simulated review (editor's letter + full referee report, 12 major + 16
minor comments), distinct from Section F's review. Overlaps substantially with F but uses
different framing and catches some additional specific issues. Status legend for this section per
explicit user instruction: **Implemented** (verified fixed in current `main.tex`/code) ·
**To be implemented** (confirmed still needed) · **Deliberately ignored** (considered and
consciously not acted on, with reason given). Verified directly against current `main.tex` today
where marked "verified"; otherwise inherits the same "claimed done, not re-verified" caveat as
Section F.*

**Simulated decision:** Major Revision. Editor's letter frames the numerical-certification gap as
the decisive issue — "the paper's strongest claim... is not yet rigorously supported under
floating-point computation." Referee's own estimate: Major revision most likely; reject-and-invite
plausible if the editor treats the float defect as invalidating the whole computational study;
minor revision/acceptance "highly unlikely" as submitted.

### G1. Major comments

| ID | Comment | Status | Notes |
|---|---|---|---|
| G1.1 | ε=1e-9 tolerance is not a rigorous remedy without a proof that total downward numerical error < ε for every certificate. Demands one of: (1) exact rational/fixed-point arithmetic, (2) directed interval arithmetic with guaranteed upper endpoint, (3) formally derived worst-case forward-error bound, (4) upward rounding of every relevant operation. Final $UB=\lfloor\overline{L}(\mu)\rfloor$ from a proven upper enclosure. All 660 certificates must be reverified and the 446-optimal count re-reported if it changes | ✅ **Implemented, verified today** | Path B's exact/directed-rounding mode is precisely option (2): `Decimal(x)` exact bit-for-bit conversion + `ROUND_CEILING` summation = a certified upper enclosure, not a repetition of the float64 computation. Result: 660/660 valid at **zero** tolerance — the 446-optimal count does not change (in fact strengthens: the ε-safeguard is now proven to compensate only for float64 summation rounding, never a genuine invalidity, on every studied instance). `verify_interval_arithmetic.py`, `results/analysis/path_b_verification_exact.csv`, Appendix A Algorithm 2 all committed |
| G1.2 | "Exact" conflates (a) exact enumeration of the discrete feasible set, (b) numerical evaluation of the multiplier-dependent objective, (c) exactness/certified enclosure of the resulting bound | ✅ **Implemented 2026-08-28** | Added a consolidated sentence in the main computational-setup paragraph (§ "Every reported certified gap...") explicitly distinguishing (i)/(ii)/(iii) and citing Path B's Appendix A independent re-derivation as the answer to (iii), rather than leaving it assumed |
| G1.3 | ALNS insufficiently specified: insertion-cost definition, tie treatment, profit-to-cost/regret definitions, Shaw relatedness, SA acceptance formula, temperature reset policy, operator-weight init/update frequency, construction heuristic, ejection-chain logic, longest-path feasibility construction + cycle detection + makespan, all tie-breaking rules. Proposition 2 omits candidate-generation and feasibility-check cost from the complexity bound | ✅ **Fully implemented 2026-08-28** | All sub-items done. Shaw relatedness $\rho(p,j)=T_{p,j}+T_{j,p}$ and regret-2 $c_2(j)-c(j)$ / ratio $b_j/\max(c(j),1)$ formulas added last, verified against `core/operators.py::destroy_shaw,repair_regret` and `adapters/ops_adapter.py::relatedness`. Nothing remaining open in this item |
| G1.4 | Algorithm 1 inconsistent with prose: UB update, missing ε tolerance, initial-bound overwrite risk, refinement/ejection-chain sequence not represented | ✅ **Implemented, verified today** | Directly checked current `main.tex` line 495: `UB' \gets \min(UB, \lfloor L+\varepsilon\rfloor)`, `tightened \gets (UB'<UB)` — the exact fix this comment demands is present. This appears to be the R2 "Algorithm 1 note on refinement post-loop" + "UB ← min(UB, ⌊L+ε⌋)" fix the conversation summary claimed, and unlike F2/oracle-pseudocode, **this one checks out** |
| G1.5 | Refinement-time framing ("time the search could not otherwise have used") is conceptually misleading — reformulate as: one-hour cap includes refinement; refinement receives unused budget after primal stopping fires; allocation is a design choice, not free | ✅ **Implemented 2026-08-28** | Found the exact "cost nothing" phrase at old line 341 (a different section already had the correct careful framing, creating an internal inconsistency) — reworded to "draw only on budget the one-hour cap left unused... allocating that unused time to the dual is an algorithm design choice, not a free resource" |
| G1.6 | Stochastic validation inadequate — one fixed 6-seed run; "noise floor" from one duplicated 30-instance config is not a variability estimate. Needs repeated full-method runs on a stratified subset (closed-immediately, gap-threshold-stop, hard-tail-70, ALNS-misses-optimum, largest line/Euclidean instances), reporting distributions of objective/gap/runtime/stop-reason, paired comparisons for variants | 🔄 **In progress** | This is exactly what Tier 1 (✓ complete, 420 pairs) + **Tier 2 noise floor (🔄 running now)** are for — disjoint-seed-set (A0 vs A0′) replication on the 70 hard-tail instances. Tier 2 doesn't cover every stratum this comment lists (e.g. "ALNS misses a known optimum" instances specifically), so even after Tier 2 completes this should be marked ◐ not ✓ until that gap is assessed |
| G1.7 | Ablation doesn't isolate main ALNS design choices (adaptive vs uniform operator selection, sync-aware insertion vs simpler repair, multi-start vs equivalent-budget single run, destroy-tier escalation, SA vs improving-only acceptance, ejection chain, in-loop rebound, refinement); restricting some ablations to the endogenously-selected hard-tail set is a post-treatment selection problem (membership determined by the baseline method itself); no-refresh comparison's "identical objectives, some worse gaps" claim needs reconciling — if warm-started identically with the min-bound retained, a refreshed bound should never produce a worse gap | ◐ **Substantially done 2026-08-29** | The redesigned B1–B8+S ablation isolates: adaptive vs uniform operator selection (B1), SA vs greedy acceptance (B2), destroy diversity (B3), repair diversity (B4), ejection chain (B5, cross-checked against the identity), destroy-tier escalation (B6), in-loop re-bound (B7, cross-checked against the census), and multi-start (B8). **Not addressed and likely not a well-posed ablation:** sync-aware insertion vs a simpler repair — the insertion procedure is a correctness requirement for SRPS feasibility, not an optional heuristic (same conclusion as F-experiments item 3). **Post-treatment-selection critique:** partially answered by design — the redesign pre-registers a *second*, non-hard-tail stratum (20 closing multi-phase instances) and reports both strata separately, never pooled, specifically so a mechanism's effect where it cannot act (verified, not assumed, for B6/B7 on non-stalling instances) doesn't dilute its effect where it can; the sophisticated point about hard-tail membership itself being an endogenously-selected outcome of the baseline method is not separately rebutted in prose and would still benefit from an explicit written response. **No-refresh "worse gap" reconciliation:** already explained in the pre-existing Table 6 discussion ("this reflects run-to-run variation in the stochastic primal search rather than the bound itself, since the re-bound can only tighten the dual value") — not modified today, not independently re-derived, but the explanation is present in current `main.tex` |
| G1.8 | Cross-method comparison over-narrates Python-vs-CPLEX speculation; should compare objective/coverage/certified-bounds only, report each method's own published runtime without normalized-dominance claims, avoid "nothing to offer" framing where BPC already proves optimality (Lagrangian bound is still an independent certificate there) | ✅ **Verified 2026-08-30** | The phrase "nothing to offer" does not appear anywhere in current `main.tex`. §5.4's "Where the optimum is known" paragraph already frames the Group-A case correctly: "The dual certificates' validity is established independently by Proposition~\ref{prop:main_valid}... A certified heuristic on an instance already closed by an exact method provides an independent dual certificate but not a new primal result" — exactly the framing this comment requests |
| G1.9 | CPLEX validation (30 instances, 180s, 6 threads) is a selected subset with unclear budget comparability; "generally dominates the compact model's relaxation" conflates a time-limited B&B dual bound with the root LP relaxation. Wants separately reported: compact-model root relaxation, best CPLEX dual bound at 180s, CPLEX incumbent + final gap, the Lagrangian bound, and the proposed method's runtime — all on the same instances | ☐ **To be implemented** | Would require re-running/re-extracting CPLEX diagnostics not currently reported this way; genuinely new experimental/reporting work, not a wording fix |
| G1.10 | Benchmark accounting inconsistent: 245+112+300=657≠660; abstract's "115 open-incumbent + 300 unreported" vs body's "112 in Group B" | ✅ **Fully implemented 2026-08-28** | Verified today: current `main.tex` already reconciles 245(A)+412(B+C)+3(partial)=660 with an explicit footnote (matches the R2 "412→415 accounting" fix). **Fixed the newly-found abstract/body mismatch**: abstract's unreconciled "115" replaced with "112 where it reports an incumbent... with a nonzero gap, 300 for which its tables report no result, and 3 further partially-solved instances" — now matches the body's Group B=112 exactly, no invented number |
| G1.11 | Novelty claims like "tight coupling" / "self-tightening dual mechanism" overstate the interaction given the primal communicates only one scalar, multipliers don't guide search operators, dual returns only a stopping bound | ✅ **Fully implemented 2026-08-28** | Body already said "the coupling is narrow in both directions" with full detail; only the section title oversold it — retitled "Tight coupling between ALNS and Lagrangian bounding" → "Coupling between ALNS and Lagrangian bounding". Checked for other "tight coupling" occurrences and cross-references — none found, no other text needed updating |
| G1.12 | Tobit regression highlighted in abstract but withdrawn/under-supported in §6.9 — no coefficients, SEs, specification, censoring definition, diagnostics shown. Either present the full model or remove the abstract claim and treat Figure 2 as descriptive only | ☐ **To be implemented** | Matches Section F's F-minor Tobit item exactly — same open status, not yet decided which direction (full model vs. removal) |

### G2. Minor/presentation comments — quick objective check today

| ID | Comment | Status |
|---|---|---|
| G2.1–2.3 | "Appendix Appendix A/B" duplication, unresolved "Section ??", broken `efapp:formulation` ref | ✅ **Implemented, verified today** — none of these three strings appear anywhere in current `main.tex` |
| G2.4–2.5 | Clarify supplement availability; Appendix A gives only structural description, should be self-contained | ◐ not fully checked — supplement now substantially more complete after today's Algorithm S2 addition, but "self-contained main-text model" question not re-assessed |
| G2.6–2.7 | Notation consistency: $UB_{\text{lag}}$/$UB$/$UB^*$ alternation; $\lfloor\min_t L(\mu^t)\rfloor$ display consistency | ☐ not checked today |
| G2.8 | Explain zero-bound denominator case even if benchmark profits make it impossible | ✅ **Implemented 2026-08-28** | One-sentence guard added immediately after the cert\_gap formula in Appendix A: denominator is zero only if the optimal SRPS profit is itself zero, not reached by any studied instance, noted for completeness |
| G2.9 | "COR magazine" → full journal name in correspondence | N/A — this is about correspondence text, not the manuscript itself |
| G2.10–2.11 | "Reason to trust the certificates" logical error; recovery of known optima validates primal empirically but doesn't establish dual-certificate validity | ✅ **Implemented, verified today** — the exact phrase "reason to trust" does not appear anywhere in current `main.tex` (matches the R2 fix the summary described, and now directly confirmed) |
| G2.12 | "Integrality property" / alternative-decomposition claims in §8 need a formal proposition or stronger justification | ☐ not checked |
| G2.13 | Avoid saying refinement iterations cost "nothing" — they consume runtime even if not displacing the terminated search | ☐ not checked |
| G2.14 | Report CI methodology for mean certified gap; same-family instances may not be independent samples | ☐ not checked — genuine statistical-methodology question, likely nontrivial to resolve |
| G2.15 | Explain why $\lvert K_j\rvert=1$ families excluded from primary analysis but included in supplementary validation | ◐ likely already explained in scope section (§2.3 per Perplexity's plan) — not re-verified today |
| G2.16 | General: fix production defects (unresolved refs, repeated labels) before resubmission | ✅ **Implemented** — see G2.1–2.3 |

### G3. Deliberately-ignored items (none yet)

No item from either Section F or Section G has been explicitly triaged as "deliberately ignored" —
every open item above is either implemented, in progress, or genuinely still to be implemented.
The one candidate for deliberate rejection is **G1.9** (expanded CPLEX validation): given six-figure
compute cost for marginal evidentiary gain over the existing 30-instance check, and that Path B
already provides the stronger dual-side certification story, this could reasonably be triaged as
"deliberately reduced scope" rather than fully implemented — **not yet decided, flagged for a
scoping conversation before the next round of runs is planned.**

---

*Section G added 2026-08-28, same session as Section E/F. Net effect of today's cross-checking:
the conversation summary's "claimed done" status was correct for G1.4 (Algorithm 1 UB update),
G2.1–2.3 (broken refs), and G2.10–2.11 (trust-certificates wording) — three genuine confirmations,
not just claims. It was also the source of one real miss (F2/oracle pseudocode, now fixed) and one
newly-discovered inconsistency not previously flagged (G1.10's 115-vs-112 count). Net: trust the
summary's "done" claims somewhat more after this batch of spot-checks, but continue verifying
before relying on any single one for a submission-blocking decision.*
