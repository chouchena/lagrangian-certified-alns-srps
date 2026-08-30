# -*- coding: utf-8 -*-
"""Rebuild every reported bound with no external value, and persist its certificate.

Three defects are fixed in one pass over all 660 study instances.

1. PROVENANCE. The initial bounds in results/master_results.csv were produced
   with the published BKS as the subgradient's Polyak reference
   (archive/run_scripts/run_ops_bounds.py:186-187). Here the reference is the
   greedy construction value -- what a run with no external information
   actually holds at that point. Nothing external enters the bound chain.

2. CERTIFICATES. run_bound_refine.py kept only `upper_bound` and discarded
   `best_mu`, so 166 of the 446 optimality proofs could not be re-derived as
   reported. Every solve here writes its multipliers to
   results/certificates/<instance>.pkl, so any bound can be re-verified
   offline without repeating the search.

3. DETERMINISM. Refinement carried a 600 s wall-clock cap that four instances
   hit, making their bounds machine-dependent. Iteration cap only.

The reported bound is min(initial, refined). In-loop re-bounds are deliberately
excluded: they were computed against our own incumbent and so are BKS-free, but
omitting them can only make the reported bound LOOSER, which is the
conservative direction. A looser bound would also have made the search run
longer, never shorter, so the incumbents remain attainable.

    python rebuild_bounds_certified.py --iters 3000 --workers 6
"""
from __future__ import annotations
import argparse, csv, io, math, os, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adapters.ops_adapter import OPSInstance, OPSSolution   # noqa: E402
from core.ops_bounds import lagrangian_bound                # noqa: E402
from run_adaptive_full import _repair_profit                # noqa: E402

BENCH = os.path.join(ROOT, "benchmarks", "ops_raw", "OPS-Benchmark-master", "input")
CERTS = os.path.join(ROOT, "results", "certificates")
EXCLUDED = ("A", "EA")
EPS = 1e-9          # flooring tolerance; see Appendix A


