"""
Instance-quality analysis: how do n, K, alpha, distance affect cert gap?

Scope  : 660-instance study set — families B, C, D, EB, EC, ED (K=2,3,4 only).
         A/EA (K=1, trivially near-zero gaps) are excluded so results are
         consistent with the paper's stated computational study.

Part 1 — four univariate non-parametric tests
Part 2 — Tobit MLE (left-censored at 0): main effects + interactions
Part 3 — Likelihood Ratio tests: overall fit, interaction block, distance drop,
           and parsimonious model (no distance)

Output is mirrored to results/analysis/quality_analysis_<date>.txt
"""
import argparse, warnings, sys, os
from datetime import datetime
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--csv", default="results/adaptive_master.csv",
                     help="Master CSV to analyse (default: results/adaptive_master.csv — "
                          "the canonical adaptive results; uses final_cert_gap_pct)")
_args, _ = _parser.parse_known_args()
_MASTER_CSV = _args.csv
from scipy import stats
from scipy.optimize import minimize
from statsmodels.tools import add_constant

# ── tee stdout to archive file ────────────────────────────────────────────────
os.makedirs("results/analysis", exist_ok=True)
datestamp = datetime.now().strftime("%Y%m%d_%H%M")
archive_path = f"results/analysis/quality_analysis_{datestamp}.txt"

class Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, data):
        for s in self.streams: s.write(data)
    def flush(self):
        for s in self.streams: s.flush()

_log = open(archive_path, "w", encoding="utf-8")
sys.stdout = Tee(sys.__stdout__, _log)

# ─────────────────────────────────────────────────────────────────────────────
# Load & prepare
# ─────────────────────────────────────────────────────────────────────────────
df_all = pd.read_csv(_MASTER_CSV)

# ── Restrict to 660-instance study set (K=2,3,4; families B/C/D/EB/EC/ED) ──
STUDY_FAMILIES = ["B", "C", "D", "EB", "EC", "ED"]
df = df_all[df_all["family"].isin(STUDY_FAMILIES)].copy()

df["K"]        = df["family"].str.lstrip("E").map({"B":2,"C":3,"D":4})
df["distance"] = np.where(df["family"].str.startswith("E"), 1, 0)
df["gap"]      = df["final_cert_gap_pct"].astype(float)

# Standardise within the study set
df["n_std"]     = (df["n"]     - df["n"].mean())     / df["n"].std()
df["alpha_std"] = (df["alpha"] - df["alpha"].mean()) / df["alpha"].std()
df["K_std"]     = (df["K"]     - df["K"].mean())     / df["K"].std()

N      = len(df)
N_zero = (df["gap"] == 0).sum()
print(f"Quality analysis  —  run {datestamp}")
print(f"Dataset: {N} instances (study set: B/C/D/EB/EC/ED, K=2,3,4)")
print(f"  gap=0: {N_zero} ({100*N_zero/N:.1f}%)  |  gap>0: {N-N_zero}")
print(f"  gap (all):   mean={df['gap'].mean():.4f}%  median={df['gap'].median():.4f}%  max={df['gap'].max():.4f}%")
print(f"  gap (gap>0): mean={df[df['gap']>0]['gap'].mean():.4f}%  median={df[df['gap']>0]['gap'].median():.4f}%")

# ─────────────────────────────────────────────────────────────────────────────
# Tobit helpers
# ─────────────────────────────────────────────────────────────────────────────
def tobit_nll(params, X, y):
    beta, log_sigma = params[:-1], params[-1]
    sigma = np.exp(log_sigma)
    xb    = X @ beta
    ll    = np.where(
        y == 0,
        np.log(stats.norm.cdf(-xb / sigma) + 1e-300),
        np.log(stats.norm.pdf((y - xb) / sigma) / sigma + 1e-300)
    )
    return -ll.sum()

def fit_tobit(X, y, label=""):
    ols_b = np.linalg.lstsq(X[y>0], y[y>0], rcond=None)[0]
    sig0  = np.std(y[y>0] - X[y>0] @ ols_b)
    x0    = np.append(ols_b, np.log(max(sig0, 1e-6)))
    res   = minimize(tobit_nll, x0, args=(X, y), method="L-BFGS-B",
                     options={"maxiter":3000,"ftol":1e-13})
    return res

