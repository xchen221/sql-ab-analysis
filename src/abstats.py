"""Experiment statistics, written out from the formulas so each step can be explained.

Every function is checked against SciPy / statsmodels in 00_selfcheck.py.
Notation: _t = treatment arm, _c = control arm, n = sample size, alpha = two-sided level.
"""
import numpy as np
from scipy import stats


def z_crit(alpha):
    return stats.norm.ppf(1 - alpha / 2)


# --------------------------------------------------------------- sample ratio
def srm_test(observed, shares):
    """Chi-square goodness-of-fit of arm counts against the designed shares.

    A small p-value (sample ratio mismatch) means the assignment or logging is
    broken, and effect estimates should not be trusted until it is explained.
    """
    observed = np.asarray(observed, dtype=float)
    expected = observed.sum() * np.asarray(shares, dtype=float)
    chi2 = np.sum((observed - expected) ** 2 / expected)
    df = len(observed) - 1
    return {"chi2": chi2, "df": df, "p": stats.chi2.sf(chi2, df)}


def smd(mean_t, sd_t, mean_c, sd_c):
    """Standardized mean difference; |SMD| < 0.1 is the usual 'balanced' rule of thumb."""
    return (mean_t - mean_c) / np.sqrt((sd_t ** 2 + sd_c ** 2) / 2)


# ------------------------------------------------------------- effect tests
def two_proportion_test(x_t, n_t, x_c, n_c, alpha=0.05):
    """Difference in proportions with a z-test.

    The test statistic uses the pooled rate, because under H0 both arms share one
    rate. The confidence interval uses the unpooled standard error, because an
    interval should not assume H0.
    """
    p_t, p_c = x_t / n_t, x_c / n_c
    diff = p_t - p_c
    p_pool = (x_t + x_c) / (n_t + n_c)
    se_h0 = np.sqrt(p_pool * (1 - p_pool) * (1 / n_t + 1 / n_c))
    z = diff / se_h0
    se = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    zc = z_crit(alpha)
    return {"mean_t": p_t, "mean_c": p_c, "diff": diff, "se": se,
            "ci_low": diff - zc * se, "ci_high": diff + zc * se,
            "stat": z, "p": 2 * stats.norm.sf(abs(z)),
            "se_t": np.sqrt(p_t * (1 - p_t) / n_t), "se_c": np.sqrt(p_c * (1 - p_c) / n_c)}


def welch_test(mean_t, var_t, n_t, mean_c, var_c, n_c, alpha=0.05):
    """Difference in means with Welch's t-test (no equal-variance assumption).

    With ~21k customers per arm the t and normal distributions are practically the
    same, so this is also the large-sample z-test for a difference in means.
    """
    a, b = var_t / n_t, var_c / n_c
    diff = mean_t - mean_c
    se = np.sqrt(a + b)
    df = (a + b) ** 2 / (a ** 2 / (n_t - 1) + b ** 2 / (n_c - 1))   # Welch-Satterthwaite
    t = diff / se
    tc = stats.t.ppf(1 - alpha / 2, df)
    return {"mean_t": mean_t, "mean_c": mean_c, "diff": diff, "se": se,
            "ci_low": diff - tc * se, "ci_high": diff + tc * se,
            "stat": t, "df": df, "p": 2 * stats.t.sf(abs(t), df),
            "se_t": np.sqrt(a), "se_c": np.sqrt(b)}


def relative_lift(mean_t, se_t, mean_c, se_c, alpha=0.05):
    """Relative lift mean_t / mean_c - 1 with a delta-method CI (arms independent).

    Var(m_t / m_c) ~= se_t^2 / m_c^2 + m_t^2 * se_c^2 / m_c^4.
    """
    lift = mean_t / mean_c - 1
    se = np.sqrt(se_t ** 2 / mean_c ** 2 + mean_t ** 2 * se_c ** 2 / mean_c ** 4)
    zc = z_crit(alpha)
    return {"lift": lift, "lift_se": se, "lift_ci_low": lift - zc * se, "lift_ci_high": lift + zc * se}


def non_inferiority(diff, se, margin, alpha_one_sided=0.025):
    """One-sided test of H0: diff <= margin against H1: diff > margin (margin < 0).

    Passing means we can rule out a drop larger than |margin|. With a one-sided
    alpha of 0.025 this is the same as 'the lower end of the 95% CI is above the margin'.
    """
    z = (diff - margin) / se
    lower = diff - stats.norm.ppf(1 - alpha_one_sided) * se
    return {"margin": margin, "lower_bound": lower, "stat": z,
            "p": stats.norm.sf(z), "passes": bool(lower > margin)}


# ------------------------------------------------------------------- power
def mde(sd, n_t, n_c, alpha=0.05, power=0.80):
    """Minimum detectable effect (absolute) for a two-sided test of a difference in
    means: (z_{1-alpha/2} + z_{power}) * sd * sqrt(1/n_t + 1/n_c).

    For a 0/1 metric, sd = sqrt(p (1 - p)) at the baseline rate p.
    """
    return (z_crit(alpha) + stats.norm.ppf(power)) * sd * np.sqrt(1 / n_t + 1 / n_c)


def n_per_arm(sd, delta, alpha=0.05, power=0.80):
    """Customers per arm (equal split) to detect an absolute effect delta."""
    return int(np.ceil(2 * ((z_crit(alpha) + stats.norm.ppf(power)) * sd / delta) ** 2))


# ----------------------------------------------------- multiple comparisons
def holm(pvals):
    """Holm step-down adjusted p-values (controls the family-wise error rate)."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def benjamini_hochberg(pvals):
    """Benjamini-Hochberg adjusted p-values (controls the false discovery rate)."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)[::-1]                      # largest p first
    adj = np.empty(m)
    running = 1.0
    for k, i in enumerate(order):
        rank = m - k                                 # 1-based rank of p[i] from the smallest
        running = min(running, p[i] * m / rank)
        adj[i] = running
    return adj


# --------------------------------------------------------- variance reduction
def cuped_theta(y, x):
    """theta = Cov(y, x) / Var(x), estimated on the pooled data of both arms.

    x must be measured before treatment, so it cannot be affected by the e-mail and
    the adjustment cannot bias the treatment effect.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)


def cuped_adjust(y, x, theta):
    """y_cuped = y - theta * (x - mean(x)). Same mean as y, variance reduced by rho^2."""
    x = np.asarray(x, dtype=float)
    return np.asarray(y, dtype=float) - theta * (x - x.mean())


# ----------------------------------------------------------------- bootstrap
def bootstrap_diff_ci(y_t, y_c, n_boot, rng, alpha=0.05, chunk=200):
    """Percentile bootstrap CI for mean(y_t) - mean(y_c), resampling within each arm."""
    y_t = np.asarray(y_t, dtype=float)
    y_c = np.asarray(y_c, dtype=float)
    diffs = []
    for start in range(0, n_boot, chunk):
        b = min(chunk, n_boot - start)
        mt = y_t[rng.integers(0, len(y_t), size=(b, len(y_t)))].mean(axis=1)
        mc = y_c[rng.integers(0, len(y_c), size=(b, len(y_c)))].mean(axis=1)
        diffs.append(mt - mc)
    diffs = np.concatenate(diffs)
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return {"boot_ci_low": lo, "boot_ci_high": hi, "boot_se": diffs.std(ddof=1)}
