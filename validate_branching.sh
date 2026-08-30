#!/usr/bin/env bash
# Validate the branching approach on a small set.
#
# Run 1: k=3 with the stall counter logged. All three regimes are then read off
#        its phase log as prefixes.
# Run 2: k=1 executed separately on the SAME instances.
#
# Test A (logical)  : is the branch point well defined and self-consistent?
# Test B (practical): does the separate k=1 execution land near the branch
#                     prediction? Exact agreement is NOT expected -- phases are
#                     wall-clock budgeted, so two executions of the same config
#                     diverge. This measures whether that divergence is small
#                     enough for the branch to be representative.
set -u
cd "c:/Users/user/Desktop/Sapir/Full_SRPS-ALNS" || exit 1

SUBSET=results/stall_smoke4.csv
LOG=results/branch_validate.log
: > "$LOG"

echo "[val] k=3 reference run starting $(date +%H:%M)" | tee -a "$LOG"
python run_adaptive_full.py --subset "$SUBSET" --cold-start --stop-at-stall 3 \
    --tag branchref --save-suffix _branchref > results/branchref_out.txt 2>&1
echo "[val] k=3 done $(date +%H:%M)" | tee -a "$LOG"

echo "[val] k=1 separate execution starting $(date +%H:%M)" | tee -a "$LOG"
python run_adaptive_full.py --subset "$SUBSET" --cold-start --stop-at-stall 1 \
    --tag branchk1 --save-suffix _branchk1 > results/branchk1_out.txt 2>&1
echo "[val] k=1 done $(date +%H:%M)" | tee -a "$LOG"

echo "[val] complete $(date +%H:%M)" | tee -a "$LOG"
