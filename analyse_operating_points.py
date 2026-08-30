# -*- coding: utf-8 -*-
"""Reproduce the supplementary runtime/quality operating-point table.

Replays the recorded phase trajectories under stopping rules, then adds the
measured refinement cost. Truncation is read from recorded state, not
simulated. Refinement bounds were computed with the FINAL incumbent, so where
truncation lowers z the reported gap here is slightly optimistic; that set is
counted and reported rather than hidden.

Usage:
    python analyse_operating_points.py
    python analyse_operating_points.py --phase-log archive/results_interim/adaptive_full_20260619_0917_phases.csv
"""
import argparse
import csv
import sys, io, os, statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
S = {"B", "C", "D", "EB", "EC", "ED"}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-log", default=os.path.join(
        "archive", "results_interim", "adaptive_full_20260619_0917_phases.csv"))
    parser.add_argument("--master", default=os.path.join("results", "adaptive_master.csv"))
    parser.add_argument("--refinement", default=os.path.join("results", "bound_refine_corrected.csv"))
    parser.add_argument("--refined-master", default=os.path.join("results", "adaptive_master_refined.csv"),
                        help="Supplies corrected final bounds for rows absent from the refinement file.")
    parser.add_argument("--out", default=os.path.join("results", "analysis", "operating_points.txt"))
    return parser.parse_args()


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def stop_index(ps, k):
    """index of the phase at which the k-th consecutive stall occurs."""
    run = 0
    for i, p in enumerate(ps):
        ev = p.get("event") or ""
        if "OBJ+" in ev:
            run = 0
            continue
        if ("STALL" in ev) or ("TIERS" in ev) or ("UB_TIGHT" in ev):
            run += 1
            if run >= k:
                return i
    return None


def evaluate(rule, am, ref, refined, by, frozen_bound):
    gaps, rts, zlost, dz = [], [], 0, []
    for inst, r in am.items():
        z_fin = f(r["alns_obj"])
        t_full = f(r["alns_runtime_s"]) or 0.0
        ps = by.get(inst, [])
        z, t = z_fin, t_full
        ub_at_stop = None
        if rule and ps:
            i = stop_index(ps, rule)
            if i is not None and i < len(ps) - 1:
                z_at = f(ps[i]["obj"])
                t = f(ps[i]["cumul_rt"]) or t_full
                # the bound the truncated run actually held: the in-loop
                # re-bound fires on stalls, so stopping early keeps a looser
                # bound. Taking the completed run's bound here would charge
                # truncation for its primal cost while crediting it a
                # certificate it never earned.
                ub_at_stop = f(ps[i]["ub"])
                if z_at is not None and z_fin is not None and z_at < z_fin - 1e-9:
                    zlost += 1
                    dz.append(z_fin - z_at)
                    z = z_at
        # bound: refined where available
        if inst in ref:
            # lag_ub is the refinement's own value; new_ub is already min'd
            # with the COMPLETED run's bound, which a truncated run never had
            ub = f(ref[inst]["lag_ub"]) if not frozen_bound else f(ref[inst]["new_ub"])
            t += f(ref[inst]["refine_s"]) or 0.0
        elif inst in refined:
            # The four corrected flooring rows have no raw refinement row.
            # Their corrected final bound is versioned in the refined master.
            ub = f(refined[inst]["best_ub"])
        else:
            ub = f(r["best_ub"])
        if ub_at_stop is not None and not frozen_bound:
            # still generous: refinement was computed against the FINAL
            # incumbent, which this run would not hold
            ub = min(ub, ub_at_stop) if ub else ub_at_stop
        gaps.append(max(0.0, (ub - z) / ub * 100) if ub else 0.0)
        rts.append(t)
    return gaps, rts, zlost, dz

def main():
    args = parse_args()
    for path in (args.phase_log, args.master, args.refinement, args.refined_master):
        if not os.path.exists(path):
            raise SystemExit(f"missing required input: {path}")
    am = {r["instance"]: r for r in csv.DictReader(
        io.open(args.master, encoding="utf-8-sig")) if r["family"] in S}
    ref = {r["instance"]: r for r in csv.DictReader(io.open(args.refinement, encoding="utf-8-sig"))}
    refined = {r["instance"]: r for r in csv.DictReader(io.open(args.refined_master, encoding="utf-8-sig"))}
    by = defaultdict(list)
    for row in csv.DictReader(io.open(args.phase_log, encoding="utf-8-sig")):
        by[row["instance"]].append(row)
    for rows in by.values():
        rows.sort(key=lambda row: int(float(row["phase"])))

    frozen_bound = "--frozen-bound" in sys.argv
    lines = ["%-26s %10s %10s %10s %9s %8s" %
             ("operating point", "mean gap", "median", "closed", "mean rt", "max rt")]
    for label, rule in (("full search (used)", None),
                        ("stop at 2nd stall", 2),
                        ("stop at 1st stall", 1)):
        g, t, zl, dz = evaluate(rule, am, ref, refined, by, frozen_bound)
        lines.append("%-22s mean %.4f%%  med %.4f%%  max %.4f%%  closed %d  w0.5 %.1f%%"
                     % (label, st.mean(g), st.median(g), max(g),
                        sum(1 for x in g if x < 1e-12),
                        100 * sum(1 for x in g if x <= 0.5) / len(g)))
        lines.append("%-22s rt: med %.1fm mean %.1fm max %.1fm | z lost %d, total %d units, worst %d"
                     % ("", st.median(t) / 60, st.mean(t) / 60, max(t) / 60,
                        zl, int(sum(dz)) if dz else 0, int(max(dz)) if dz else 0))
    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text, end="")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
