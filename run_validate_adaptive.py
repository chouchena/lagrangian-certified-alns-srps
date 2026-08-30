"""
run_validate_adaptive.py — Postmortem sanity check for adaptive full run.

Loads every PKL incumbent from results/beta_incumbents/, independently
validates each solution (7 checks: route bookends, job membership,
route↔selected consistency, acyclicity, schedule feasibility, obj recomputation),
and cross-checks the claimed obj from the adaptive CSV.

Must pass 100% before any result is inserted into the master file.

Usage:
    python run_validate_adaptive.py
    python run_validate_adaptive.py --csv results/adaptive_full_20260619_0917.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from adapters.ops_adapter import OPSInstance, OPSSolution
from validators.validate_ops_solution import validate

BENCH          = os.path.join("benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
INCUMBENTS_DIR = os.path.join("results", "beta_incumbents")
MASTER_CSV     = os.path.join("results", "master_results.csv")
STUDY_FAMILIES = {"B", "C", "D", "EB", "EC", "ED"}


def _instance_path(family: str, label: str) -> str:
    return os.path.join(BENCH, family, "instances", label + ".txt")


def _load_pkl(label: str, inst: OPSInstance):
    path = os.path.join(INCUMBENTS_DIR, label + ".pkl")
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = pickle.load(f)
    sol = OPSSolution(inst)
    sol.routes   = [list(r) for r in data["routes"]]
    sol.selected = set(data["selected"])
    return sol, sol.objective()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None,
                        help="Adaptive run CSV to cross-check claimed objectives")
    args = parser.parse_args()

    # Load family map from master CSV
    family_map = {}
    with open(MASTER_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["family"].strip() in STUDY_FAMILIES:
                family_map[r["instance"].strip()] = r["family"].strip()

    # Load claimed objectives from adaptive CSV if provided
    claimed = {}
    if args.csv and os.path.exists(args.csv):
        with open(args.csv, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                obj = r.get("beta_obj", "").strip()
                if obj:
                    claimed[r["instance"].strip()] = float(obj)

    # Find all PKLs
    if not os.path.isdir(INCUMBENTS_DIR):
        print("ERROR: incumbents dir not found:", INCUMBENTS_DIR)
        sys.exit(1)

    pkls = sorted(f[:-4] for f in os.listdir(INCUMBENTS_DIR) if f.endswith(".pkl"))
    study_pkls = [p for p in pkls if p in family_map]

    print("=" * 70)
    print(f"Adaptive run postmortem validation")
    print(f"PKLs found  : {len(pkls)}  |  in study set: {len(study_pkls)}")
    if args.csv:
        print(f"Cross-check : {args.csv}  ({len(claimed)} claimed objectives)")
    print("=" * 70)
    print()

    passed = failed = skipped = 0
    failures = []
    t0 = time.time()

    for label in study_pkls:
        family = family_map[label]
        inst_path = _instance_path(family, label)
        if not os.path.exists(inst_path):
            print(f"  SKIP  {label}  (instance file not found)")
            skipped += 1
            continue

        try:
            inst = OPSInstance.from_instance_file(inst_path)
            sol, recomputed_obj = _load_pkl(label, inst)

            if sol is None:
                print(f"  SKIP  {label}  (PKL missing)")
                skipped += 1
                continue

            # Cross-check claimed obj from CSV
            if label in claimed:
                csv_obj = claimed[label]
                if abs(csv_obj - recomputed_obj) > 0.5:
                    failures.append((label, f"CSV obj {csv_obj} != PKL obj {recomputed_obj}"))
                    print(f"  FAIL  {label}  CSV/PKL obj mismatch: {csv_obj} vs {recomputed_obj}")
                    failed += 1
                    continue

            # Full 7-check validation
            validate(inst, sol, claimed_obj=recomputed_obj)
            passed += 1
            if passed % 50 == 0:
                print(f"  ... {passed} passed so far ({time.time()-t0:.0f}s)")

        except AssertionError as e:
            failures.append((label, str(e)))
            print(f"  FAIL  {label}  {e}")
            failed += 1
        except Exception as e:
            failures.append((label, f"EXCEPTION: {e}"))
            print(f"  ERROR {label}  {e}")
            failed += 1

    elapsed = time.time() - t0
    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed  |  {failed} failed  |  {skipped} skipped")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * 70)

    if failures:
        print()
        print("FAILURES:")
        for label, msg in failures:
            print(f"  {label}: {msg}")
        print()
        print("VALIDATION FAILED — do not insert results into master file.")
        sys.exit(1)
    else:
        print()
        print("ALL SOLUTIONS VALID — safe to proceed with master file insertion.")
        sys.exit(0)


if __name__ == "__main__":
    main()