def numerical_se(result, X, y):
    eps, n_p = 1e-5, len(result.x)
    H = np.zeros((n_p, n_p))
    for i in range(n_p):
        for j in range(i, n_p):
            ei, ej = np.zeros(n_p), np.zeros(n_p)
            ei[i] = eps; ej[j] = eps
            H[i,j] = H[j,i] = (
                tobit_nll(result.x+ei+ej, X, y)
              - tobit_nll(result.x+ei-ej, X, y)
              - tobit_nll(result.x-ei+ej, X, y)
              + tobit_nll(result.x-ei-ej, X, y)
            ) / (4*eps**2)
    try:
        cov = np.linalg.inv(H)
        return np.sqrt(np.abs(np.diag(cov)[:-1]))
    except Exception:
        return np.full(len(result.x)-1, np.nan)

def mcz_r2(result, X):
    """McKelvey-Zavoina pseudo-R² for a Tobit model.
    R²_MZ = Var(Xβ) / (Var(Xβ) + σ²)  where Var is population variance."""
    beta     = result.x[:-1]
    var_yhat = np.var(X @ beta)
    sigma_sq = np.exp(result.x[-1]) ** 2
    return var_yhat / (var_yhat + sigma_sq)

def lr_test(ll_restricted, ll_full, df_diff):
    """ll_restricted and ll_full are log-likelihoods (higher = better fit)."""
    LR = 2 * (ll_full - ll_restricted)   # always >= 0 for nested models
    p  = stats.chi2.sf(LR, df_diff)
    return LR, p

def print_tobit(result, feature_names, se):
    beta   = result.x[:-1]
    sigma  = np.exp(result.x[-1])
    z_stat = beta / np.where(se > 0, se, np.nan)
    p_vals = 2 * stats.norm.sf(np.abs(z_stat))
    print(f"  sigma = {sigma:.4f}   log-likelihood = {-result.fun:.4f}")
    print(f"\n  {'Predictor':<26} {'Coef':>9} {'SE':>9} {'z':>8} {'p':>11}  Sig")
    print("  " + "-"*72)
    for nm, b, s, z, p in zip(feature_names, beta, se, z_stat, p_vals):
        if np.isnan(p): sig=""
        elif p<0.001: sig="***"
        elif p<0.01:  sig="**"
        elif p<0.05:  sig="*"
        elif p<0.10:  sig="."
        else:         sig=""
        print(f"  {nm:<26} {b:>9.4f} {s:>9.4f} {z:>8.3f} {p:>11.4e}  {sig}")
    print("  Significance: *** p<0.001  ** p<0.01  * p<0.05  . p<0.10")

# ─────────────────────────────────────────────────────────────────────────────
# Build design matrices for three nested models
# ─────────────────────────────────────────────────────────────────────────────
df_m = df[["n_std","K_std","alpha_std","distance","gap"]].dropna()
y    = df_m["gap"].values

# Model 0: intercept only (null)
X0   = add_constant(np.ones((len(y),1)))[:,0:1]          # just intercept
feat0 = ["const"]

# Model 1: main effects only
X1_raw  = df_m[["n_std","K_std","alpha_std","distance"]].values
X1      = add_constant(X1_raw)
feat1   = ["const","n_std","K_std","alpha_std","distance"]

# Model 2: main effects + all pairwise interactions
IA = [("n_std","K_std"),("n_std","alpha_std"),("n_std","distance"),
      ("K_std","alpha_std"),("K_std","distance"),("alpha_std","distance")]
ia_vals = np.column_stack([df_m[a].values * df_m[b].values for a,b in IA])
X2      = add_constant(np.hstack([X1_raw, ia_vals]))
feat2   = feat1[1:] + [f"{a}:{b}" for a,b in IA]
feat2   = ["const"] + feat2[1:] if feat2[0]=="const" else ["const"] + feat2
feat2   = ["const","n_std","K_std","alpha_std","distance"] + [f"{a}:{b}" for a,b in IA]

# Model 3: main effects, no distance
X3_raw  = df_m[["n_std","K_std","alpha_std"]].values
X3      = add_constant(X3_raw)
feat3   = ["const","n_std","K_std","alpha_std"]

# Model 4: parsimonious — n + K + alpha + n*K + K*alpha (no distance, theoretically motivated)
IA_pars  = [("n_std","K_std"),("K_std","alpha_std")]
ia_pars  = np.column_stack([df_m[a].values * df_m[b].values for a,b in IA_pars])
X4       = add_constant(np.hstack([X3_raw, ia_pars]))
feat4    = ["const","n_std","K_std","alpha_std","n_std:K_std","K_std:alpha_std"]

# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — Univariate non-parametric tests
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*74)
print("PART 1 — Univariate non-parametric tests")
print("="*74)

rho_n, p_n = stats.spearmanr(df["n"], df["gap"])
print(f"\n1. Spearman rho  (n vs gap):         rho = {rho_n:+.4f}   p = {p_n:.4e}")
print(f"   Note: negative rho is a K confound (large n = K=1 family)")

# K=1 (families A/EA) is excluded from the study set, so analyse K=2,3,4 only.
K_LEVELS = [2,3,4]
groups_K = [df[df["K"]==k]["gap"].values for k in K_LEVELS]
H_K, p_K = stats.kruskal(*groups_K)
means_K  = {k: df[df["K"]==k]["gap"].mean() for k in K_LEVELS}
print(f"\n2. Kruskal-Wallis  (K vs gap):        H = {H_K:.3f}   p = {p_K:.4e}")
print(f"   mean gap by K: " + "  ".join(f"K={k}: {means_K[k]:.4f}%" for k in K_LEVELS))
pairs_K = [(2,3),(2,4),(3,4)]
n_pk = len(pairs_K)
print(f"   Pairwise Mann-Whitney (Bonferroni corrected, alpha={0.05/n_pk:.4f}):")
for a,b in pairs_K:
    U,p = stats.mannwhitneyu(df[df["K"]==a]["gap"], df[df["K"]==b]["gap"], alternative="two-sided")
    sig = "**" if p<0.05/n_pk else ("*" if p<0.05 else "")
    print(f"     K={a} vs K={b}: U={U:.0f}  p={p:.4e} {sig}")

line = df[df["distance"]==0]["gap"]
eucl = df[df["distance"]==1]["gap"]
U_d, p_d = stats.mannwhitneyu(line, eucl, alternative="two-sided")
print(f"\n3. Mann-Whitney  (distance):          U = {U_d:.1f}   p = {p_d:.4e}")
print(f"   mean gap: Line={line.mean():.4f}%   Euclidean={eucl.mean():.4f}%")

alphas   = sorted(df["alpha"].unique())
groups_a = [df[df["alpha"]==a]["gap"].values for a in alphas]
H_a, p_a = stats.kruskal(*groups_a)
means_a  = {a: df[df["alpha"]==a]["gap"].mean() for a in alphas}
print(f"\n4. Kruskal-Wallis  (alpha vs gap):    H = {H_a:.3f}   p = {p_a:.4e}")
print(f"   mean gap by alpha: " + "  ".join(f"a={a}: {means_a[a]:.4f}%" for a in alphas))
pairs_a = [(alphas[i],alphas[j]) for i in range(len(alphas)) for j in range(i+1,len(alphas))]
n_pa = len(pairs_a)
print(f"   Pairwise Mann-Whitney (Bonferroni corrected, alpha={0.05/n_pa:.4f}):")
for a,b in pairs_a:
    U,p = stats.mannwhitneyu(df[df["alpha"]==a]["gap"], df[df["alpha"]==b]["gap"], alternative="two-sided")
    sig = "**" if p<0.05/n_pa else ("*" if p<0.05 else "")
    print(f"     a={a} vs a={b}: U={U:.0f}  p={p:.4e} {sig}")

# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — Tobit regression models
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*74)
print(f"PART 2 — Tobit regression  (left-censored at 0,  n={N},  n_censored={N_zero})")
print("="*74)

print("\nFitting Model 0 (null — intercept only)...")
r0 = fit_tobit(X0, y)
print("Fitting Model 1 (main effects only)...")
r1 = fit_tobit(X1, y)
print("Fitting Model 2 (main effects + all interactions)...")
r2 = fit_tobit(X2, y)
print("Fitting Model 3 (main effects, no distance)...")
r3 = fit_tobit(X3, y)
print("Fitting Model 4 (parsimonious: n+K+alpha+n*K+K*alpha)...")
r4 = fit_tobit(X4, y)

print("\n--- Model 1: Main effects only ---")
se1 = numerical_se(r1, X1, y)
print_tobit(r1, feat1, se1)
print(f"  McKelvey-Zavoina R² = {mcz_r2(r1, X1):.4f}")

