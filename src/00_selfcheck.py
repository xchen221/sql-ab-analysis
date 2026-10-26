"""Check the hand-written statistics in abstats.py against SciPy / statsmodels, and
check CI coverage and CUPED on simulated data where the truth is known."""
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportions_ztest

import abstats as ab
from config import SEED

rng = np.random.default_rng(SEED)
ok = True


def check(name, ours, ref, tol=1e-8):
    global ok
    good = np.allclose(ours, ref, rtol=tol, atol=tol)
    ok &= good
    print(f"  {'ok ' if good else 'BAD'} {name}: ours={np.round(ours, 6)} ref={np.round(ref, 6)}")


print("Two-proportion z-test vs statsmodels.proportions_ztest")
r = ab.two_proportion_test(1830, 12000, 1610, 12000)
z, p = proportions_ztest([1830, 1610], [12000, 12000])
check("z, p", [r["stat"], r["p"]], [z, p])

print("Welch t-test vs scipy.stats.ttest_ind(equal_var=False)")
a = rng.exponential(2.0, 3000)
b = rng.exponential(1.8, 2500)
r = ab.welch_test(a.mean(), a.var(ddof=1), len(a), b.mean(), b.var(ddof=1), len(b))
ref = stats.ttest_ind(a, b, equal_var=False)
ci = ref.confidence_interval(0.95)
check("t, p, df", [r["stat"], r["p"], r["df"]], [ref.statistic, ref.pvalue, ref.df])
check("95% CI", [r["ci_low"], r["ci_high"]], [ci.low, ci.high])

print("Chi-square SRM test vs scipy.stats.chisquare")
obs = [21306, 21307, 21387]
r = ab.srm_test(obs, [1 / 3] * 3)
ref = stats.chisquare(obs)
check("chi2, p", [r["chi2"], r["p"]], [ref.statistic, ref.pvalue])

print("MDE and sample size vs statsmodels.NormalIndPower")
sd, n = 0.3, 20000
d = NormalIndPower().solve_power(nobs1=n, alpha=0.05, power=0.8, ratio=1.0)
check("MDE", ab.mde(sd, n, n), d * sd, tol=1e-6)
n_ref = NormalIndPower().solve_power(effect_size=0.01 / sd, alpha=0.05, power=0.8, ratio=1.0)
check("n per arm", ab.n_per_arm(sd, 0.01), np.ceil(n_ref), tol=1e-6)

print("Holm and Benjamini-Hochberg vs statsmodels.multipletests")
pv = np.array([0.001, 0.04, 0.03, 0.2, 0.012, 0.049])
check("Holm", ab.holm(pv), multipletests(pv, method="holm")[1])
check("BH", ab.benjamini_hochberg(pv), multipletests(pv, method="fdr_bh")[1])

print("Coverage of the 95% CI for a difference in proportions (2000 simulated tests)")
p_c, p_t, n = 0.10, 0.12, 5000
cover = 0
for _ in range(2000):
    r = ab.two_proportion_test(rng.binomial(n, p_t), n, rng.binomial(n, p_c), n)
    cover += r["ci_low"] <= p_t - p_c <= r["ci_high"]
print(f"  coverage = {cover / 2000:.3f} (expect about 0.95)")
ok &= abs(cover / 2000 - 0.95) < 0.015

print("CUPED on simulated data: unbiased, variance reduced by about rho^2")
n, effect = 20000, 0.5
x = rng.normal(10, 3, 2 * n)                          # pre-period metric
treat = np.repeat([1, 0], n)
y = 2 + 0.8 * x + effect * treat + rng.normal(0, 3, 2 * n)
theta = ab.cuped_theta(y, x)
y_adj = ab.cuped_adjust(y, x, theta)
raw = y[treat == 1].mean() - y[treat == 0].mean()
adj = y_adj[treat == 1].mean() - y_adj[treat == 0].mean()
rho2 = np.corrcoef(y, x)[0, 1] ** 2
print(f"  theta = {theta:.3f} (true 0.8); effect raw = {raw:.3f}, CUPED = {adj:.3f} (true {effect})")
print(f"  variance reduction = {1 - y_adj.var() / y.var():.3f}, rho^2 = {rho2:.3f}")
ok &= abs(theta - 0.8) < 0.02 and abs(adj - effect) < 0.1

print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
raise SystemExit(0 if ok else 1)