def f(row, key):
    v = row.get(key)
    if v in (None, "", "None", "?", "NA"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def one(task):
    label, family, obj, init_iters, ref_iters = task
    path = os.path.join(BENCH, family, "instances", label + ".txt")
    if not os.path.exists(path):
        return {"instance": label, "error": "missing instance file"}
    t0 = time.perf_counter()
    try:
        inst = OPSInstance.from_instance_file(path)

        # --- initial bound, self-seeded ----------------------------------
        sol = OPSSolution(inst)
        _repair_profit(sol)
        greedy = sol.objective()
        r_init = lagrangian_bound(inst, max_iter=init_iters,
                                  lower_bound=float(greedy))
        init_ub = math.floor(r_init["upper_bound"] + EPS)

        # --- refinement against our own final incumbent ------------------
        r_ref = lagrangian_bound(inst, max_iter=ref_iters, lower_bound=float(obj))
        ref_ub = math.floor(r_ref["upper_bound"] + EPS)
    except Exception as exc:                                   # pragma: no cover
        return {"instance": label, "error": str(exc)[:140]}

    final_ub = min(init_ub, ref_ub)
    binding = "initial" if init_ub <= ref_ub else "refined"

    os.makedirs(CERTS, exist_ok=True)
    cert = os.path.join(CERTS, label + ".pkl")
    with open(cert, "wb") as fh:
        pickle.dump({
            "instance": label, "family": family,
            "incumbent": obj, "greedy": greedy,
            "init_mu": r_init.get("best_mu"), "init_raw": r_init["upper_bound"],
            "init_iters": r_init.get("iterations"), "init_ub": init_ub,
            "refine_mu": r_ref.get("best_mu"), "refine_raw": r_ref["upper_bound"],
            "refine_iters": r_ref.get("iterations"), "refine_ub": ref_ub,
            "refine_converged": bool(r_ref.get("converged")),
            "final_ub": final_ub, "binding": binding, "eps": EPS,
        }, fh, protocol=4)

    return {
        "instance": label, "family": family, "incumbent": obj, "greedy": greedy,
        "init_ub": init_ub, "init_raw": round(r_init["upper_bound"], 6),
        "init_iters": r_init.get("iterations"),
        "refined_ub": ref_ub, "refined_raw": round(r_ref["upper_bound"], 6),
        "refine_iters": r_ref.get("iterations"),
        "refine_converged": int(bool(r_ref.get("converged"))),
        "final_ub": final_ub, "binding": binding,
        "final_gap_pct": max(0.0, (final_ub - obj) / final_ub * 100) if final_ub else "",
        "cert_path": os.path.relpath(cert, ROOT).replace("\\", "/"),
        "solve_s": round(time.perf_counter() - t0, 1), "error": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=3000, help="refinement cap")
    ap.add_argument("--init-iters", type=int, default=200, help="initial-bound cap")
    ap.add_argument("--workers", type=int, default=6)
    cli = ap.parse_args()

    rows = [r for r in csv.DictReader(
        io.open("results/adaptive_master_refined.csv", encoding="utf-8-sig"))
        if r["family"] not in EXCLUDED]
    tasks = [(r["instance"], r["family"], f(r, "alns_obj"),
              cli.init_iters, cli.iters) for r in rows]
    print("rebuilding %d bounds | init %d iters | refine %d iters | %d workers\n"
          % (len(tasks), cli.init_iters, cli.iters, cli.workers), flush=True)

    out, errs = [], 0
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cli.workers) as ex:
        for i, r in enumerate(ex.map(one, tasks), 1):
            if r.get("error"):
                errs += 1
                print("  ERROR %-22s %s" % (r["instance"], r["error"]), flush=True)
                continue
            out.append(r)
            if i % 20 == 0 or i == len(tasks):
                el = time.perf_counter() - t0
                print("  [%3d/%3d] %5.1f min elapsed, ETA %5.1f min"
                      % (i, len(tasks), el / 60, (el / i) * (len(tasks) - i) / 60),
                      flush=True)

    dst = "results/bounds_certified.csv"
    with io.open(dst, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        for r in out:
            w.writerow(r)

    import statistics as st
    cur = {r["instance"]: r for r in rows}
    g = [r["final_gap_pct"] for r in out if r["final_gap_pct"] != ""]
    old = [f(cur[r["instance"]], "final_cert_gap_pct") for r in out]
    old = [x for x in old if x is not None]
    ex0, oe = sum(1 for x in g if x == 0.0), sum(1 for x in old if x == 0.0)
    w = lambda t: sum(1 for x in g if x <= t)
    viol = [r for r in out if r["final_ub"] < r["incumbent"] - EPS]

    print("\n" + "=" * 60)
    print("CERTIFIED REBUILD — no external value in the bound chain")
    print("=" * 60)
    print("  %-24s %12s %12s" % ("", "as reported", "rebuilt"))
    print("  %-24s %12d %12d" % ("proven optimal", oe, ex0))
    print("  %-24s %11.1f%% %11.1f%%" % ("proven optimal %", oe/len(old)*100, ex0/len(g)*100))
    print("  %-24s %12.4f %12.4f" % ("mean gap %", st.mean(old), st.mean(g)))
    print("  %-24s %12.4f %12.4f" % ("median gap %", st.median(old), st.median(g)))
    print("  %-24s %12.4f %12.4f" % ("max gap %", max(old), max(g)))
    print("  %-24s %12d %12d" % ("within 0.5%", sum(1 for x in old if x<=.5), w(0.5)))
    print("  %-24s %12d %12d" % ("above 2%", sum(1 for x in old if x>2), len(g)-w(2)))
    print("\n  binding bound: initial %d, refined %d"
          % (sum(1 for r in out if r["binding"] == "initial"),
             sum(1 for r in out if r["binding"] == "refined")))
    print("  refinement converged: %d/%d"
          % (sum(r["refine_converged"] for r in out), len(out)))
    print("  VALIDITY violations (ub < incumbent): %d" % len(viol))
    print("  certificates written: %d" % len(out))
    print("  errors: %d" % errs)
    print("\nwritten: %s" % dst)
    return 1 if (viol or errs) else 0


if __name__ == "__main__":
    sys.exit(main())
