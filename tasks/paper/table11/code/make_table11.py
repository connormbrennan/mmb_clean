#!/usr/bin/env python3
"""
Purpose:
  Build the two Table 11 specifications from the MMB analysis dataset.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/table11/billway.txt
  ../output/table11/connorway.txt

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
TABLE_DIR = OUTPUT_DIR / "table11"

FIXED_VARS = ["rule_g", "rule_itr", "estimated"]
OUTCOMES = ["IScurve20", "infl_per_rr20", "sacratio20", "y_timing_max", "piq_timing_max"]
TIMING_OUTCOMES = ["y_timing_max", "piq_timing_max"]
TIME_LIMIT = 99

SPECS = {
    "billway": [
        "stky_wg:wg_ndx",
        "stky_wg:not_wg_ndx",
        "pr_ndx",
        "firm_bs:bank",
        "hh_demand:firm_bs",
        "hh_demand:open",
        "firm_bs",
        "hh_demand",
        "labor_frict",
        "cb_authors_ext",
        "vint_early",
        "vint_mid",
    ],
    "connorway": [
        "stky_wg:wg_ndx",
        "stky_wg:not_wg_ndx",
        "pr_ndx",
        "firm_bs:bank",
        "hh_demand:open",
        "firm_bs",
        "hh_demand",
        "bank",
        "labor_frict",
        "open",
        "cb_authors_ext",
        "vint_mid",
        "vint_late",
        "cb_authors_ext:vint_late",
    ],
}

VAR_LABELS = {
    "Intercept": "Constant",
    "rule_g": "Rule: Growth",
    "rule_itr": "Rule: Inertial Taylor",
    "estimated": "Estimated",
    "stky_wg": "Sticky wages",
    "wg_ndx": "Wage indexation",
    "not_wg_ndx": "Not wage indexed",
    "pr_ndx": "Price indexation",
    "firm_bs": "Firm balance-sheet channel",
    "bank": "Bank intermediation channel",
    "hh_demand": "Constrained household demand",
    "labor_frict": "Labor-market friction",
    "open": "Open economy",
    "cb_authors_ext": "Central bank authors",
    "vint_early": "Early vintage",
    "vint_mid": "Middle vintage",
    "vint_late": "Late vintage",
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


def formula_for(depvar, variables):
    return f"{depvar} ~ " + " + ".join(FIXED_VARS + variables)


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
    y, x = dmatrices(formula_for(depvar, variables), data=data, return_type="dataframe")
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
        coef_cells = [label_for(term)]
        se_cells = [""]
        for fit in fits.values():
            if term in fit.params.index:
                coef = float(fit.params[term])
                se = float(fit.bse[term])
                p_value = float(fit.pvalues[term]) if term in fit.pvalues.index else np.nan
                coef_cells.append(f"{coef:.3f}{stars(p_value)}")
                se_cells.append(f"({se:.3f})")
            else:
                coef_cells.append("")
                se_cells.append("")
        lines.append("\t".join(coef_cells))
        lines.append("\t".join(se_cells))
    lines.append("")
    lines.append("\t".join(["Observations"] + [str(int(fit.nobs)) for fit in fits.values()]))
    lines.append("\t".join(["Pseudo R2"] + [f"{r2s[dep]:.3f}" for dep in fits]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


prepare_output()
df = load_data()
manifest_rows = []
for spec_name, variables in SPECS.items():
    fits = {}
    r2s = {}
    for depvar in OUTCOMES:
        fit = fit_model(depvar, variables, df)
        fits[depvar] = fit
        r2s[depvar] = pseudo_r2(fit, df, depvar)
    path = TABLE_DIR / f"{spec_name}.txt"
    write_table(path, f"Table 11: {spec_name}", fits, r2s)
    manifest_rows.append({"file": str(path.relative_to(OUTPUT_DIR)), "spec": spec_name})
pd.DataFrame(manifest_rows).to_csv(TABLE_DIR / "manifest.csv", index=False)
