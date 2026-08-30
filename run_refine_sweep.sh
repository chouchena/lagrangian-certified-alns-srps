#!/usr/bin/env bash
# Refinement iteration-cap sensitivity: same 60 instances at 1000 and 5000
# iterations, for comparison against the 3000-iteration production run.
# run_bound_refine.py orders tasks by published gap descending, so --limit 60
# selects the identical instance set at every setting.
set -u
cd "c:/Users/user/Desktop/Sapir/Full_SRPS-ALNS" || exit 1

for IT in 1000 5000; do
    echo "[sweep] iters=$IT starting at $(date +%H:%M)"
    python run_bound_refine.py --iters "$IT" --max-time 1200 --limit 60 --workers 6 \
        > "results/refine_sweep_${IT}.txt" 2>&1
    echo "[sweep] iters=$IT finished at $(date +%H:%M)"
done
echo "[sweep] complete"
