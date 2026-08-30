# Literature & References — Trajectory and Roadmap

*Created 2026-06-24. The standing top-priority pre-submission task (see `memory/project_roadmap.md`
→ Next actions #1 and `cor_revision_roadmap.md` → Step 8). Goal: a broad-but-focused, **fully
verified** reference set that positions the paper in (i) the ALNS line, (ii) the Lagrangian/
subgradient tradition, and (iii) modern synchronised / prize-collecting routing — without bloat.*

---

## 0. Hard rule (learned the hard way) — VERIFY BEFORE INSERT

Every candidate reference handed to us so far has arrived with **fabricated metadata** — a plausible
title attached to invented authors / journal / volume / year / DOI. Confirmed cases:

| Proposed (wrong) | Reality (Crossref-verified) |
|---|---|
| Afifi et al., "TOP with time windows", COR 76 (2016) | Afifi/Dang/Moukrim, *Optimization Letters* 10(3) (2016) 511–525 — VRPTW + sync visits |
| Larsen & Ropke, COR 40(4) (2013) | **D. Pisinger**, *Transp. Res. C* 179 (2025) 105293 |
| Dahl/Fagerholt/Thomassen, EJOR 313(3) (2024) | **S. Voigt**, *EJOR* 322 (2025) 357–375 |
| Polyak, Handbook of Num. Analysis (2003) | **B. T. Polyak**, *USSR Comp. Math.* 9(3) (1969) 14–29 |
| Perron/Gendreau/Bräysy, COR 165 (2024) | **Sakarya et al.**, *Transp. Res. C* 171 (2025) 104987 |
| Fagerholt/Hoff/Korsvik, COR 89 (2018) | **Lianes et al.**, *COR* 134 (2021) 105316 |

**Protocol for EVERY new reference (no exceptions):**
1. Query Crossref by title — `https://api.crossref.org/works?query.bibliographic=<title words>&rows=3`
   (open API, no 403; ScienceDirect/Springer block direct fetch). Confirm authors, journal, volume,
   pages/article-no, year, DOI from the JSON.
2. If a DOI is claimed, resolve it: `https://api.crossref.org/works/<DOI>`.
3. Only then insert — and insert into **BOTH** `paper/main_standalone.tex` (`thebibliography`)
   **and** `paper/refs.bib` (used by `paper/main.tex`).
4. Re-run the cite↔bibitem lint (cites == bibitems, no dangling, brace/`$` balanced).
5. Never trust pasted authors/DOIs; never "adjust authors if needed to match" — look them up.

---

## 1. Current state — 23 references (all verified)

2026-06-24 batch (18 → 23), Crossref-verified, **two corrected from the supplied list**:
Golden-Levy-Vohra 1987 (OP origin, NRL 34(3)), Chao-Golden-Wasil 1996 (TOP origin,
EJOR 88(3) — *not* "Chao/Kan/Xu, Transp. Sci."), Gunawan-Lau-Vansteenwegen 2016
(OP survey update, EJOR 255(2)), Feillet-Dejax-Gendreau 2005 (TSP with profits,
*Transp. Sci.* 39(2) — *not* Oper. Res.), Pisinger-Ropke 2007 (LNS methodology,
COR 34(8)). Woven into §1 (OP/TOP/profit-collecting named) and §3.2 (LNS). The
"recent 2021+ sync paper" item is already satisfied (Lianes 2021, Sakarya 2025).


Grew 7 → 12 on 2026-06-23/24, then 12 → 18 on 2026-06-24 (Phases A/B/D below). Inventory by theme:
- **SRPS / exact base:** RieraLedesma2021SRPS.
- **OP/TOP metaheuristics + ALNS:** Vansteenwegen2011Orienteering (survey), RopkePisinger2006ALNS
  (canonical ALNS), StochasticALNSPrizeCollecting (Pisinger 2025, ALNS in prize-collecting),
  ALNSOperatorReview (Voigt 2025, operator ranking), Archetti2007MetaheuristicsTOP (TOP
  metaheuristics), Vansteenwegen2009GLSTOP (guided local search for TOP).
- **Synchronised / prize-collecting routing:** Drexl2012SurveySync (survey), Afifi2016COPTW
  (VRPTW+sync visits), TwoEchelonPCVRPSync (Sakarya 2025), AquacultureServiceVRP (Lianes 2021).
- **Lagrangian / subgradient / matheuristics:** Fisher1997VRPTW, Kohl1999LagrangeVRPTW, PolyakStepSize
  (Polyak 1969), Fisher1981Lagrangian (Lagrangian-relaxation survey), Held1974Subgradient (subgradient
  validation), ArchettiSperanza2014Matheuristic (matheuristics survey).
- **Application — observation scheduling:** Ma2025RadioTelescope (radio-telescope-array scheduling).

In-text anchors wired: §1 (telescope-scheduling application → Ma2025RadioTelescope), §2.1 (sync
variants), §3 "Broader routing and primal–dual context" (TOP metaheuristics →
Archetti2007MetaheuristicsTOP/Vansteenwegen2009GLSTOP; Lagrangian → Fisher1981Lagrangian/
Held1974Subgradient; matheuristics → ArchettiSperanza2014Matheuristic; ALNS + operator review),
§4.2 "Subgradient scheme" (Polyak). All 18 verified on Crossref; lint (cites==bibitems==refs.bib,
both .tex identical cite-sets, braces/$ balanced) passes.

**Verdict:** 18 references — inside the ~18–25 target band, a comfortable and defensible footprint for
COR across the three required axes. Phase~C (certification-in-heuristics) is left open: genuine
references are hard to source without fabrication risk, and it is non-blocking. Remaining phases below
are optional polish.

---

## 2. Forward trajectory (phased; each phase = verify → place → dual-insert → lint)

Target band: **~18–25 references** (broad but not bloated). Stop when each theme has 3–5 solid anchors.

### Phase A — Lagrangian-in-heuristics / matheuristics / primal–dual (highest value)
The dual side currently rests on 3 refs; this is the paper's core novelty axis, so it deserves depth.
Candidates to VERIFY then add (1–2 each):
- A classic subgradient/Lagrangian-bound-in-heuristics reference (e.g. Held–Wolfe–Crowder validation
  of subgradient optimization; Fisher's "Lagrangian relaxation for integer programming" survey).
- A modern **matheuristic / primal–dual heuristic** for routing that reports per-instance bounds.
- Place in §3 "Broader routing and primal–dual context" (the "Second, Lagrangian…" sentence).

### Phase B — OP/TOP metaheuristics breadth
Add 1–2 TOP/OP metaheuristic anchors beyond the survey (e.g. an ILS/tabu/GRANULAR-VNS for TOPTW),
to show command of the orienteering metaheuristic landscape. Place in §2.2 / §3.

### Phase C — Optimality certification in heuristics
The distinguishing contribution is *certification*. Add 1–2 references on heuristics that return
optimality certificates / guarantees (LP-bound-guided heuristics, certifying local search). Place in
§3 and/or the §1 positioning paragraph.

### Phase D — Telescope / observation scheduling application context
Currently the application leans solely on RieraLedesma2021SRPS. Add 1–2 observation/telescope
scheduling references (GTC/EMIR scheduling, or general astronomical observation-scheduling OR) so the
motivating domain is independently cited. Place in §1 and §2 (problem motivation).

### Phase E — Final consistency pass
- Confirm every `\cite` has a target in BOTH `thebibliography` and `refs.bib`.
- Decide issue-number policy and apply uniformly (existing entries carry `vol~(issue)`; the 5 new
  ones omit issue — harmonise or leave, but be consistent).
- Optional: weave 1–2 sentences so no reference is "orphan-cited" (cited once with no context).

---

## 3. Mechanics / where things live
- `paper/main_standalone.tex`: inline `\begin{thebibliography}{9}` block (now at the END, after the
  appendices). Add `\bibitem{key}` here.
- `paper/refs.bib`: BibTeX entries for the modular `paper/main.tex` (`\bibliographystyle{elsarticle-num}`).
- Keep keys identical across both files. Protect caps/accents in BibTeX (`{ALNS}`, `{\"O}`).
- Lint after each batch (cites vs bibitems/keys; brace/`$` balance).

## 4. Definition of done
- ~18–25 verified references, every one Crossref-confirmed.
- Each theme (SRPS/sync · OP-TOP/ALNS · Lagrangian/subgradient/certification · application) has
  ≥3 anchors.
- §2.2, §3, §4 reviews read as connected prose, not citation dumps.
- Both manuscripts compile clean on Overleaf with all citations resolved.
