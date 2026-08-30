#!/usr/bin/env bash
# Regime comparison on the 30-instance stratified hard-tail sample.
#
# Three stopping regimes, each run cold and end-to-end, then refined against
# ITS OWN incumbents. Running them rather than replaying them is what removes
# the composition problem: every (gap, runtime) pair comes out of one execution.
#
# The in-loop dual budget is left at its default (200 iters / 60 s) throughout,
# so k is the only variable. Refinement runs offline at 3000 iterations.
set -u
cd "c:/Users/user/Desktop/Sapir/Full_SRPS-ALNS" || exit 1

SUBSET=results/regime_sample30.csv
LOG=results/regime_chain.log
: > "$LOG"

for K in 3 2 1; do
    echo "[chain] k=$K search starting $(date +%H:%M)" | tee -a "$LOG"
    python run_adaptive_full.py \
        --subset "$SUBSET" --cold-start --stop-at-stall "$K" \
        --tag "regime_k$K" --save-suffix "_regime_k$K" \
        > "results/regime_k${K}_out.txt" 2>&1
    echo "[chain] k=$K search done $(date +%H:%M)" | tee -a "$LOG"

    RUN=$(ls -t results/adaptive_full_*regime_k${K}.csv 2>/dev/null | grep -v _phases | head -1)
    if [ -z "$RUN" ]; then
        echo "[chain] k=$K produced no run CSV -- aborting" | tee -a "$LOG"
        exit 2
    fi
    echo "[chain] k=$K refining from $RUN" | tee -a "$LOG"
    python run_bound_refine.py --from-run "$RUN" --iters 3000 --max-time 600 --workers 6 \
        > "results/regime_k${K}_refine.txt" 2>&1
    echo "[chain] k=$K refine done $(date +%H:%M)" | tee -a "$LOG"
done

echo "[chain] all regimes complete $(date +%H:%M)" | tee -a "$LOG"
