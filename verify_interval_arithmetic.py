"""
Path B: Interval arithmetic verification of Lagrangian certificates.

Two verification modes:
  --mode float  : independent re-derivation using standard float64 arithmetic
                  (reproducibility / integrity check; matches production bit-for-bit)
  --mode exact  : independent re-derivation using exact Decimal conversion of every
                  float64 input (Decimal(x), not Decimal(str(x)) — no string round-trip
                  loss) and directed-rounding (ROUND_CEILING) summation. This bounds
                  the TRUE floating-point summation error rather than reproducing it.

Both modes load each instance from the raw benchmark file and recompute L(mu) from
the certificate's saved multipliers only — no dependency on cached/production objects.

Usage:
  python verify_interval_arithmetic.py                        # verify all 660, float mode
  python verify_interval_arithmetic.py --mode exact            # all 660, exact mode
  python verify_interval_arithmetic.py --smoke                 # first 10 only
  python verify_interval_arithmetic.py --stratified 3          # 3 per (family, alpha) stratum
  python verify_interval_arithmetic.py --csv                   # output results to CSV
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import pickle
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext, ROUND_CEILING, ROUND_FLOOR

# Set high precision for intermediate calculations — with profit/mu magnitudes in
# the thousands, 80 significant digits is far beyond what's needed for the exact
# decimal value of any float64 input, so summation below introduces no rounding
# error of its own; ROUND_CEILING is the directed-rounding safety net regardless.
getcontext().prec = 80

# Force UTF-8 stdout so unicode checkmarks survive redirection/piping on Windows
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from adapters.ops_adapter import OPSInstance
from core.ops_bounds import orienteering_dp_with_selection


def evaluate_lagrangian_float(inst: OPSInstance, mu: dict, eps) -> dict:
    """
    Re-derive L(mu) using standard float64 arithmetic (same operations, same
    order as production). This is a reproducibility / integrity check: it
    confirms the certificate's stored values were not corrupted or mislabeled,
    but it does not independently bound floating-point summation error (it
    will reproduce the exact same rounding behaviour production exhibited).
    """
    Kj = inst.Kj
    Jk = inst.Jk

    y_contrib = 0.0
    for j, ks in Kj.items():
        total_mu = sum((mu.get((j, k2), 0.0) for k2 in ks), 0.0)
        residual = inst.profits[j] - total_mu
        if residual > 0.0:
            y_contrib += residual

    total_ok = 0.0
    for k in range(inst.num_processors):
        mod_profits = list(inst.profits)
        for j in Jk[k]:
            mod_profits[j] = mu.get((j, k), 0.0)
        feasible_jobs = [j for j in Jk[k] if mod_profits[j] > 0.0]
        if feasible_jobs:
            ok, _ = orienteering_dp_with_selection(
                feasible_jobs, inst.T, inst.start, inst.end, mod_profits, inst.L,
            )
            total_ok += ok

    lag = y_contrib + total_ok
    eps_f = float(eps)
    return {
        "lag_value": lag,
        "ub_strict": math.floor(lag),
        "ub_with_eps": math.floor(lag + eps_f),
        "near_tie_jobs": 0,
        "boundary_processors": 0,
        "max_discrepancy": 0.0,
    }


def evaluate_lagrangian_exact(inst: OPSInstance, mu: dict, eps) -> dict:
    """
    Re-derive L(mu) using exact Decimal conversion of every float64 input
    (Decimal(x) captures the exact binary value bit-for-bit — no string
    round-trip loss) and directed-rounding (ROUND_CEILING) summation.

    y_contrib is summed in exact arithmetic directly (cheap, unambiguous).

    total_ok reuses the float64 DP's selected job subset per processor (route
    feasibility depends only on integer transition times, unaffected by
    profit precision) but re-sums that subset's exact profit total in Decimal,
    directly measuring the float64 DP's summation error rather than
    re-deriving it. Discrepancies between the exact re-sum and the DP's own
    reported total are flagged, not silently absorbed.

    Limitation: this does not re-verify the DP recurrence's internal
    subset-selection comparisons under exact arithmetic (a combinatorial,
    not floating-point-summation, concern) — only the final profit total for
    the subset the DP actually returned.
    """
    getcontext().rounding = ROUND_CEILING
    Kj = inst.Kj
    Jk = inst.Jk

    y_contrib = Decimal(0)
    near_tie_jobs = 0
    for j, ks in Kj.items():
        total_mu = sum((Decimal(mu.get((j, k2), 0.0)) for k2 in ks), Decimal(0))
        profit = Decimal(inst.profits[j])
        residual = profit - total_mu
        if 0 < abs(residual) < Decimal("1e-6"):
            near_tie_jobs += 1
        if residual > 0:
            y_contrib += residual

    total_ok = Decimal(0)
    boundary_processors = 0
    max_discrepancy = 0.0
    for k in range(inst.num_processors):
        mod_profits = list(inst.profits)
        for j in Jk[k]:
            mod_profits[j] = mu.get((j, k), 0.0)
        feasible_jobs = [j for j in Jk[k] if mod_profits[j] > 0.0]
        if feasible_jobs:
            ok_float, selected = orienteering_dp_with_selection(
                feasible_jobs, inst.T, inst.start, inst.end, mod_profits, inst.L,
            )
            exact_subset_sum = sum(
                (Decimal(mu.get((j, k), 0.0)) for j in selected), Decimal(0)
            )
            total_ok += exact_subset_sum
            discrepancy = float(exact_subset_sum) - ok_float
            if abs(discrepancy) > max_discrepancy:
                max_discrepancy = abs(discrepancy)
            if abs(discrepancy) > 1e-9:
                boundary_processors += 1

    lag = y_contrib + total_ok
    eps_dec = Decimal(str(eps))
    ub_strict = int(lag.to_integral_value(rounding=ROUND_FLOOR))
    ub_with_eps = int((lag + eps_dec).to_integral_value(rounding=ROUND_FLOOR))

    return {
        "lag_value": float(lag),
        "ub_strict": ub_strict,
        "ub_with_eps": ub_with_eps,
        "near_tie_jobs": near_tie_jobs,
        "boundary_processors": boundary_processors,
        "max_discrepancy": max_discrepancy,
    }


def verify_certificate(cert_file: str, mode: str = "float") -> dict:
    """
    Load and verify a single certificate.
    
    Returns dict with verification result and details.
    """
    try:
        with open(cert_file, "rb") as f:
            cert = pickle.load(f)
    except Exception as e:
        return {
            "instance": os.path.splitext(os.path.basename(cert_file))[0],
            "status": "LOAD_ERROR",
            "error": str(e),
        }
    
    inst_name = cert["instance"]
    final_ub = int(cert["final_ub"])
    refine_mu = cert["refine_mu"]  # Use refined multipliers (best result)
    refine_ub_float = int(cert["refine_ub"])
    eps_cert = cert["eps"]
    
    # Extract family from instance name (e.g., "B_n100_001_a25_001" -> "B")
    family = inst_name.split("_")[0]
    
    # Load the OPS instance
    try:
        bench_base = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
        ipath = os.path.join(bench_base, family, "instances", f"{inst_name}.txt")
        inst = OPSInstance.from_instance_file(ipath)
    except Exception as e:
        return {
            "instance": inst_name,
            "status": "INSTANCE_LOAD_ERROR",
            "error": f"Could not load {ipath}: {e}",
        }
    
    # Re-evaluate L(mu) independently
    try:
        evaluator = evaluate_lagrangian_exact if mode == "exact" else evaluate_lagrangian_float
        result = evaluator(inst, refine_mu, eps_cert)
    except Exception as e:
        import traceback
        return {
            "instance": inst_name,
            "status": "EVAL_ERROR",
            "error": f"{type(e).__name__}: {str(e)[:100]}",
            "traceback": traceback.format_exc()[:500],
        }
    
    # Verification logic:
    # The stored final_ub is an integer. Production's actual formula is:
    #   UB_lag = floor(L(mu) + eps),  eps = 1e-9
    # We re-derive L(mu) independently from the saved multipliers and check
    # that this SAME formula reproduces (or exceeds) the certified bound.
    #   - passes_zero_tol : floor(L(mu)) >= final_ub               (no safeguard)
    #   - passes_tol      : floor(L(mu) + eps) >= final_ub         (production formula)
    # An instance that needs the safeguard (fails zero-tol, passes with tol) is
    # not a defect — it is the exact mechanism documented in the paper's
    # numerical-safeguard appendix, now confirmed by independent re-derivation.
    
    ub_strict = int(result["ub_strict"])
    ub_with_eps = int(result["ub_with_eps"])
    
    passes_zero_tol = ub_strict >= final_ub
    passes_tol = ub_with_eps >= final_ub
    required_eps_safeguard = (not passes_zero_tol) and passes_tol
    
    delta = result["lag_value"] - refine_ub_float
    
    if passes_zero_tol:
        status = "PASS"
    elif passes_tol:
        status = "PASS_NEEDS_EPS"
    else:
        status = "FAIL"
    
    return {
        "instance": inst_name,
        "mode": mode,
        "status": status,
        "final_ub_cert": final_ub,
        "refine_ub_float": refine_ub_float,
        "ub_strict": ub_strict,
        "ub_with_eps": ub_with_eps,
        "lag_value": round(result["lag_value"], 6),
        "passes_strict": passes_zero_tol,
        "passes_tol": passes_tol,
        "required_eps_safeguard": required_eps_safeguard,
        "delta": round(delta, 6),
        "near_tie_jobs": result.get("near_tie_jobs", 0),
        "boundary_processors": result.get("boundary_processors", 0),
        "max_discrepancy": round(result.get("max_discrepancy", 0.0), 12),
    }


def stratified_sample(cert_files: list, per_stratum: int) -> list:
    """Pick `per_stratum` certificates from each (family, alpha) stratum."""
    strata = defaultdict(list)
    for c in cert_files:
        name = os.path.splitext(os.path.basename(c))[0]
        family = name.split("_")[0]
        alpha = next((p for p in name.split("_") if p.startswith("a") and p[1:].isdigit()), "?")
        strata[(family, alpha)].append(c)
    sample = []
    for key in sorted(strata):
        sample.extend(sorted(strata[key])[:per_stratum])
    return sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Verify only first 10 certificates")
    parser.add_argument("--stratified", type=int, metavar="N",
                        help="Sample N certificates per (family, alpha) stratum")
    parser.add_argument("--mode", choices=["float", "exact"], default="float",
                        help="float = reproducibility check; exact = Decimal directed-rounding check")
    parser.add_argument("--csv", action="store_true", help="Output results to CSV")
    args = parser.parse_args()
    
    cert_files = sorted(glob.glob(os.path.join(ROOT, "results", "certificates", "*.pkl")))
    
    if args.smoke:
        cert_files = cert_files[:10]
    elif args.stratified:
        cert_files = stratified_sample(cert_files, args.stratified)
    
    mode_desc = {
        "float": "float64 reproducibility (bit-for-bit re-derivation)",
        "exact": "exact Decimal + directed rounding (ROUND_CEILING/ROUND_FLOOR)",
    }[args.mode]
    
    print(f"\n{'='*72}")
    print(f"Path B: Interval Arithmetic Verification  [mode={args.mode}]")
    print(f"{'='*72}")
    print(f"Method: {mode_desc}")
    print(f"Verifying {len(cert_files)} certificate(s)...\n")
    
    t0 = time.perf_counter()
    results = []
    for i, cert_file in enumerate(cert_files):
        result = verify_certificate(cert_file, mode=args.mode)
        results.append(result)
        
        status_str = result.get("status", "?")
        if "error" in result:
            print(f"  [{i+1:3d}] {result['instance']:30s} {status_str:15s} [ERROR]")
        else:
            check_mark = "✓" if result.get("passes_strict") else ("ε" if result.get("passes_tol") else "✗")
            final_ub = result.get("final_ub_cert", "?")
            ub_s = result.get("ub_strict", "?")
            flag = ""
            if result.get("boundary_processors"):
                flag = f" [boundary x{result['boundary_processors']}]"
            print(f"  [{i+1:3d}] {result['instance']:30s} {check_mark} UB={final_ub:4d} L̄={ub_s:4d} Δ={result.get('delta', 0):+7.4f}{flag}")
        
        if (i + 1) % 10 == 0:
            print(f"        ({i+1}/{len(cert_files)} complete)")
    wall = time.perf_counter() - t0
    
    # Summary
    passed_strict = sum(1 for r in results if r.get("passes_strict"))
    needs_eps = sum(1 for r in results if r.get("required_eps_safeguard"))
    failed = sum(1 for r in results if not r.get("passes_tol") and "error" not in r)
    errors = sum(1 for r in results if "error" in r)
    all_valid = sum(1 for r in results if r.get("passes_tol"))
    boundary_total = sum(r.get("boundary_processors", 0) for r in results)
    max_disc_overall = max((r.get("max_discrepancy", 0.0) for r in results), default=0.0)
    
    print(f"\n{'='*72}")
    print(f"SUMMARY  [mode={args.mode}]")
    print(f"{'='*72}")
    print(f"  Passed with zero tolerance:      {passed_strict:3d}")
    print(f"  Passed, required eps=1e-9:       {needs_eps:3d}  (safeguard mechanism confirmed)")
    print(f"  Valid overall (production rule): {all_valid:3d}")
    print(f"  Failed (invalid even w/ eps):    {failed:3d}")
    print(f"  Errors:                          {errors:3d}")
    print(f"  Total:                           {len(results):3d}")
    if args.mode == "exact":
        print(f"  Processor-level discrepancies:   {boundary_total:3d}  (float64 DP total vs exact re-sum, >1e-9)")
        print(f"  Max discrepancy observed:        {max_disc_overall:.2e}")
    print(f"  Wall clock:                      {wall:.2f}s  ({wall/max(len(results),1)*1000:.1f} ms/instance)")
    if len(results) > 0:
        proj_660 = wall / len(results) * 660
        print(f"  Projected time for all 660:      {proj_660:.1f}s")
    
    if failed > 0 or errors > 0:
        print(f"\n  [!] VERIFICATION INCOMPLETE")
        # Print first error for debugging
        for r in results:
            if "error" in r:
                print(f"\n  First error ({r['instance']}):")
                print(f"    {r.get('error', 'unknown')}")
                if "traceback" in r:
                    print(f"    Traceback: {r.get('traceback', '')[:300]}")
                break
        for r in results:
            if not r.get("passes_tol") and "error" not in r:
                print(f"\n  First real failure ({r['instance']}):")
                print(f"    final_ub={r.get('final_ub_cert')}  recomputed L(mu)={r.get('lag_value')}")
                break
    else:
        print(f"\n  [OK] All {len(results)} certificates independently re-derived and valid")
        print(f"       under production's UB_lag = floor(L(mu) + 1e-9) rule.")
    
    if args.csv:
        suffix = "_exact" if args.mode == "exact" else ""
        csv_path = os.path.join(ROOT, "results", "analysis", f"path_b_verification{suffix}.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
        print(f"\n  Results saved to: {csv_path}")
    
    print()


if __name__ == "__main__":
    main()
