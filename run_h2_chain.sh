#!/usr/bin/env bash
# Wait for the in-flight hard-tail H2 arm to finish, then run the remaining
# 332 instances that invoked the in-loop re-bound. Sequential by design: both
# arms need the same six workers, and runtime is one of the measured outcomes.
set -u

cd "c:/Users/user/Desktop/Sapir/Full_SRPS-ALNS" || exit 1

TAIL_CSV=$(ls -t results/adaptive_full_*hardtail_H2.csv 2>/dev/null | head -1)
echo "[chain] waiting on: $TAIL_CSV"

# poll until 70 data rows land, or 4 h elapse (guard against a hung run)
deadline=$(( $(date +%s) + 14400 ))
while :; do
    rows=$(( $(wc -l < "$TAIL_CSV" 2>/dev/null || echo 1) - 1 ))
    [ "$rows" -ge 70 ] && { echo "[chain] tail complete: $rows rows"; break; }
    [ "$(date +%s)" -ge "$deadline" ] && { echo "[chain] TIMEOUT at $rows rows"; exit 2; }
    sleep 60
done

echo "[chain] launching remainder (332 instances) at $(date +%H:%M)"
python run_adaptive_full.py \
    --subset results/rebound_remainder.csv \
    --lag-max-iter 1000 --lag-max-time 300 \
    --tag rebound_H2 --save-suffix _rebound_H2 \
    > results/rebound_H2_console.txt 2>&1

echo "[chain] remainder finished at $(date +%H:%M)"