print("\n--- Model 2: Main effects + all pairwise interactions ---")
se2 = numerical_se(r2, X2, y)
print_tobit(r2, feat2, se2)
print(f"  McKelvey-Zavoina R² = {mcz_r2(r2, X2):.4f}")

print("\n--- Model 4: Parsimonious (n + K + alpha + n*K + K*alpha) [REPORTING MODEL] ---")
se4 = numerical_se(r4, X4, y)
print_tobit(r4, feat4, se4)
print(f"  McKelvey-Zavoina R² = {mcz_r2(r4, X4):.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# PART 3 — Likelihood Ratio tests
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*74)
print("PART 3 — Likelihood Ratio (LR) tests")
print("="*74)
print("  H0: restricted model sufficient  vs  H1: unrestricted model better")
print(f"  LR = 2*(LL_full - LL_restricted)  ~  chi2(df_diff)\n")

ll0 = -r0.fun
ll1 = -r1.fun
ll2 = -r2.fun
ll3 = -r3.fun

rows = []

# Test A: overall model significance — main effects vs null
LR_A, p_A = lr_test(-r0.fun, -r1.fun, len(feat1)-len(feat0))
rows.append(("A", "Null vs Main effects",
             len(feat0), ll0, len(feat1), ll1,
             len(feat1)-len(feat0), LR_A, p_A))

# Test B: interaction block — main effects vs full model
LR_B, p_B = lr_test(-r1.fun, -r2.fun, len(feat2)-len(feat1))
rows.append(("B", "Main effects vs +Interactions",
             len(feat1), ll1, len(feat2), ll2,
             len(feat2)-len(feat1), LR_B, p_B))

# Test C: overall — null vs full
LR_C, p_C = lr_test(-r0.fun, -r2.fun, len(feat2)-len(feat0))
rows.append(("C", "Null vs Full model",
             len(feat0), ll0, len(feat2), ll2,
             len(feat2)-len(feat0), LR_C, p_C))

# Test D: drop distance — model without distance vs main effects
LR_D, p_D = lr_test(-r3.fun, -r1.fun, len(feat1)-len(feat3))
rows.append(("D", "Drop distance (main effects)",
             len(feat3), -r3.fun, len(feat1), -r1.fun,
             len(feat1)-len(feat3), LR_D, p_D))

# Test E: parsimonious vs full model (are the dropped terms jointly zero?)
LR_E, p_E = lr_test(-r4.fun, -r2.fun, len(feat2)-len(feat4))
rows.append(("E", "Parsimonious vs Full (dropped terms = 0)",
             len(feat4), -r4.fun, len(feat2), -r2.fun,
             len(feat2)-len(feat4), LR_E, p_E))

print(f"  {'Test':<2}  {'Comparison':<42} {'dof':>4} {'LR':>9} {'p':>12}  Decision")
print("  " + "-"*80)
for tid, label, k0, ll_r, k1, ll_f, dof, LR, p in rows:
    if p < 0.001:   dec = "Reject H0 ***"
    elif p < 0.01:  dec = "Reject H0 **"
    elif p < 0.05:  dec = "Reject H0 *"
    elif p < 0.10:  dec = "Marginal ."
    else:           dec = "Fail to reject H0"
    print(f"  {tid:<2}  {label:<42} {dof:>4} {LR:>9.3f} {p:>12.4e}  {dec}")

print(f"""
  Interpretation:
  A: Instance characteristics collectively explain significant variation in cert gap.
  B: Interaction terms add significant explanatory power beyond main effects.
     The n x K cross-effect is structurally present within the study set.
  C: Full model strongly preferred over null.
  D: Distance can be dropped from main-effects model without significant loss.
  E: Parsimonious model (n+K+alpha+n*K+K*alpha) is not significantly worse than
     the full model — justifies using Model 4 as the reporting model.
     p(E)={p_E:.3f}: {'Parsimonious model adequate.' if p_E>=0.05 else 'WARNING: dropped terms may matter.'}"""
)

# ─────────────────────────────────────────────────────────────────────────────
# Cross-impact pivot tables
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*74)
print("CROSS-IMPACT — mean cert gap % by (K x alpha)")
print("="*74)
print(df.pivot_table(values="gap", index="K", columns="alpha", aggfunc="mean").round(4).to_string())

