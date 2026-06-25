#!/usr/bin/env python3
"""
Purpose:
  Estimate bivariate robust outcome regressions and plot coefficients.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/coef_plots_outcomes/
  ../output/coef_plots_outcomes.zip
  ../output/coef_plots_outcomes_description.txt

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
import statsmodels.formula.api as smf
from statsmodels.robust import norms, scale


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
PLOT_DIR = OUTPUT_DIR / "coef_plots_outcomes"

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
    ("IScurve", "IS", "IS curve slope"),
    ("sacratio", "sac", "Sacrifice ratio"),
    ("Billsacrat", "Billsac", "Bill sacrifice ratio"),
    ("infl_per_rr", "ipr", "Inflation response per real-rate response"),
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
    "rule_tr": "Rule: Taylor",
    "rule_g": "Rule: Growth",
    "Intercept": "Constant",
}


def prepare_output():
    if PLOT_DIR.exists():
        shutil.rmtree(PLOT_DIR)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    for path in [
        OUTPUT_DIR / "coef_plots_outcomes.zip",
        OUTPUT_DIR / "coef_plots_outcomes_description.txt",
        OUTPUT_DIR / "manifest.csv",
    ]:
        if path.exists():
            path.unlink()


def fit_outcome_regression(df, depvar, covariate):
    cols = [depvar, "rule_tr", "rule_g", covariate]
    d = df[cols].dropna().copy()
    for col in cols:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna().copy()

    formula = f"{depvar} ~ rule_tr + rule_g + {covariate}"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = smf.rlm(
            formula,
            data=d,
            M=norms.TukeyBiweight(c=4.685),
        ).fit(
            scale_est=scale.HuberScale(),
            update_scale=True,
            cov="H1",
            conv="coefs",
        )

    resid = d[depvar].to_numpy(dtype=float) - fit.fittedvalues.to_numpy(dtype=float)
    y = d[depvar].to_numpy(dtype=float)
    r2 = 1.0 - float(np.sum(resid ** 2)) / float(np.sum((y - y.mean()) ** 2))

    rows = []
    for term in [covariate, "rule_tr", "rule_g", "Intercept"]:
        rows.append(
            {
                "term": term,
                "coef": float(fit.params.get(term, np.nan)),
                "se": float(fit.bse.get(term, np.nan)),
                "p_value": float(fit.pvalues.get(term, np.nan)),
                "nobs": int(fit.nobs),
                "r2": r2,
            }
        )
    return {"covariate": covariate, "depvar": depvar, "rows": rows}


def collect_results(df, depvar, covariates):
    records = []
    for covariate in covariates:
        result = fit_outcome_regression(df, depvar, covariate)
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
    ax.set_xlabel("Coefficient, 90% confidence interval")
    ax.set_title(title)
    for yi, (_, row) in zip(y, d.iterrows()):
        ax.text(ax.get_xlim()[1], yi, f"  R2={row['r2']:.2f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def draw_rule_plot(results, title, path):
    d = results.loc[results["term"].isin(["rule_tr", "rule_g", "Intercept"])].copy()
    d["cov_label"] = d["covariate"].map(VAR_LABELS).fillna(d["covariate"])
    terms = ["rule_tr", "rule_g", "Intercept"]
    offsets = {"rule_tr": -0.18, "rule_g": 0.0, "Intercept": 0.18}
    colors = {"rule_tr": "#1f4e79", "rule_g": "#8c2d04", "Intercept": "#2f6f3e"}

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
    ax.set_xlabel("Coefficient, 90% confidence interval")
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
        "Estimator: robust linear model with Tukey biweight loss.",
        "Specification: outcome = constant + rule_tr + rule_g + one attribute variable.",
        "Intervals: 90 percent confidence intervals.",
        f"Number of bivariate regressions: {n_regs}",
        "Data source: ../input/MMB_reg_format.dta.",
    ]
    path.with_name(path.stem + "_description.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_archive():
    archive = OUTPUT_DIR / "coef_plots_outcomes.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PLOT_DIR.iterdir()):
            zf.write(path, path.relative_to(OUTPUT_DIR))


prepare_output()
df = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")

manifest_rows = []
for horizon in [20, 40, 60]:
    for base_name, prefix, pretty_outcome in OUTCOMES:
        depvar = f"{base_name}{horizon}"
        for group_name, covariates in [
            ("nonmodvars", NONMODEL_VARS),
            ("modvars", MODEL_VARS),
        ]:
            available_covariates = [var for var in covariates if var in df.columns]
            results = collect_results(df, depvar, available_covariates)

            stem = f"{prefix}{horizon}_{group_name}_ofinterest"
            plot_path = PLOT_DIR / f"{stem}.pdf"
            draw_interest_plot(
                results,
                f"{pretty_outcome}, horizon {horizon}: attribute coefficients",
                plot_path,
            )
            write_description(plot_path, depvar, group_name, "attribute coefficient", len(available_covariates))
            manifest_rows.append({"file": str(plot_path.relative_to(OUTPUT_DIR)), "depvar": depvar, "group": group_name, "plot_type": "ofinterest"})

            stem = f"{prefix}{horizon}_{group_name}_rules"
            plot_path = PLOT_DIR / f"{stem}.pdf"
            draw_rule_plot(
                results,
                f"{pretty_outcome}, horizon {horizon}: rule coefficients",
                plot_path,
            )
            write_description(plot_path, depvar, group_name, "rule coefficients", len(available_covariates))
            manifest_rows.append({"file": str(plot_path.relative_to(OUTPUT_DIR)), "depvar": depvar, "group": group_name, "plot_type": "rules"})

pd.DataFrame(manifest_rows).to_csv(OUTPUT_DIR / "manifest.csv", index=False)
(OUTPUT_DIR / "coef_plots_outcomes_description.txt").write_text(
    "Outcome coefficient plots generated from robust bivariate Python regressions on ../input/MMB_reg_format.dta.\n",
    encoding="utf-8",
)
make_archive()

