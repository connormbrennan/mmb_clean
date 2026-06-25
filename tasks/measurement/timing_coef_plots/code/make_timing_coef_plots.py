#!/usr/bin/env python3
"""
Purpose:
  Estimate bivariate timing regressions and plot coefficients.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/coef_plots_timing/
  ../output/coef_plots_timing.zip
  ../output/coef_plots_timing_description.txt

Run:
  make
"""

from pathlib import Path
import os
import shutil
import warnings
import zipfile

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
PLOT_DIR = OUTPUT_DIR / "coef_plots_timing"

TIME_LIMIT = 60

NONMODEL_VARS = [
    "cb_authors_ext",
    "estimated",
    "calibrated",
    "ln_neq",
    "vint_early",
    "vint_mid",
    "vint_late",
    "est_early",
    "est_late",
]

MODEL_VARS = [
    "firm_bs",
    "bank",
    "hh_demand",
    "labor_frict",
    "other_channel",
    "learning",
    "open",
    "stky_pr",
    "stky_pr_calvo",
    "stky_pr_rotemberg",
    "stky_pr_other",
    "stky_wg",
    "wg_ndx",
    "pr_ndx",
]

OUTCOMES = [
    ("y_timing_max", "Output timing"),
    ("piq_timing_max", "Inflation timing"),
]

VAR_LABELS = {
    "cb_authors_ext": "Central bank authors",
    "estimated": "Estimated",
    "calibrated": "Calibrated",
    "ln_neq": "Log number of equations",
    "vint_early": "Early vintage",
    "vint_mid": "Middle vintage",
    "vint_late": "Late vintage",
    "est_early": "Early estimation sample",
    "est_late": "Late estimation sample",
    "firm_bs": "Firm balance-sheet channel",
    "bank": "Bank intermediation channel",
    "hh_demand": "Constrained household demand",
    "labor_frict": "Labor-market friction",
    "other_channel": "Any real channel",
    "learning": "Learning",
    "open": "Open economy",
    "stky_pr": "Sticky prices",
    "stky_pr_calvo": "Sticky prices, Calvo",
    "stky_pr_rotemberg": "Sticky prices, Rotemberg",
    "stky_pr_other": "Sticky prices, other",
    "stky_wg": "Sticky wages",
    "wg_ndx": "Wage indexation",
    "pr_ndx": "Price indexation",
    "rule_itr": "Rule: Inertial Taylor",
    "rule_g": "Rule: Growth",
    "Intercept": "Constant",
}


def prepare_output():
    if PLOT_DIR.exists():
        shutil.rmtree(PLOT_DIR)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    for path in [
        OUTPUT_DIR / "coef_plots_timing.zip",
        OUTPUT_DIR / "coef_plots_timing_description.txt",
        OUTPUT_DIR / "manifest.csv",
    ]:
        if path.exists():
            path.unlink()


def independent_design(y, x):
    keep = []
    rank = 0
    for col in x.columns:
        trial = x[keep + [col]]
        trial_rank = np.linalg.matrix_rank(trial.to_numpy(dtype=float))
        if trial_rank > rank:
            keep.append(col)
            rank = trial_rank
    return y, x[keep]


def fit_count_regression(df, depvar, covariate):
    formula = f"{depvar} ~ rule_itr + rule_g + {covariate}"
    cols = [depvar, "rule_itr", "rule_g", covariate]
    d = df.loc[df[depvar] < TIME_LIMIT, cols].dropna().copy()
    for col in cols:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna().copy()

    y, x = dmatrices(formula, data=d, return_type="dataframe")
    y, x = independent_design(y, x)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            poisson = sm.GLM(y, x, family=sm.families.Poisson()).fit(cov_type="HC0")
        except np.linalg.LinAlgError:
            poisson = sm.GLM(y, x, family=sm.families.Poisson()).fit()

    mu = poisson.fittedvalues.squeeze()
    aux_y = ((y.squeeze() - mu) ** 2) - y.squeeze()
    aux_x = mu ** 2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        aux = sm.OLS(aux_y, aux_x).fit(cov_type="HC0")
    alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
    p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0

    if p_over < 0.05 and alpha_hat > 0:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = sm.GLM(y, x, family=sm.families.NegativeBinomial(alpha=alpha_hat)).fit(cov_type="HC0")
        family = "negative binomial"
    else:
        fit = poisson
        family = "poisson"

    rows = []
    for term in [covariate, "rule_itr", "rule_g", "Intercept"]:
        rows.append(
            {
                "term": term,
                "coef": float(fit.params.get(term, np.nan)),
                "se": float(fit.bse.get(term, np.nan)),
                "p_value": float(fit.pvalues.get(term, np.nan)),
                "nobs": int(fit.nobs),
                "family": family,
            }
        )
    return {"covariate": covariate, "depvar": depvar, "rows": rows}


