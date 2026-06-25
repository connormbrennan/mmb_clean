#!/usr/bin/env python3
"""
Purpose:
  Build paper regression tables from the MMB analysis dataset.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/paper_tables/

Run:
  make
"""

from pathlib import Path
import shutil
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices
from statsmodels.robust import norms, scale


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
TABLE_DIR = OUTPUT_DIR / "paper_tables"

FIXED_VARS = ["rule_g", "rule_itr", "estimated"]
OUTCOMES = ["IScurve20", "infl_per_rr20", "sacratio20", "y_timing_max", "piq_timing_max"]
TIMING_OUTCOMES = ["y_timing_max", "piq_timing_max"]
TIME_LIMIT = 99

TABLE_SPECS = {
    "policy_rules_estimation": [],
    "nominal_rigidities": [
        "stky_wg:wg_ndx",
        "stky_wg:not_wg_ndx",
        "pr_ndx",
    ],
    "real_rigidities": [
        "hh_demand",
        "bank",
        "firm_bs",
        "labor_frict",
        "open",
        "hh_demand:bank",
        "firm_bs:bank",
        "hh_demand:firm_bs",
        "hh_demand:open",
    ],
    "nonmodel_attributes": [
        "cb_authors_ext",
        "ln_neq",
        "vint_early",
        "vint_mid",
        "vint_late",
        "est_early",
        "est_late",
    ],
}

TABLE_SPECS["broad_model_variables"] = (
    TABLE_SPECS["nominal_rigidities"]
    + TABLE_SPECS["real_rigidities"]
    + TABLE_SPECS["nonmodel_attributes"]
)

VAR_LABELS = {
    "Intercept": "Constant",
    "rule_g": "Rule: Growth",
    "rule_itr": "Rule: Inertial Taylor",
    "estimated": "Estimated",
    "stky_wg": "Sticky wages",
    "wg_ndx": "Wage indexation",
    "not_wg_ndx": "Not wage indexed",
    "pr_ndx": "Price indexation",
    "hh_demand": "Constrained household demand",
    "bank": "Bank intermediation channel",
    "firm_bs": "Firm balance-sheet channel",
    "labor_frict": "Labor-market friction",
    "open": "Open economy",
    "cb_authors_ext": "Central bank authors",
    "ln_neq": "Log number of equations",
    "vint_early": "Early vintage",
    "vint_mid": "Middle vintage",
    "vint_late": "Late vintage",
    "est_early": "Early estimation sample",
    "est_late": "Late estimation sample",
}

OUTCOME_LABELS = {
    "IScurve20": "IS curve slope",
    "infl_per_rr20": "Inflation per real-rate response",
    "sacratio20": "Sacrifice ratio",
    "y_timing_max": "Output timing",
    "piq_timing_max": "Inflation timing",
}


def prepare_output():
    if TABLE_DIR.exists():
        shutil.rmtree(TABLE_DIR)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    df = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")
    df = df.loc[df["y_timing_max"] < TIME_LIMIT].copy()
    df = df.loc[df["piq_timing_max"] < TIME_LIMIT].copy()
    df["not_wg_ndx"] = 1 - df["wg_ndx"]
    return df


def active_controls(data):
    return [var for var in FIXED_VARS if data[var].nunique(dropna=True) > 1]


def formula_for(depvar, variables, data):
    rhs = active_controls(data) + variables
    if not rhs:
        return f"{depvar} ~ 1"
    return f"{depvar} ~ " + " + ".join(rhs)


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


def fit_model(depvar, variables, data):
    formula = formula_for(depvar, variables, data)
    y, x = dmatrices(formula, data=data, return_type="dataframe")
    y, x = independent_design(y, x)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if depvar in TIMING_OUTCOMES:
            poisson = sm.GLM(y, x, family=sm.families.Poisson()).fit(cov_type="HC0")
            mu = poisson.fittedvalues.squeeze()
            aux_y = ((y.squeeze() - mu) ** 2) - y.squeeze()
            aux_x = mu ** 2
            aux = sm.OLS(aux_y, aux_x).fit(cov_type="HC0")
            alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
            p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0
            if p_over < 0.05 and alpha_hat > 0:
                return sm.GLM(y, x, family=sm.families.NegativeBinomial(alpha=alpha_hat)).fit(cov_type="HC0")
            return poisson

        return sm.RLM(y.squeeze(), x, M=norms.TukeyBiweight(c=4.685)).fit(
            scale_est=scale.HuberScale(),
            update_scale=True,
            cov="H1",
            conv="coefs",
        )


