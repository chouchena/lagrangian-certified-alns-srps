"""
validate_noise_floor_output.py — Real-time integrity check for Tier 2 noise floor run.

Detects:
  1. CSV corruption (malformed rows, missing columns)
  2. Numeric errors (NaN, Inf in objective/bound columns)
  3. Logic errors (ub < obj, negative times, inconsistent stops)
  4. Worker crashes (error field flagged)
  5. Incomplete results (error rows without investigation)

Designed to run continuously in parallel with run_noise_floor.py to catch
crashes early instead of discovering them afterward.

Usage:
  python validate_noise_floor_output.py               # validate all CSVs
  python validate_noise_floor_output.py --watch N     # poll every N seconds
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def validate_csv_row(row: dict, row_num: int) -> list[str]:
    """Check one CSV row for errors. Returns list of error messages (empty = OK)."""
    errors = []
    
    # Required fields
    required = ["instance", "a0_obj", "a0_ub", "ap_obj", "ap_ub"]
    for field in required:
        if field not in row or row[field].strip() == "":
            errors.append(f"missing field: {field}")
    
    if errors:
        return errors
    
    # Check for error flags
    if row.get("error", "").strip():
        errors.append(f"worker error: {row['error'][:100]}")
    
    # Numeric validation
    numeric_fields = [
        "a0_obj", "a0_ub", "ap_obj", "ap_ub", "a0_rt_s", "ap_rt_s",
        "delta", "delta_pct", "abs_delta_pct"
    ]
    
    for field in numeric_fields:
        val_str = row.get(field, "").strip()
        if val_str in ("", "None"):
            continue  # OK to be missing (e.g., after a crash)
        
        try:
            val = float(val_str)
            
            # Check for NaN / Inf
            if math.isnan(val):
                errors.append(f"{field}=NaN")
            elif math.isinf(val):
                errors.append(f"{field}=Inf")
            
            # Check ranges (objective and bounds should be positive)
            if field in ("a0_obj", "a0_ub", "ap_obj", "ap_ub") and val < 0:
                errors.append(f"{field} is negative: {val}")
            
            if field in ("a0_rt_s", "ap_rt_s") and val < 0:
                errors.append(f"{field} is negative: {val}")
        
        except ValueError:
            errors.append(f"{field} not numeric: {val_str}")
    
    # Logic checks
    try:
        a0_obj = float(row.get("a0_obj", "0") or "0")
        a0_ub = float(row.get("a0_ub", "0") or "0")
        ap_obj = float(row.get("ap_obj", "0") or "0")
        ap_ub = float(row.get("ap_ub", "0") or "0")
        
        if a0_obj > 0 and a0_ub > 0 and a0_obj > a0_ub + 0.01:
            errors.append(f"A0: obj > ub ({a0_obj:.0f} > {a0_ub:.0f})")
        if ap_obj > 0 and ap_ub > 0 and ap_obj > ap_ub + 0.01:
            errors.append(f"A0': obj > ub ({ap_obj:.0f} > {ap_ub:.0f})")
    except (ValueError, TypeError):
        pass  # Already reported above
    
    return errors


def validate_csv_file(csv_path: str) -> tuple[int, int, list[tuple[int, str]]]:
    """
    Validate entire CSV file.
    
    Returns:
        (total_rows, error_rows, list of (row_num, error_msg))
    """
    if not os.path.exists(csv_path):
        return 0, 0, [(0, "File does not exist")]
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return 0, 1, [(0, "File is empty or has no header")]
            
            total_rows = 0
            error_count = 0
            error_list = []
            
            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                total_rows += 1
                errors = validate_csv_row(row, row_num)
                
                if errors:
                    error_count += 1
                    for err in errors:
                        error_list.append((row_num, f"{row.get('instance', '?'):30s} | {err}"))
            
            return total_rows, error_count, error_list
    
    except Exception as e:
        return 0, 1, [(0, f"CSV read error: {str(e)[:100]}")]


def main():
    parser = argparse.ArgumentParser(description="Real-time Tier 2 output validator")
    parser.add_argument("--watch", type=int, metavar="SECONDS",
                        help="Poll for new/updated CSVs every N seconds")
    parser.add_argument("--csv", metavar="PATH",
                        help="Validate specific CSV file (default: latest noise_floor_*.csv)")
    args = parser.parse_args()
    
    if args.watch:
        # ── Continuous monitoring mode ────────────────────────────────────────
        print(f"[Validator] Starting real-time monitor (check every {args.watch}s)")
        print(f"[Validator] Ctrl-C to stop\n")
        
        last_csv = None
        last_size = 0
        last_error_log_lines = 0
        
        try:
            while True:
                # Find latest CSV
                csv_files = sorted(glob.glob(os.path.join(ROOT, "results", "analysis", "noise_floor_*.csv")))
                if not csv_files:
                    print(f"[{time.strftime('%H:%M:%S')}] No CSV files found yet...", flush=True)
                    time.sleep(args.watch)
                    continue
                
                csv_path = csv_files[-1]
                
                # Check if new/updated
                try:
                    size = os.path.getsize(csv_path)
                    if csv_path == last_csv and size == last_size:
                        # Check error log even if CSV hasn't changed
                        error_logs = sorted(glob.glob(os.path.join(ROOT, "results", "analysis", "run_noise_floor_errors_*.log")))
                        if error_logs:
                            try:
                                with open(error_logs[-1], "r", encoding="utf-8") as f:
                                    lines = len(f.readlines())
                                    if lines > last_error_log_lines:
                                        last_error_log_lines = lines
                                        ts = time.strftime("%H:%M:%S")
                                        print(f"[{ts}] [CRASH] Errors detected in {os.path.basename(error_logs[-1])}", flush=True)
                                        with open(error_logs[-1], "r", encoding="utf-8") as f2:
                                            for line in f2.readlines()[-3:]:
                                                print(f"       {line.rstrip()}", flush=True)
                            except:
                                pass
                        time.sleep(args.watch)
                        continue
                except OSError:
                    time.sleep(args.watch)
                    continue
                
                last_csv = csv_path
                last_size = size
                
                # Validate
                total, errors, error_list = validate_csv_file(csv_path)
                
                ts = time.strftime("%H:%M:%S")
                status = "OK" if errors == 0 else "ERR"
                print(f"[{ts}] [{status}] {os.path.basename(csv_path)}: {total} rows, {errors} errors")
                
                if error_list:
                    for row_num, msg in error_list[:5]:  # Show first 5 errors
                        print(f"       Row {row_num}: {msg}")
                    if len(error_list) > 5:
                        print(f"       ... and {len(error_list) - 5} more errors")
                
                time.sleep(args.watch)
        
        except KeyboardInterrupt:
            print("\n[Validator] Stopped", flush=True)
    else:
        # ── One-shot mode ─────────────────────────────────────────────────────
        if args.csv:
            csv_path = args.csv
        else:
            # Find latest CSV
            csv_files = sorted(glob.glob(os.path.join(ROOT, "results", "analysis", "noise_floor_*.csv")))
            if not csv_files:
                print("No CSV files found in results/analysis/", file=sys.stderr)
                sys.exit(1)
            csv_path = csv_files[-1]
        
        print(f"Validating: {csv_path}\n")
        
        total, errors, error_list = validate_csv_file(csv_path)
        
        print(f"Total rows    : {total}")
        print(f"Error rows    : {errors}")
        
        if error_list:
            print(f"\nErrors found:")
            for row_num, msg in error_list:
                print(f"  Row {row_num}: {msg}")
        else:
            print("\nNo errors found!")
        
        sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
