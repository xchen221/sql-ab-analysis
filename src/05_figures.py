"""Figures for the README, drawn from the CSVs in results/ (no recomputation here)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from config import FIGURES, RESULTS

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
ARM_COLOR = {"Mens E-Mail": "#2a78d6", "Womens E-Mail": "#eb6834"}   # fixed per arm
SINGLE = "#2a78d6"
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "lines.linewidth": 2, "savefig.dpi": 160, "savefig.bbox": "tight",
})

OL = RESULTS / "olist"
EX = RESULTS / "experiment"


def monthly_gmv():
    df = pd.read_csv(OL / "q02_monthly_gmv.csv", parse_dates=["month"])
    df = df[df.in_window]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.plot(df.month, df.gmv / 1e3, color=SINGLE, marker="o", markersize=4)
    peak = df.loc[df.gmv.idxmax()]
    ax.annotate(f"Nov 2017 (Black Friday)\n{peak.gmv / 1e6:.2f}M BRL, {peak.gmv_mom_pct:+.0f}% MoM",
                xy=(peak.month, peak.gmv / 1e3), xytext=(-14, 0), textcoords="offset points",
                ha="right", va="center", color=INK_2, fontsize=9)
    ticks = df.month[::3]
    ax.set_xticks(ticks, [d.strftime("%b %Y") for d in ticks])
    ax.set_ylabel("GMV, thousand BRL")
    ax.set_ylim(0, 1350)
    ax.grid(axis="x", visible=False)
    ax.set_title("Olist monthly GMV (items + freight, sale orders)")
    fig.savefig(FIGURES / "01_monthly_gmv.png")
    plt.close(fig)


def cohort_heatmap():
    df = pd.read_csv(OL / "q03_cohort_retention.csv", parse_dates=["cohort_month"])
    wide = df[df.months_since.between(1, 12)].pivot(index="cohort_month", columns="months_since",
                                                    values="pct_retained")
    wide = wide.dropna(how="all")                      # last cohort has no observable month yet
    sizes = df.drop_duplicates("cohort_month").set_index("cohort_month").n_customers
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    data = np.ma.masked_invalid(wide.to_numpy())
    im = ax.imshow(data, cmap=BLUES, aspect="auto", vmin=0, vmax=np.nanmax(wide.to_numpy()))
    ax.set_xticks(range(wide.shape[1]), wide.columns)
    ax.set_yticks(range(wide.shape[0]),
                  [f"{d:%Y-%m}  (n={sizes[d]:,})" for d in wide.index])
    ax.set_xlabel("Months since first purchase")
    ax.set_ylabel("Cohort (first-purchase month)")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("% of cohort buying again that month", color=INK_2)
    cb.outline.set_visible(False)
    ax.set_title("Monthly repeat-purchase rate by cohort (blank = not yet observable)")
    fig.savefig(FIGURES / "02_cohort_retention.png")
    plt.close(fig)


def delivery_review():
    df = pd.read_csv(OL / "q05_delivery_vs_review.csv").sort_values("bucket_order")
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(df))
    ax.bar(x, df.avg_score, width=0.6, color=SINGLE, edgecolor=SURFACE, linewidth=2)
    for xi, (score, share) in enumerate(zip(df.avg_score, df.pct_of_orders)):
        ax.text(xi, score + 0.08, f"{score:.2f}", ha="center", color=INK, fontsize=9)
        ax.text(xi, 0.12, f"{share:.1f}%\nof orders" if xi == 0 else f"{share:.1f}%",
                ha="center", va="bottom", color=SURFACE, fontsize=8)
    ax.set_xticks(x, df.delivery_bucket, rotation=20, ha="right")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average review score (1-5)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Review score by delivery date vs. promised date (association, not causal)")
    fig.savefig(FIGURES / "03_delivery_vs_review.png")
    plt.close(fig)


def effects_forest():
    eff = pd.read_csv(EX / "effects.csv")
    panels = [("visit", 100, "percentage points", "Visit rate"),
              ("conversion", 100, "percentage points", "Conversion rate"),
              ("spend", 1, "dollars per customer", "Spend per customer")]
    fig, axes = plt.subplots(1, 3, figsize=(9, 2.8))
    for ax, (metric, scale, unit, title) in zip(axes, panels):
        d = eff[eff.metric == metric].reset_index(drop=True)
        for i, row in d.iterrows():
            y = 1 - i
            c = ARM_COLOR[row.treatment]
            ax.plot([row.ci_low * scale, row.ci_high * scale], [y, y], color=c, lw=2,
                    solid_capstyle="round")
            ax.plot(row["diff"] * scale, y, "o", color=c, markersize=8,
                    markeredgecolor=SURFACE, markeredgewidth=2)
            ax.text(row.ci_high * scale, y + 0.18, f"{row['diff'] * scale:+.2f}", ha="right",
                    color=INK, fontsize=9)
        ax.axvline(0, color=INK_2, lw=0.8)
        ax.set_yticks([1, 0], ["Mens e-mail", "Womens e-mail"] if ax is axes[0] else ["", ""])
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(min(0, d.ci_low.min() * scale) - 0.05 * d.ci_high.max() * scale,
                    d.ci_high.max() * scale * 1.12)
        ax.set_xlabel(unit)
        ax.grid(axis="y", visible=False)
        ax.set_title(title)
    fig.suptitle("Effect vs. no e-mail (point estimate and 95% CI), n = 21.3k per arm",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=1.04)
    fig.savefig(FIGURES / "04_experiment_effects.png")
    plt.close(fig)


def heterogeneity():
    het = pd.read_csv(EX / "heterogeneity_subgroups.csv")
    groups = ["mens only", "womens only", "both"]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    offsets = {"Mens E-Mail": -0.12, "Womens E-Mail": 0.12}
    for arm, off in offsets.items():
        d = het[het.treatment == arm].set_index("past_category").loc[groups]
        x = np.arange(len(groups)) + off
        ax.vlines(x, d.ci_low * 100, d.ci_high * 100, color=ARM_COLOR[arm], lw=2)
        ax.plot(x, d["diff"] * 100, "o", color=ARM_COLOR[arm], markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, label=arm.replace("E-Mail", "e-mail"))
    w = het[(het.treatment == "Womens E-Mail") & (het.past_category == "mens only")].iloc[0]
    ax.annotate(f"Womens e-mail barely moves\nmens-only buyers: {w['diff'] * 100:+.1f} pp",
                xy=(0.12, w["diff"] * 100), xytext=(0.35, 2.0), color=INK_2, fontsize=9,
                arrowprops={"arrowstyle": "-", "color": INK_2, "lw": 0.8})
    ax.axhline(0, color=INK_2, lw=0.8)
    ax.set_xticks(range(len(groups)), [f"bought {g} last year" for g in groups])
    ax.set_ylabel("Visit-rate lift, pp")
    ax.set_ylim(-1, None)
    ax.set_xlim(-0.5, 2.5)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Visit-rate lift by past purchase category (95% CI)")
    fig.savefig(FIGURES / "05_heterogeneity.png")
    plt.close(fig)


def peeking():
    pk = pd.read_csv(EX / "peeking_simulation.csv")
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.fill_between(pk.n_looks, (pk.false_positive_rate - 1.96 * pk.mc_se) * 100,
                    (pk.false_positive_rate + 1.96 * pk.mc_se) * 100, color=SINGLE, alpha=0.15,
                    linewidth=0)
    ax.plot(pk.n_looks, pk.false_positive_rate * 100, color=SINGLE, marker="o", markersize=6)
    ax.axhline(5, color=INK_2, lw=1, ls="--")
    ax.text(pk.n_looks.max(), 5.8, "nominal 5%", ha="right", color=INK_2, fontsize=9)
    for k in [1, 10, 50]:
        r = pk[pk.n_looks == k].iloc[0]
        ax.text(k, r.false_positive_rate * 100 + 2.2, f"{r.false_positive_rate * 100:.1f}%",
                ha="center", color=INK, fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks(pk.n_looks, pk.n_looks)
    ax.minorticks_off()
    ax.set_ylim(0, 40)
    ax.set_xlabel("Number of interim looks (stop at the first p < 0.05)")
    ax.set_ylabel("False-positive rate, %")
    ax.set_title("A/A simulation on the control arm: peeking inflates false positives")
    fig.savefig(FIGURES / "06_peeking.png")
    plt.close(fig)


def main():
    FIGURES.mkdir(exist_ok=True)
    for f in [monthly_gmv, cohort_heatmap, delivery_review, effects_forest, heterogeneity, peeking]:
        f()
        print(f"  {f.__name__}")


if __name__ == "__main__":
    main()
