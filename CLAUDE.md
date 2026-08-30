# SRPS-ALNS — working notes for Claude
<!-- To resume a crashed session: read SESSION.md in this directory. -->

## Long-run standard (any run > 3 min)

Before launching any experiment with expected wall-clock > 3 minutes:

1. **Incremental CSV writes** — flush every row immediately; never batch at end.
2. **Phase 1 checkpoint** — save setup output to JSON after every item; support `--resume`.
3. **Sleep prevention** — `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` at entry.
4. **External window** — launch outside VS Code terminal:
   ```powershell
   Start-Process powershell -ArgumentList '-NoExit -Command "cd ''<dir>''; python <script> *>&1 | Tee-Object results\<name>.log"'
   ```
5. **Provenance block** — embed git commit, dirty flag, argv, python, machine, start time. Abort if source dirty.

Monitor at any time: `python monitor_runs.py`

Certified primal–dual method for the Selective Routing Problem with
Synchronization. An ALNS supplies incumbents; a Lagrangian relaxation of the
joint-service coupling supplies valid per-instance upper bounds. The
deliverable is a manuscript for *Computers & Operations Research*.

## Status, stated plainly

**Nothing here is published.** The manuscript has not been submitted. Never
describe our own results, tables, or figures as "published" — in the manuscript
that word is reserved for Riera-Ledesma & Salazar-González's BPC results and for
external best-known values. Say "reported", "current draft", or "our results".

`github.com/chouchena/srps-alns` is **private**, while `main.tex` prints that
URL in its data-availability statement. Resolve before submission.

## Verify before asserting

Run the checks in `checks/` rather than recomputing ad hoc:

    python checks/check_paper.py           # structural lint (no LaTeX here)
    python checks/check_claims.py          # every headline number vs the data
    python checks/check_bound_validity.py  # falsification tests on the bounds

Each exits non-zero on failure. `check_claims.py` exists because the same
column trap produced wrong figures twice — see below.

## Data traps that have actually bitten

**Column choice.** Use `alns_obj` and `alns_runtime_s`. The `master_*` columns
belong to an earlier campaign and are *not* this method's output. Using
`master_obj` gave 0.147% for a 0.133% result; `master_rt_s` gave a 91.4-minute
maximum under a 60-minute cap.

**Study set.** 660 instances = all families **except A and EA** (the |K_j|=1
cases). The master CSV holds 780 rows.

**Gap columns.** `baseline_cert_gap_pct` is *before* refinement,
`final_cert_gap_pct` is *after* — the latter is the headline series. The
robustness studies (ablation, sensitivity, hard-tail, Tobit) deliberately use
the pre-refinement certificates, which is why their baselines (0.148%, 0.153%)
sit above the headline 0.066%.

**Pre-refinement proven count is 280, not 284.** Four instances carried invalid
bounds from the flooring defect and were falsely proven optimal;
`baseline_cert_gap_pct` still records them as zero. 280 + 166 new proofs = 446.
Filter on `refined_source != "reverified"`.

**Falsy-zero idiom.** Never write `(x or 1)` on a gap — a legitimate `0.0`
becomes `1`. Use explicit `is not None`.

## Campaign settings — fixed

**6 workers for every run in this campaign** (`N_WORKERS = 6`, already the
default). Do not vary it: runtime figures are only comparable across
experiments if contention is held constant, and phase budgets are wall-clock,
so worker count directly affects how many ALNS iterations fit in a phase.
Changing it mid-campaign would make the ablation and sensitivity arms
incomparable with the main run.

## Agents

`.claude/agents/manuscript-adversary.md` is a cold-start adversarial reviewer.
Claude Code registers agent definitions **at session start**, so a file added
mid-session is not callable until the next session; until then, run its brief
through `general-purpose`. Invoke it explicitly — it never fires on its own.

## Code

`run_adaptive_full.py` is **frozen**: one code version for every run. Do not
edit it mid-campaign. `--stop-at-stall`, `--cold-start`, `--lag-max-iter`,
`--lag-max-time` are inert at defaults.

Warm start reads previously saved incumbents. A run warm-started from a
completed campaign holds its final solution from the outset, so it **cannot**
measure the primal cost of stopping early. Use `--cold-start` for anything that
claims a truncation cost.

Regimes need not be re-run: stall tolerance affects only the termination test,
so a κ-regime run is a strict prefix of a longer one. Validated — branched
prediction vs separate execution matched objectives 4/4 exactly. The replay in
`analyse_operating_points.py` reads the `event` string, which matches the
solver's own counter 30/30. Do **not** reconstruct the counter by differencing
objectives: that is blind to a phase-1 warm-start stall.

## Paper

Single source: `paper/main.tex` (+ `refs.bib`, `figures/`).
`main_standalone.tex` was retired — a hand-maintained twin that drifted and
silently lost five `\bibitem` entries.

MiKTeX 25.12 is installed at `%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64`
(prepend to PATH). Build: `pdflatex` → `bibtex main` → `pdflatex` ×2. Current
state compiles clean — 46 pages, 0 undefined citations or references.
`paper_overleaf.zip` is the Overleaf bundle (`main.tex`, `refs.bib`,
`figures/`).

Algorithm 1 uses a custom `breakablealgorithm` environment, not `algorithm`: at
~70 lines it is about two pages, so as a float it could never be placed
("Float too large for page by 518pt"). Do not convert it back.

`checks/check_paper.py` catches structural errors without a compile, but only a
real compile sees overfull boxes and float placement.

κ is the stall tolerance (Algorithm 1). Algorithm 2 uses `m` for its placement
count — these collided once.

## Environment

Windows, PowerShell primary. **Write scripts with the Write tool, not bash
heredocs** — heredocs mangle backslashes, turning `\ref` into a carriage return
and `\t` into a tab. This has broken edits and analysis scripts repeatedly.

Console is cp1252; set `PYTHONIOENCODING=utf-8` before printing non-ASCII.
CSVs written by PowerShell carry a BOM — read with `utf-8-sig`.
