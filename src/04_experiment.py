"""Analyse the Hillstrom e-mail experiment end to end.

Order of the analysis follows the order a reviewer would check things:
  1 data checks -> 2 sample ratio -> 3 covariate balance -> 4 sensitivity (MDE)
  -> 5 effects + multiple comparisons -> 6 CUPED / regression adjustment
  -> 7 guardrail -> 8 heterogeneity -> 9 A/A and peeking simulations.
Arm-level aggregates come from SQL (sql/experiment/); unit-level data are used only
where they are needed (bootstrap, CUPED, regression, simulations).
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

import abstats as ab
from common import connect, run_sql_file
from config import (ADJUST_COVARIATES, ALPHA, CONTROL, CUPED_COVARIATE, DESIGN_SHARES,
                    GUARDRAIL_METRIC, GUARDRAIL_REL_MARGIN, N_BOOT, N_LOOKS, N_SIM, POWER,
                    PRIMARY_METRIC, RESULTS, SECONDARY_METRICS, SEED, SQL_DIR, SRM_ALPHA,
                    TREATMENTS)

OUT = RESULTS / "experiment"
EXP_SQL = SQL_DIR / "experiment"
METRICS = [PRIMARY_METRIC] + SECONDARY_METRICS
BINARY = {"visit", "conversion"}
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def section(title):
    print(f"\n=== {title}")


def save(df, name):
    df.to_csv(OUT / f"{name}.csv", index=False)


def compare(metric, t_stats, c_stats):
    """Effect of one treatment on one metric from arm-level sufficient statistics."""
    if metric in BINARY:
        r = ab.two_proportion_test(t_stats["total"], t_stats["n"], c_stats["total"], c_stats["n"], ALPHA)
        r["test"] = "two-proportion z"
    else:
        r = ab.welch_test(t_stats["mean"], t_stats["var"], t_stats["n"],
                          c_stats["mean"], c_stats["var"], c_stats["n"], ALPHA)
        r["test"] = "Welch t"
    r.update(ab.relative_lift(r["mean_t"], r["se_t"], r["mean_c"], r["se_c"], ALPHA))
    return r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    rng = np.random.default_rng(SEED)
    summary = {}

    # ------------------------------------------------------------ 1. checks
    section("1. Data checks (e00_checks.sql)")
    checks = run_sql_file(con, EXP_SQL / "e00_checks.sql")
    save(checks, "e00_checks")
    print(checks.to_string(index=False))
    assert checks.loc[checks.check_name.str.startswith("rows"), "n_rows"].item() == 64000
    failed = checks[~checks.check_name.str.startswith("rows") & (checks.n_rows > 0)]
    print("all checks zero" if failed.empty else f"NON-ZERO CHECKS: {failed.check_name.tolist()}")

    # ------------------------------------------------------ 2. sample ratio
    section("2. Sample ratio mismatch (SRM) check")
    assign = run_sql_file(con, EXP_SQL / "e01_assignment.sql")
    save(assign, "e01_assignment")
    arms = list(DESIGN_SHARES)
    counts = assign.set_index("arm").loc[arms, "n"].to_numpy()
    srm = ab.srm_test(counts, [DESIGN_SHARES[a] for a in arms])
    print(assign.to_string(index=False))
    print(f"chi2 = {srm['chi2']:.3f} (df {srm['df']}), p = {srm['p']:.3f}; "
          f"alarm threshold p < {SRM_ALPHA}: {'SRM!' if srm['p'] < SRM_ALPHA else 'no SRM'}")
    summary["srm"] = {**srm, "counts": dict(zip(arms, counts.tolist()))}

    # --------------------------------------------------- 3. covariate balance
    section("3. Pre-treatment covariate balance (standardized mean differences)")
    bal = run_sql_file(con, EXP_SQL / "e02_balance.sql").set_index(["covariate", "arm"])
    rows = []
    for t in TREATMENTS:
        for cov in bal.index.get_level_values("covariate").unique():
            bt, bc = bal.loc[(cov, t)], bal.loc[(cov, CONTROL)]
            rows.append({"treatment": t, "covariate": cov, "mean_t": bt["mean"], "mean_c": bc["mean"],
                         "smd": ab.smd(bt["mean"], bt["sd"], bc["mean"], bc["sd"])})
    balance = pd.DataFrame(rows)
    save(balance, "balance")
    print(balance.pivot(index="covariate", columns="treatment", values="smd").round(4).to_string())
    summary["max_abs_smd"] = float(balance.smd.abs().max())
    print(f"max |SMD| = {summary['max_abs_smd']:.4f} (rule of thumb: < 0.1)")

    # ----------------------------------------------- 4. sensitivity / MDE
    section("4. Sensitivity: minimum detectable effect at the realised sample size")
    arm_stats = run_sql_file(con, EXP_SQL / "e03_arm_metrics.sql")
    save(arm_stats, "e03_arm_metrics")
    s = arm_stats.set_index(["metric", "arm"])
    family_size = {PRIMARY_METRIC: len(TREATMENTS)}
    family_size.update({m: len(SECONDARY_METRICS) * len(TREATMENTS) for m in SECONDARY_METRICS})
    rows = []
    for metric in METRICS:
        c = s.loc[(metric, CONTROL)]
        sd = np.sqrt(c["var"])
        alpha_design = ALPHA / family_size[metric]          # Bonferroni, for design only
        n_t = s.loc[(metric, TREATMENTS[0]), "n"]
        mde = ab.mde(sd, n_t, c["n"], alpha_design, POWER)
        rows.append({"metric": metric, "baseline_mean": c["mean"], "baseline_sd": sd,
                     "alpha_per_test": alpha_design, "power": POWER, "n_per_arm": int(c["n"]),
                     "mde_abs": mde, "mde_rel": mde / c["mean"],
                     "n_per_arm_for_10pct_lift": ab.n_per_arm(sd, 0.10 * c["mean"], alpha_design, POWER)})
    power = pd.DataFrame(rows)
    save(power, "power_mde")
    print("Baseline = control arm (stands in for pre-experiment history, which this dataset lacks).")
    print(power.round(5).to_string(index=False))

    # ------------------------------------ 5. effects + multiple comparisons
    section("5. Treatment effects (difference vs control, 95% CI) with Holm adjustment per family")
    rows = []
    for metric in METRICS:
        for t in TREATMENTS:
            r = compare(metric, s.loc[(metric, t)], s.loc[(metric, CONTROL)])
            rows.append({"metric": metric,
                         "family": "primary" if metric == PRIMARY_METRIC else "secondary",
                         "treatment": t, "n_t": int(s.loc[(metric, t), "n"]),
                         "n_c": int(s.loc[(metric, CONTROL), "n"]), **r})
    eff = pd.DataFrame(rows)
    eff["p_holm"] = np.nan
    for fam, idx in eff.groupby("family").groups.items():
        eff.loc[idx, "p_holm"] = ab.holm(eff.loc[idx, "p"].to_numpy())

    # Spend is zero-inflated and heavy-tailed: confirm the Welch CI with a bootstrap.
    df = con.execute("SELECT * FROM hillstrom").df()
    for t in TREATMENTS:
        b = ab.bootstrap_diff_ci(df.loc[df.segment == t, "spend"], df.loc[df.segment == CONTROL, "spend"],
                                 N_BOOT, rng, ALPHA)
        for k, v in b.items():
            eff.loc[(eff.metric == "spend") & (eff.treatment == t), k] = v
    cols = ["metric", "treatment", "mean_c", "mean_t", "diff", "ci_low", "ci_high", "lift",
            "lift_ci_low", "lift_ci_high", "p", "p_holm", "boot_ci_low", "boot_ci_high"]
    save(eff, "effects")
    print(eff[cols].to_string(index=False, float_format=lambda v: f"{v:.5g}"))

    # The launch decision is "which e-mail", so also compare the two e-mails directly
    # (its own family of 3 tests, Holm-adjusted).
    a, b = TREATMENTS
    h2h = pd.DataFrame([{"metric": metric, "comparison": f"{a} - {b}",
                         **compare(metric, s.loc[(metric, a)], s.loc[(metric, b)])}
                        for metric in METRICS])
    h2h["p_holm"] = ab.holm(h2h.p.to_numpy())
    save(h2h, "head_to_head")
    print(f"\nHead-to-head ({a} minus {b}):")
    print(h2h[["metric", "mean_t", "mean_c", "diff", "ci_low", "ci_high", "p", "p_holm"]]
          .to_string(index=False, float_format=lambda v: f"{v:.5g}"))

    # --------------------------------------- 6. CUPED and regression adjustment
    section(f"6. Variance reduction: CUPED on '{CUPED_COVARIATE}' and regression adjustment")
    rows = []
    for metric in METRICS:
        for t in TREATMENTS:
            sub = df[df.segment.isin([t, CONTROL])].copy()
            sub["treat"] = (sub.segment == t).astype(int)
            yt, yc = sub.loc[sub.treat == 1, metric], sub.loc[sub.treat == 0, metric]
            raw = ab.welch_test(yt.mean(), yt.var(), len(yt), yc.mean(), yc.var(), len(yc), ALPHA)

            theta = ab.cuped_theta(sub[metric], sub[CUPED_COVARIATE])
            sub["y_cuped"] = ab.cuped_adjust(sub[metric], sub[CUPED_COVARIATE], theta)
            at, ac = sub.loc[sub.treat == 1, "y_cuped"], sub.loc[sub.treat == 0, "y_cuped"]
            cup = ab.welch_test(at.mean(), at.var(), len(at), ac.mean(), ac.var(), len(ac), ALPHA)

            # Lin (2013) estimator: covariates centred, interacted with treatment, HC2 SEs.
            for cov in ADJUST_COVARIATES:
                sub[f"{cov}_c"] = sub[cov] - sub[cov].mean()
            centred = " + ".join(f"{c}_c" for c in ADJUST_COVARIATES)
            fit = smf.ols(f"{metric} ~ treat * ({centred})", data=sub).fit(cov_type="HC2")

            rows.append({"metric": metric, "treatment": t,
                         "diff_raw": raw["diff"], "se_raw": raw["se"],
                         "theta": theta,
                         "corr_y_x": np.corrcoef(sub[metric], sub[CUPED_COVARIATE])[0, 1],
                         "diff_cuped": cup["diff"], "se_cuped": cup["se"],
                         "var_reduction_cuped": 1 - sub["y_cuped"].var() / sub[metric].var(),
                         "diff_regadj": fit.params["treat"], "se_regadj": fit.bse["treat"],
                         "se_ratio_cuped": cup["se"] / raw["se"],
                         "se_ratio_regadj": fit.bse["treat"] / raw["se"]})
    var_red = pd.DataFrame(rows)
    save(var_red, "variance_reduction")
    print(var_red.to_string(index=False, float_format=lambda v: f"{v:.5g}"))

    # ------------------------------------------------------- 7. guardrail
    section(f"7. Guardrail: {GUARDRAIL_METRIC} per customer, non-inferiority "
            f"(margin {GUARDRAIL_REL_MARGIN:+.0%} of control mean)")
    rows = []
    for t in TREATMENTS:
        e = eff[(eff.metric == GUARDRAIL_METRIC) & (eff.treatment == t)].iloc[0]
        ni = ab.non_inferiority(e["diff"], e["se"], GUARDRAIL_REL_MARGIN * e["mean_c"])
        rows.append({"treatment": t, "diff": e["diff"], **ni})
    guard = pd.DataFrame(rows)
    save(guard, "guardrail")
    print(guard.to_string(index=False, float_format=lambda v: f"{v:.5g}"))

    # -------------------------------------------------- 8. heterogeneity
    section("8. Heterogeneity: visit lift by past purchase category")
    seg_sql = run_sql_file(con, EXP_SQL / "e04_segment_visits.sql")
    save(seg_sql, "e04_segment_visits")
    df["past_category"] = np.select([(df.mens == 1) & (df.womens == 1), df.mens == 1],
                                    ["both", "mens only"], "womens only")
    rows = []
    for t in TREATMENTS:
        for g in ["mens only", "womens only", "both"]:
            d = df[df.past_category == g]
            yt, yc = d.loc[d.segment == t, "visit"], d.loc[d.segment == CONTROL, "visit"]
            r = ab.two_proportion_test(yt.sum(), len(yt), yc.sum(), len(yc), ALPHA)
            rows.append({"treatment": t, "past_category": g, "n_t": len(yt), "n_c": len(yc),
                         "mean_c": r["mean_c"], "mean_t": r["mean_t"], "diff": r["diff"],
                         "se": r["se"], "ci_low": r["ci_low"], "ci_high": r["ci_high"], "p": r["p"]})
    het = pd.DataFrame(rows)
    het["p_bh"] = ab.benjamini_hochberg(het.p.to_numpy())     # exploratory: 6 subgroup tests
    save(het, "heterogeneity_subgroups")
    print(het.drop(columns="se").to_string(index=False, float_format=lambda v: f"{v:.4g}"))

    # Pre-specified contrast: does each e-mail lift visits more among customers who
    # bought that category last year than among those who bought only the other one?
    rows = []
    for t, match, other in [("Mens E-Mail", "mens only", "womens only"),
                            ("Womens E-Mail", "womens only", "mens only")]:
        a = het[(het.treatment == t) & (het.past_category == match)].iloc[0]
        b = het[(het.treatment == t) & (het.past_category == other)].iloc[0]
        dd = a["diff"] - b["diff"]
        se = np.sqrt(a["se"] ** 2 + b["se"] ** 2)            # independent subgroups
        z = dd / se
        rows.append({"treatment": t, "matching": match, "other": other,
                     "lift_matching": a["diff"], "lift_other": b["diff"], "diff_in_lift": dd,
                     "ci_low": dd - ab.z_crit(ALPHA) * se, "ci_high": dd + ab.z_crit(ALPHA) * se,
                     "p": 2 * stats.norm.sf(abs(z))})
    contrast = pd.DataFrame(rows)
    contrast["p_holm"] = ab.holm(contrast.p.to_numpy())
    save(contrast, "heterogeneity_contrast")
    print("\nPre-specified contrast (matching minus non-matching past category):")
    print(contrast.to_string(index=False, float_format=lambda v: f"{v:.4g}"))

    # ------------------------------------------- 9. A/A and peeking simulation
    section(f"9. A/A test and peeking, simulated on the control arm ({N_SIM} runs)")
    y = df.loc[df.segment == CONTROL, PRIMARY_METRIC].to_numpy(dtype=float)
    n = len(y)
    look_counts = [1, 2, 3, 5, 10, 20, 50]
    reject_any = {k: 0 for k in look_counts}
    reject_bonf = 0
    batch = 100
    for start in range(0, N_SIM, batch):
        b = min(batch, N_SIM - start)
        y_ord = y[np.argsort(rng.random((b, n)), axis=1)]     # random arrival order
        a = rng.random((b, n)) < 0.5                          # random A/A assignment
        cx_t, cn_t = np.cumsum(y_ord * a, axis=1), np.cumsum(a, axis=1)
        cx_c, cn_c = np.cumsum(y_ord * ~a, axis=1), np.cumsum(~a, axis=1)
        for k in look_counts:
            idx = (np.arange(1, k + 1) * n) // k - 1          # k equally spaced looks
            r = ab.two_proportion_test(cx_t[:, idx], cn_t[:, idx], cx_c[:, idx], cn_c[:, idx])
            reject_any[k] += int((r["p"] < ALPHA).any(axis=1).sum())
            if k == N_LOOKS:
                reject_bonf += int((r["p"] < ALPHA / N_LOOKS).any(axis=1).sum())
    peek = pd.DataFrame({"n_looks": look_counts,
                         "false_positive_rate": [reject_any[k] / N_SIM for k in look_counts]})
    peek["mc_se"] = np.sqrt(peek.false_positive_rate * (1 - peek.false_positive_rate) / N_SIM)
    save(peek, "peeking_simulation")
    print(peek.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"With {N_LOOKS} looks and a Bonferroni threshold of alpha/{N_LOOKS} per look: "
          f"false-positive rate = {reject_bonf / N_SIM:.4f}")

    # --------------------------------------------------------- summary
    summary.update({
        "effects": eff[cols + ["family", "test", "se"]].to_dict(orient="records"),
        "head_to_head": h2h.drop(columns="test").to_dict(orient="records"),
        "power": power.to_dict(orient="records"),
        "variance_reduction": var_red.to_dict(orient="records"),
        "guardrail": guard.to_dict(orient="records"),
        "heterogeneity_contrast": contrast.to_dict(orient="records"),
        "peeking": peek.to_dict(orient="records"),
        "peeking_bonferroni_fpr": reject_bonf / N_SIM,
    })
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print("\nwrote results/experiment/*.csv and summary.json")


if __name__ == "__main__":
    main()