def collect_results(df, depvar, covariates):
    records = []
    for covariate in covariates:
        result = fit_count_regression(df, depvar, covariate)
        for row in result["rows"]:
            row["covariate"] = covariate
            records.append(row)
    return pd.DataFrame(records)


def draw_interest_plot(results, title, path):
    d = results.loc[results["term"] == results["covariate"]].copy()
    d["label"] = d["covariate"].map(VAR_LABELS).fillna(d["covariate"])
    d = d.iloc[::-1].reset_index(drop=True)

    fig_height = max(4.5, 0.34 * len(d) + 1.8)
    fig, ax = plt.subplots(figsize=(8.5, fig_height))
    y = np.arange(len(d))
    ci = 1.645 * d["se"].to_numpy(dtype=float)
    ax.errorbar(d["coef"], y, xerr=ci, fmt="D", markersize=4, color="#1f4e79", ecolor="#557a95", capsize=2)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d["label"])
    ax.set_xlabel("Log-count coefficient, 90% confidence interval")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def draw_rule_plot(results, title, path):
    d = results.loc[results["term"].isin(["rule_itr", "rule_g", "Intercept"])].copy()
    d["cov_label"] = d["covariate"].map(VAR_LABELS).fillna(d["covariate"])
    terms = ["rule_itr", "rule_g", "Intercept"]
    offsets = {"rule_itr": -0.18, "rule_g": 0.0, "Intercept": 0.18}
    colors = {"rule_itr": "#1f4e79", "rule_g": "#8c2d04", "Intercept": "#2f6f3e"}

    labels = list(dict.fromkeys(d["cov_label"].tolist()))[::-1]
    label_pos = {label: i for i, label in enumerate(labels)}

    fig_height = max(4.5, 0.34 * len(labels) + 1.8)
    fig, ax = plt.subplots(figsize=(8.5, fig_height))
    for term in terms:
        dt = d.loc[d["term"] == term].copy()
        yy = dt["cov_label"].map(label_pos).to_numpy(dtype=float) + offsets[term]
        ci = 1.645 * dt["se"].to_numpy(dtype=float)
        ax.errorbar(
            dt["coef"],
            yy,
            xerr=ci,
            fmt="o",
            markersize=4,
            color=colors[term],
            ecolor=colors[term],
            capsize=2,
            label=VAR_LABELS[term],
        )
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Log-count coefficient, 90% confidence interval")
    ax.set_title(title)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_description(path, depvar, group_name, plot_kind, n_regs):
    lines = [
        f"Figure: {path.name}",
        f"Dependent variable: {depvar}",
        f"Covariate group: {group_name}",
        f"Plot type: {plot_kind}",
        "Estimator: robust Poisson unless Wooldridge overdispersion test selects negative binomial.",
        "Specification: timing = constant + rule_itr + rule_g + one attribute variable.",
        f"Sample restriction: {depvar} < {TIME_LIMIT}.",
        "Intervals: 90 percent confidence intervals.",
        f"Number of bivariate regressions: {n_regs}",
        "Data source: ../input/MMB_reg_format.dta.",
    ]
    path.with_name(path.stem + "_description.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_archive():
    archive = OUTPUT_DIR / "coef_plots_timing.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PLOT_DIR.iterdir()):
            zf.write(path, path.relative_to(OUTPUT_DIR))


prepare_output()
df = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")

manifest_rows = []
for depvar, pretty_outcome in OUTCOMES:
    for group_name, covariates in [
        ("nonmodvars", NONMODEL_VARS),
        ("modvars", MODEL_VARS),
    ]:
        available_covariates = [var for var in covariates if var in df.columns]
        results = collect_results(df, depvar, available_covariates)

        stem = f"{depvar}_{group_name}_ofinterest"
        plot_path = PLOT_DIR / f"{stem}.pdf"
        draw_interest_plot(results, f"{pretty_outcome}: attribute coefficients", plot_path)
        write_description(plot_path, depvar, group_name, "attribute coefficient", len(available_covariates))
        manifest_rows.append({"file": str(plot_path.relative_to(OUTPUT_DIR)), "depvar": depvar, "group": group_name, "plot_type": "ofinterest"})

        stem = f"{depvar}_{group_name}_rules"
        plot_path = PLOT_DIR / f"{stem}.pdf"
        draw_rule_plot(results, f"{pretty_outcome}: rule coefficients", plot_path)
        write_description(plot_path, depvar, group_name, "rule coefficients", len(available_covariates))
        manifest_rows.append({"file": str(plot_path.relative_to(OUTPUT_DIR)), "depvar": depvar, "group": group_name, "plot_type": "rules"})

pd.DataFrame(manifest_rows).to_csv(OUTPUT_DIR / "manifest.csv", index=False)
(OUTPUT_DIR / "coef_plots_timing_description.txt").write_text(
    "Timing coefficient plots generated from Python count regressions on ../input/MMB_reg_format.dta.\n",
    encoding="utf-8",
)
make_archive()

