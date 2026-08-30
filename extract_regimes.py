# -*- coding: utf-8 -*-
"""Extract each stopping regime from a single k=3 run.

stop_at_stall influences only the termination check, never the search, so a
k-regime execution is a strict PREFIX of a k=3 execution. The state recorded at
the first phase where the stall counter reaches k is therefore exactly what a
k-regime run returns -- and reading all regimes from one run gives a PAIRED
comparison, with no run-to-run variance between them.

Writes one CSV per regime in the same shape as a run summary, so
run_bound_refine.py --from-run can refine each against its own incumbents.

    python extract_regimes.py --run results/adaptive_full_<ts>_<tag>.csv
"""
from __future__ import annotations
import argparse, csv, io, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="k=3 run summary CSV")
    ap.add_argument("--regimes", default="1,2,3")
    cli = ap.parse_args()

    ph_path = cli.run.replace(".csv", "_phases.csv")
    if not os.path.exists(ph_path):
        sys.exit("missing phase log: %s" % ph_path)

    summary = {r["instance"]: r for r in csv.DictReader(
        io.open(cli.run, encoding="utf-8-sig"))}
    phases = {}
    for r in csv.DictReader(io.open(ph_path, encoding="utf-8-sig")):
        phases.setdefault(r["instance"], []).append(r)
    for k in phases:
        phases[k].sort(key=lambda r: int(float(r["phase"])))
    print("run: %s   instances: %d" % (os.path.basename(cli.run), len(summary)))

    for kk in [int(x) for x in cli.regimes.split(",")]:
        rows, exact, fallback = [], 0, 0
        for inst, base in sorted(summary.items()):
            ps = phases.get(inst, [])
            hit = next((p for p in ps if (f(p.get("stall_run")) or 0) >= kk), None)
            if hit is None:
                # never reached that stall level: the regime runs to completion,
                # so its result IS the full run's result
                hit = ps[-1] if ps else None
                fallback += 1
            else:
                exact += 1
            r = dict(base)
            if hit is not None:
                r["beta_obj"] = hit["obj"]
                r["beta_ub"] = hit["ub"]
                r["beta_gap_pct"] = hit["gap_pct"]
                r["beta_total_rt_s"] = hit["cumul_rt"]
                r["beta_phases"] = hit["phase"]
                r["beta_stop_reason"] = ("STALL_STOP_%d" % kk
                                         if (f(hit.get("stall_run")) or 0) >= kk
                                         else base.get("beta_stop_reason", ""))
            rows.append(r)

        dst = "results/regime_k%d_extracted.csv" % kk
        with io.open(dst, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        gaps = [f(r["beta_gap_pct"]) for r in rows if f(r["beta_gap_pct"]) is not None]
        rts = [f(r["beta_total_rt_s"]) for r in rows if f(r["beta_total_rt_s"]) is not None]
        import statistics as st
        print("  k=%d -> %s   branch fired on %d, ran to completion on %d"
              % (kk, os.path.basename(dst), exact, fallback))
        print("        mean gap %.4f%%  median rt %.0fs  mean rt %.0fs"
              % (st.mean(gaps), st.median(rts), st.mean(rts)))


if __name__ == "__main__":
    main()
