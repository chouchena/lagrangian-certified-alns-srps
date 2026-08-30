# Cover Letter — Submission to *Computers & Operations Research*

**To:** The Editor-in-Chief, *Computers & Operations Research*

**Date:** August 2026

**Title:** An Adaptive Large Neighborhood Search with Lagrangian Certification for the Selective Routing Problem with Synchronization

**Authors:** David Chouchena, Yuval Ben-Abu
**Affiliation:** Sapir Academic Institute, D.N. Hof Ashkelon 7915600, Israel
**Corresponding author:** Yuval Ben-Abu (yuvalb@sapir.ac.il)

---

Dear Editor,

We submit for consideration the above manuscript, which we believe is well-suited for publication in *Computers & Operations Research* owing to its direct combination of a routing metaheuristic with a rigorous dual-bounding scheme — a pairing that sits squarely within COR's tradition of algorithmic contributions to combinatorial optimisation.

## What the paper does

The paper addresses the **Selective Routing Problem with Synchronization (SRPS)**, a profit-maximising routing problem in which each selected job requires a prescribed subset of processors to begin service simultaneously under a shared time horizon. SRPS arises in telescope-scheduling at the Gran Telescopio Canarias. The only published method for SRPS is an exact branch-and-price-and-cut (BPC) algorithm (Riera-Ledesma and Salazar-Gonzalez, *COR* 2021), which is the problem's defining reference.

We contribute:

1. **First certified heuristic for SRPS.** An Adaptive Large Neighborhood Search (ALNS) with a synchronisation-aware insertion operator, coupled to a Lagrangian relaxation of the joint-service coupling that produces a per-instance optimality certificate for every solution returned.
2. **In-loop bound refreshing.** A warm-started Polyak step periodically re-tightens the dual bound inside the search, sharpening certificates on the hard tail of the benchmark.
3. **Full benchmark coverage.** On the standard 660-instance SRPS benchmark the method achieves a mean certified gap of 0.066%, certifies 96.8% of instances within 0.5%, proves optimality on 446 instances, and delivers certified solutions for all 415 instances the exact BPC method leaves open or unreported. Of these, 196 have no published best-known solution. Median per-instance wall-clock time is 6.2 minutes within the same one-hour cap.

## Fit with COR

- The paper belongs to the core COR subfields of heuristic methods, vehicle routing, and primal-dual optimisation.
- It directly extends results published in *COR* (Riera-Ledesma & Salazar-Gonzalez 2021) by providing the complementary heuristic counterpart to that exact method.
- The benchmark instances are publicly available (same benchmark as the 2021 COR paper). The standalone solver, scripts, certificates, and versioned result artifacts are publicly available at <https://github.com/chouchena/lagrangian-certified-alns-srps>, made public upon submission; the repository includes a claim-level reproduction guide.

## Declarations

- This manuscript is **original work**, has not been published elsewhere, and is not currently under review at any other journal.
- All authors have approved the final version and agree to this submission.
- The authors declare **no competing interests**. This work was supported by the **Sapir Applied Science Institute, Faculty of Technology, Sapir Academic College, Israel**.
- The study is purely computational; no ethical approval or human-subjects considerations apply.

## Suggested reviewers (optional)

Suggesting reviewers is a courtesy, not a requirement of the submission
process — COR's Editorial Manager portal also offers its own optional
reviewer-suggestion step independent of this letter, and the editor is free to
select reviewers without it. We offer the following as a non-blocking
courtesy, matched to the paper's three main technical threads:

1. **Stefan Ropke**, Technical University of Denmark (DTU), Department of Management Engineering [email — not verified, do not fabricate] — expertise: adaptive large neighborhood search / destroy–repair metaheuristics for VRP and orienteering. Co-author of the cited foundational ALNS paper (`RopkePisinger2006ALNS`). Affiliation confirmed 2026-08-30 via Google Scholar (verified `dtu.dk` email domain shown on profile).
2. **Guy Desaulniers**, École Polytechnique de Montréal, Département de mathématiques et de génie industriel [email — not verified, do not fabricate] — expertise: Lagrangian relaxation and matheuristics for routing problems (column generation, branch-and-price). Affiliation confirmed 2026-08-30 via Google Scholar (verified `polymtl.ca` email domain shown on profile).
3. **Michael Drexl**, Technische Hochschule Deggendorf (Deggendorf Institute of Technology), Faculty of Applied Natural Sciences and Industrial Engineering [email — not verified, do not fabricate] — expertise: synchronised vehicle routing and team orienteering. Author of the cited Transportation Science survey of VRPs with synchronization constraints (`Drexl2012SurveySync`). Affiliation confirmed 2026-08-30 via the institution's own faculty listing (moved here from Johannes Gutenberg University Mainz, where he is cited in his 2012 paper).

<!-- Non-blocking note: since this section is optional, submission may proceed
     with it exactly as-is, with the bracketed fields simply omitted, or with
     the whole section removed. If it is kept and completed, verify each
     candidate's current affiliation, professional email, and absence of a
     conflict of interest (no shared institution, no recent co-authorship or
     collaboration with either author, not a handling/associate editor of this
     submission) have NOT been independently verified and must be confirmed by
     the authors before submission via each candidate's current faculty page,
     ORCID, or Google Scholar profile. Do not fabricate or guess an email
     address. If any candidate fails the conflict check, replace with another
     author from the same cited works or from the broader literature review. -->

We are grateful for the editors' and reviewers' time and look forward to their feedback.

Sincerely,

**Yuval Ben-Abu** (corresponding author)
Sapir Academic Institute
yuvalb@sapir.ac.il

---
*Estimated word count (body text, excluding appendices): ~7,000 words*
*Abstract: 245 words | Keywords: 6*
