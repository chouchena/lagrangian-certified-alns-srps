"""SA-inertness check — analyses acceptance rate from Tier 1 adaptivity A/B data.

The session reviewer found that n_accept_worse counts suggest SA may be nearly
inert on some instance sizes. This script checks the claim across the full size
range using the paired A/B data (200 iterations each, both adaptive and frozen).

No new compute: reads adaptivity_ab_20260827_1611.csv.
"""
import csv, os, statistics as st

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "results", "analysis", "adaptivity_ab_20260827_1611.csv")

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
rows = [r for r in rows if not r.get("error", "").strip()]

iters = int(rows[0]["iters"])   # 200

def _rate(count_str):
    try:
        return int(count_str) / iters * 100
    except (ValueError, TypeError):
        return None

# Per-instance (average across seeds): acceptance rate
by_inst = {}
for r in rows:
    key = (r["instance"], r["family"])
    ad = _rate(r.get("acc_worse_adaptive"))
    fr = _rate(r.get("acc_worse_frozen"))
    if ad is not None:
        by_inst.setdefault(key, {"n": r["instance"].split("_n")[1].split("_")[0],
                                  "family": r["family"], "ad": [], "fr": []})
        by_inst[key]["ad"].append(ad)
        by_inst[key]["fr"].append(fr)

by_inst = {k: {**v,
               "ad_mean": st.mean(v["ad"]),
               "fr_mean": st.mean(v["fr"])}
           for k, v in by_inst.items()}

ad_rates = [v["ad_mean"] for v in by_inst.values()]
fr_rates = [v["fr_mean"] for v in by_inst.values()]

print("=" * 60)
print("SA INERTNESS CHECK — acceptance rate (% worsening moves accepted)")
print(f"Data: {SRC}")
print(f"Instances: {len(by_inst)}  Seeds: {len(rows)//len(by_inst)}  Iters: {iters}")
print("=" * 60)
print(f"\n{'Arm':<12} {'Mean':>6} {'Median':>7} {'Min':>6} {'Max':>6}")
print("-" * 40)
for name, rates in [("adaptive", ad_rates), ("frozen", fr_rates)]:
    print(f"{name:<12} {st.mean(rates):>5.1f}%  {st.median(rates):>6.1f}%"
          f"  {min(rates):>5.1f}%  {max(rates):>5.1f}%")

# By size band
print("\nAcceptance rate by n (adaptive arm):")
bands = {}
for (inst, fam), v in by_inst.items():
    try:
        n = int(v["n"])
    except ValueError:
        continue
    band = (n // 20) * 20
    bands.setdefault(band, []).append(v["ad_mean"])

for band in sorted(bands):
    rates = bands[band]
    print(f"  n={band:3d}-{band+19:3d}: mean={st.mean(rates):4.1f}%  "
          f"n_inst={len(rates)}")

# Inertness verdict
overall_mean = st.mean(ad_rates)
print("\n" + "=" * 60)
if overall_mean < 5.0:
    print(f"VERDICT: SA is nearly inert — mean acceptance {overall_mean:.1f}% < 5%.")
    print("  The temperature schedule provides almost no diversification.")
    print("  Report this finding; it explains why adaptivity shows no aggregate effect.")
elif overall_mean < 15.0:
    print(f"VERDICT: SA acceptance low ({overall_mean:.1f}%) but not negligible.")
    print("  Verify whether the pattern varies systematically with n.")
else:
    print(f"VERDICT: SA is active — mean acceptance {overall_mean:.1f}%.")
print("=" * 60)