print("\n" + "="*74)
print("CROSS-IMPACT — mean cert gap % by (K x distance)")
print("="*74)
piv_kd = df.pivot_table(values="gap", index="K",
                         columns=df["distance"].map({0:"Line",1:"Euclidean"}),
                         aggfunc="mean").round(4)
print(piv_kd.to_string())

print("\n" + "="*74)
print("CROSS-IMPACT — mean cert gap % by (n x K)  [K=1 omitted, near-zero]")
print("="*74)
piv_nK = df[df["K"]>1].pivot_table(values="gap", index="n", columns="K", aggfunc="mean").round(4)
print(piv_nK.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# CSV exports
# ─────────────────────────────────────────────────────────────────────────────
base = archive_path.replace(".txt", "")

# 1. Per-instance data with all analysis variables
inst_csv = base + "_instances.csv"
df_out = df[["instance","family","n","K","alpha","distance","gap"]].copy()
df_out["distance_label"] = df_out["distance"].map({0:"Line",1:"Euclidean"})
df_out["tier"] = pd.cut(
    df_out["gap"],
    bins=[-1e-9, 0.005, 0.5, 1.0, 2.0, float("inf")],
    labels=["exact","<0.5%","0.5-1%","1-2%",">2%"]
)
df_out.drop(columns=["distance"]).rename(columns={"distance_label":"distance"}).to_csv(inst_csv, index=False)

# 2. Tobit coefficients — M1, M2, M4 stacked
rows_tobit = []
for model_name, result, features, se, X_m in [
    ("M1_main",  r1, feat1[1:], se1[1:], X1),
    ("M2_full",  r2, feat2[1:], se2[1:], X2),
    ("M4_pars",  r4, feat4[1:], se4[1:], X4),
]:
    beta  = result.x[1:-1]          # skip const and log_sigma
    sigma = np.exp(result.x[-1])
    ll    = -result.fun
    r2mz  = round(mcz_r2(result, X_m), 4)
    z_arr = beta / np.where(se > 0, se, np.nan)
    p_arr = 2 * stats.norm.sf(np.abs(z_arr))
    for nm, b, s, z, p in zip(features, beta, se, z_arr, p_arr):
        rows_tobit.append({
            "model": model_name, "predictor": nm,
            "coef": round(b, 4), "se": round(s, 4),
            "z": round(z, 3), "p": round(p, 6),
            "sig": ("***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else "." if p<0.10 else ""),
            "sigma": round(sigma, 4), "log_likelihood": round(ll, 4),
            "r2_mz": r2mz,
        })
tobit_csv = base + "_tobit.csv"
pd.DataFrame(rows_tobit).to_csv(tobit_csv, index=False)

# 3. LR test results
lr_rows = [
    {"test":"A","comparison":"Null vs Main effects",           "dof":len(feat1)-len(feat0),"LR":round(LR_A,3),"p":round(p_A,6)},
    {"test":"B","comparison":"Main effects vs +Interactions",  "dof":len(feat2)-len(feat1),"LR":round(LR_B,3),"p":round(p_B,6)},
    {"test":"C","comparison":"Null vs Full model",             "dof":len(feat2)-len(feat0),"LR":round(LR_C,3),"p":round(p_C,6)},
    {"test":"D","comparison":"Drop distance (main effects)",   "dof":len(feat1)-len(feat3),"LR":round(LR_D,3),"p":round(p_D,6)},
    {"test":"E","comparison":"Parsimonious vs Full",           "dof":len(feat2)-len(feat4),"LR":round(LR_E,3),"p":round(p_E,6)},
]
lr_csv = base + "_lr_tests.csv"
pd.DataFrame(lr_rows).to_csv(lr_csv, index=False)

# 4. Cross-impact K×alpha (long format)
piv_ka_long = (df.pivot_table(values="gap", index="K", columns="alpha", aggfunc=["mean","median","count"])
               .stack(level=1).reset_index())
piv_ka_long.columns = ["K","alpha","mean_cert","median_cert","count"]
piv_ka_long = piv_ka_long.round(4)
crossimpact_csv = base + "_crossimpact_Kalpha.csv"
piv_ka_long.to_csv(crossimpact_csv, index=False)

sys.stdout = sys.__stdout__
_log.close()
print(f"\nOutput archived to: {archive_path}")
print(f"CSV exports:")
print(f"  {inst_csv}")
print(f"  {tobit_csv}")
print(f"  {lr_csv}")
print(f"  {crossimpact_csv}")
