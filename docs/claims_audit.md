# Claims audit — 2026-08-26

Every checkable numeric claim, verified against the data. Certificate claims
against adaptive_master_refined.csv; primal claims against adaptive_master.csv
(refinement does not touch incumbents).

```
claim                                           paper         data
--------------------------------------------------------------------
OK       mean certified gap %                   0.066       0.0657
OK       median certified gap %                   0.0       0.0000
OK       max certified gap %                    1.613       1.6135
OK       within 0.5%                             96.8      96.8182
OK       within 2%                              100.0     100.0000
OK       proven optimal count                     446          446
OK       proven optimal %                        67.6      67.5758
OK       median runtime (min)                     6.2       6.1700
OK       max runtime (min)                       46.9      46.8950
OK       tier exact                               446          446
OK       tier <=0.5%                              193          193
OK       tier 0.5-1%                               12           12
OK       tier 1-2%                                  9            9
OK       proven-opt also proved by BPC            220          220
OK       proven-opt by Lagrangian alone           226          226
OK       improved incumbents                       24           24
  (matched 425, below 12, with BKS 461)
  instances with no published BKS: 199
OK       max |J_k| over study set                  13           13
--------------------------------------------------------------------
mismatches: 0

group sizes: optimal=245, incumbent=115, not_reported=300

A optimal      n=245   improve   0   match 241   below   4   no BKS   0
B incumbent    n=115   improve  15   match  93   below   4   no BKS   3
C not_reported n=300   improve   9   match  91   below   4   no BKS 196

PAPER CLAIMS vs DATA
  A: recover optimum 241 / miss 4        -> data match 241, below 4
  B: improve 15 / match 93 / below 4     -> data improve 15, match 93, below 4
  C: 300 instances, 196 first-ever       -> data n=300, no BKS 196
  C with BKS: 9 improve / 91 match / 4 below -> data 9 / 91 / 4

  'all 415 instances the exact method fails to close' -> data 415
  '98.4% reproduces the proven optimum' -> data 98.4% (241/245)
```