def pseudo_r2(fit, data, depvar):
    y = pd.to_numeric(data.loc[fit.fittedvalues.index, depvar], errors="coerce")
    resid = y.to_numpy(dtype=float) - np.asarray(fit.fittedvalues, dtype=float)
    denom = np.sum((y.to_numpy(dtype=float) - y.mean()) ** 2)
    if denom <= 0:
        return np.nan
    return 1.0 - float(np.sum(resid ** 2)) / float(denom)


def stars(p_value):
    if not np.isfinite(p_value):
        return ""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


def label_for(term):
    if term in VAR_LABELS:
        return VAR_LABELS[term]
    if ":" in term:
        return " x ".join(VAR_LABELS.get(part, part) for part in term.split(":"))
    return term


def format_coef(fit, term):
    if term not in fit.params.index:
        return ""
    coef = float(fit.params[term])
    p_value = float(fit.pvalues[term]) if term in fit.pvalues.index else np.nan
    return f"{coef:.3f}{stars(p_value)}"


def format_se(fit, term):
    if term not in fit.bse.index:
        return ""
    return f"({float(fit.bse[term]):.3f})"


def write_table(path, title, fits, r2s):
    terms = []
    for fit in fits.values():
        for term in fit.params.index:
            if term not in terms:
                terms.append(term)
    terms = sorted(terms, key=lambda term: (term != "Intercept", term))

    lines = [
        title,
        "=" * len(title),
        "",
        "Coefficients are followed by robust standard errors in parentheses.",
        "Significance: * p<0.10, ** p<0.05, *** p<0.01.",
        "",
        "\t".join(["Variable"] + [OUTCOME_LABELS.get(dep, dep) for dep in fits]),
    ]
    for term in terms:
        lines.append("\t".join([label_for(term)] + [format_coef(fit, term) for fit in fits.values()]))
        lines.append("\t".join([""] + [format_se(fit, term) for fit in fits.values()]))
    lines.append("")
    lines.append("\t".join(["Observations"] + [str(int(fit.nobs)) for fit in fits.values()]))
    lines.append("\t".join(["Pseudo R2"] + [f"{r2s[dep]:.3f}" for dep in fits]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_table(data, spec_name, variables, sample_name):
    fits = {}
    r2s = {}
    for depvar in OUTCOMES:
        fit = fit_model(depvar, variables, data)
        fits[depvar] = fit
        r2s[depvar] = pseudo_r2(fit, data, depvar)
    path = TABLE_DIR / f"{spec_name}_{sample_name}.txt"
    title = f"{spec_name.replace('_', ' ').title()} ({sample_name.replace('_', ' ')})"
    write_table(path, title, fits, r2s)
    return path


prepare_output()
df = load_data()
samples = {
    "full_sample": df,
    "estimated_models": df.loc[df["estimated"] == 1].copy(),
}

manifest_rows = []
all_text = []
for spec_name, variables in TABLE_SPECS.items():
    for sample_name, sample_df in samples.items():
        path = build_table(sample_df, spec_name, variables, sample_name)
        manifest_rows.append({"file": str(path.relative_to(OUTPUT_DIR)), "spec": spec_name, "sample": sample_name})
        all_text.append(path.read_text(encoding="utf-8"))

combined = TABLE_DIR / "all_regression_tables.txt"
combined.write_text("\n\n".join(all_text), encoding="utf-8")
manifest_rows.append({"file": str(combined.relative_to(OUTPUT_DIR)), "spec": "all", "sample": "all"})
pd.DataFrame(manifest_rows).to_csv(TABLE_DIR / "manifest.csv", index=False)
