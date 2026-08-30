# -*- coding: utf-8 -*-
"""Stratified 30-instance sample from the hard tail, for the regime comparison.

The stopping rule can only bite on instances that stall, so the sample is drawn
from the 70 tier-exhausted instances. Within those it is stratified by family
and then by certified gap, so the sample spans the difficulty range rather than
clustering on the loosest instances.

Writes results/regime_sample30.csv with an instance_id column, which
run_adaptive_full.py accepts via --subset.
"""
import csv, io, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
TARGET = 30


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


am = {r["instance"]: r for r in csv.DictReader(
    io.open("results/adaptive_master.csv", encoding="utf-8-sig"))}
tail = [r["instance_id"] for r in csv.DictReader(
    io.open("results/hard_tail_70.csv", encoding="utf-8-sig"))]
tail = [i for i in tail if i in am]
print("hard-tail pool: %d" % len(tail))

byfam = defaultdict(list)
for i in tail:
    byfam[am[i]["family"]].append(i)
for fam in byfam:
    byfam[fam].sort(key=lambda i: -(f(am[i]["final_cert_gap_pct"]) or 0))

# proportional allocation, at least one per represented family
alloc, chosen = {}, []
for fam, lst in sorted(byfam.items()):
    alloc[fam] = max(1, round(TARGET * len(lst) / len(tail)))
while sum(alloc.values()) > TARGET:
    fam = max(alloc, key=lambda k: alloc[k])
    alloc[fam] -= 1
while sum(alloc.values()) < TARGET:
    fam = max(alloc, key=lambda k: len(byfam[k]) - alloc[k])
    alloc[fam] += 1

# within a family, spread across the gap range rather than taking the top n
for fam, k in sorted(alloc.items()):
    lst = byfam[fam]
    if k >= len(lst):
        pick = lst
    else:
        idx = [round(j * (len(lst) - 1) / (k - 1)) if k > 1 else 0 for j in range(k)]
        pick = [lst[j] for j in sorted(set(idx))]
        j = 0
        while len(pick) < k and j < len(lst):
            if lst[j] not in pick:
                pick.append(lst[j])
            j += 1
    chosen.extend(pick)
    gaps = [f(am[i]["final_cert_gap_pct"]) for i in pick]
    print("  %-3s %2d of %2d   gap %.3f%%..%.3f%%" % (fam, len(pick), len(lst),
                                                      min(gaps), max(gaps)))

chosen = sorted(set(chosen))[:TARGET]
with io.open("results/regime_sample30.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["instance_id"])
    for i in chosen:
        w.writerow([i])

g = [f(am[i]["final_cert_gap_pct"]) for i in chosen]
rt = [f(am[i]["alns_runtime_s"]) for i in chosen]
import statistics as st
print("\nselected %d instances" % len(chosen))
print("  certified gap : %.3f%% .. %.3f%%   (mean %.3f%%)" % (min(g), max(g), st.mean(g)))
print("  canonical rt  : serial %.1f h  -> %.1f h at 6 workers"
      % (sum(rt) / 3600, sum(rt) / 3600 / 6))
print("wrote results/regime_sample30.csv")
