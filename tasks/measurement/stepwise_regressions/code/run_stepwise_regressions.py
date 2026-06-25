#!/usr/bin/env python3
"""
Purpose:
  Run bidirectional stepwise regressions for the MMB outcome and timing variables.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/stepwise_regressions/

Run:
  make
"""

from pathlib import Path
import shutil
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrices
from statsmodels.robust import norms, scale


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
TABLE_DIR = OUTPUT_DIR / "stepwise_regressions"

ALPHA_ENTER = 0.10
ALPHA_EXIT = 0.15
TIME_LIMIT = 99
FIXED_VARS = ["rule_g", "rule_itr", "estimated"]
HORIZONS = [20]
ELASTICITY_BASES = ["IScurve", "infl_per_rr", "sacratio"]
TIMING_DEPVARS = ["y_timing_max", "piq_timing_max"]

VARSETS = {
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
    "nonmod_attributes": [
        "cb_authors_ext",
        "ln_neq",
        "vint_early",
        "vint_mid",
        "est_early",
    ],
}

VARSETS["all"] = (
    VARSETS["nominal_rigidities"]
    + VARSETS["real_rigidities"]
    + VARSETS["nonmod_attributes"]
)

VARSETS["all_nominal_rigidities"] = [
    "stky_pr",
    "stky_wg",
    "pr_ndx",
    "wg_ndx",
    "stky_pr:pr_ndx",
    "stky_wg:wg_ndx",
    "stky_pr:not_pr_ndx",
    "stky_wg:not_wg_ndx",
    "stky_pr:wg_ndx",
    "stky_wg:pr_ndx",
    "stky_pr:not_wg_ndx",
    "stky_wg:not_pr_ndx",
]

VARSETS["all_real_rigidities"] = [
    "hh_demand",
    "firm_bs",
    "bank",
    "labor_frict",
    "open",
    "learning",
    "hh_demand:firm_bs",
    "hh_demand:bank",
    "hh_demand:labor_frict",
    "firm_bs:bank",
    "firm_bs:labor_frict",
    "bank:labor_frict",
    "hh_demand:open",
    "hh_demand:learning",
    "firm_bs:open",
    "firm_bs:learning",
    "bank:open",
    "bank:learning",
    "labor_frict:open",
    "labor_frict:learning",
    "open:learning",
]

VARSETS["all_nonmod_attributes"] = [
    "cb_authors_ext",
    "ln_neq",
    "vint_early",
    "vint_mid",
    "vint_late",
    "est_early",
    "est_late",
    "cb_authors_ext:ln_neq",
    "cb_authors_ext:vint_early",
    "cb_authors_ext:vint_mid",
    "cb_authors_ext:vint_late",
    "cb_authors_ext:est_early",
    "cb_authors_ext:est_late",
    "ln_neq:vint_early",
    "ln_neq:vint_mid",
    "ln_neq:vint_late",
    "ln_neq:est_early",
    "ln_neq:est_late",
    "vint_early:est_early",
    "vint_early:est_late",
    "vint_mid:est_early",
    "vint_mid:est_late",
    "vint_late:est_early",
    "vint_late:est_late",
]

VARSETS["all_all"] = (
    VARSETS["all_nominal_rigidities"]
    + VARSETS["all_real_rigidities"]
    + VARSETS["all_nonmod_attributes"]
)

VAR_LABELS = {
    "Intercept": "Constant",
    "rule_g": "Rule: Growth",
    "rule_itr": "Rule: Inertial Taylor",
    "estimated": "Estimated",
    "stky_pr": "Sticky prices",
    "stky_wg": "Sticky wages",
    "pr_ndx": "Price indexation",
    "wg_ndx": "Wage indexation",
    "not_pr_ndx": "Not price indexed",
    "not_wg_ndx": "Not wage indexed",
    "hh_demand": "Constrained household demand",
    "firm_bs": "Firm balance-sheet channel",
    "bank": "Bank intermediation channel",
    "labor_frict": "Labor-market friction",
    "open": "Open economy",
    "learning": "Learning",
    "cb_authors_ext": "Central bank authors",
    "ln_neq": "Log number of equations",
    "vint_early": "Early vintage",
    "vint_mid": "Middle vintage",
    "vint_late": "Late vintage",
    "est_early": "Early estimation sample",
    "est_late": "Late estimation sample",
}

DEPVAR_LABELS = {
    "IScurve20": "IS curve slope, h=20",
    "infl_per_rr20": "Inflation per real-rate response, h=20",
    "sacratio20": "Sacrifice ratio, h=20",
    "y_timing_max": "Output timing",
    "piq_timing_max": "Inflation timing",
}


def prepare_output():
    if TABLE_DIR.exists():
        shutil.rmtree(TABLE_DIR)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = OUTPUT_DIR / "manifest.csv"
    if manifest.exists():
        manifest.unlink()


def load_data():
    df = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")
    df = df.loc[df["y_timing_max"] < TIME_LIMIT].copy()
    df = df.loc[df["piq_timing_max"] < TIME_LIMIT].copy()
    df["not_pr_ndx"] = 1 - df["pr_ndx"]
    df["not_wg_ndx"] = 1 - df["wg_ndx"]
    return df


def build_formula(depvar, variables):
    rhs = list(FIXED_VARS) + list(variables)
    return f"{depvar} ~ " + " + ".join(rhs)


def formula_is_estimable(formula, data):
    try:
        _, x = dmatrices(formula, data=data, return_type="dataframe")
    except Exception:
        return False
    rank = np.linalg.matrix_rank(x)
    if rank < x.shape[1]:
        return False
    if x.shape[1] > 1 and np.linalg.cond(x) > 1e8:
        return False
    return True


def fit_rlm(depvar, variables, data):
    formula = build_formula(depvar, variables)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return smf.rlm(
            formula,
            data=data,
            M=norms.TukeyBiweight(c=4.685),
        ).fit(
            scale_est=scale.HuberScale(),
            update_scale=True,
            cov="H1",
            conv="coefs",
        )


def fit_count(depvar, variables, data):
    formula = build_formula(depvar, variables)
    d = data.loc[data[depvar] < TIME_LIMIT].copy()
    y, x = dmatrices(formula, data=d, return_type="dataframe")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        poisson = sm.GLM(y, x, family=sm.families.Poisson()).fit(cov_type="HC0")

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
            return sm.GLM(y, x, family=sm.families.NegativeBinomial(alpha=alpha_hat)).fit(cov_type="HC0")
    return poisson


def get_term_pvalue(fit, term):
    if term in fit.pvalues.index:
        return float(fit.pvalues[term])
    pieces = [idx for idx in fit.pvalues.index if idx.endswith(term) or idx == term]
    if pieces:
        return float(np.nanmin(fit.pvalues.loc[pieces]))
    return np.nan


def stepwise(depvar, candidates, data, model_kind):
    entered = []
    remaining = list(candidates)
    history = []

    for step in range(1, 101):
        best_var = None
        best_p = 1.0

        for var in list(remaining):
            trial = entered + [var]
            formula = build_formula(depvar, trial)
            if not formula_is_estimable(formula, data):
                continue
            try:
                fit = fit_rlm(depvar, trial, data) if model_kind == "rlm" else fit_count(depvar, trial, data)
            except Exception:
                continue
            pval = get_term_pvalue(fit, var)
            if np.isfinite(pval) and pval < ALPHA_ENTER and pval < best_p:
                best_var = var
                best_p = pval

        changed = False
        if best_var is not None:
            entered.append(best_var)
            remaining.remove(best_var)
            changed = True
            history.append({"step": step, "action": "enter", "variable": best_var, "p_value": best_p})

        while entered:
            try:
                fit = fit_rlm(depvar, entered, data) if model_kind == "rlm" else fit_count(depvar, entered, data)
            except Exception:
                break
            pvals = [(var, get_term_pvalue(fit, var)) for var in entered]
            finite = [(var, pval) for var, pval in pvals if np.isfinite(pval)]
            if not finite:
                break
            worst_var, worst_p = max(finite, key=lambda item: item[1])
            if worst_p <= ALPHA_EXIT:
                break
            entered.remove(worst_var)
            remaining.append(worst_var)
            changed = True
            history.append({"step": step, "action": "drop", "variable": worst_var, "p_value": worst_p})

        if not changed:
            break

    final_fit = fit_rlm(depvar, entered, data) if model_kind == "rlm" else fit_count(depvar, entered, data)
    return final_fit, entered, history


def pseudo_r2(fit, depvar, data):
    y = pd.to_numeric(data[depvar], errors="coerce")
    aligned = y.loc[fit.fittedvalues.index] if hasattr(fit.fittedvalues, "index") else y.dropna().iloc[: len(fit.fittedvalues)]
    resid = aligned.to_numpy(dtype=float) - np.asarray(fit.fittedvalues, dtype=float)
    denom = np.sum((aligned.to_numpy(dtype=float) - aligned.mean()) ** 2)
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


def format_coef(coef, p_value):
    if not np.isfinite(coef):
        return ""
    return f"{coef:.3f}{stars(p_value)}"


def format_se(se):
    if not np.isfinite(se):
        return ""
    return f"({se:.3f})"


def label_for(term):
    if term in VAR_LABELS:
        return VAR_LABELS[term]
    if ":" in term:
        return " x ".join(VAR_LABELS.get(part, part) for part in term.split(":"))
    return term


def write_table(path, title, fits, r2s, selected, histories):
    terms = []
    for fit in fits.values():
        terms.extend([term for term in fit.params.index if term not in terms])
    terms = sorted(terms, key=lambda term: (term != "Intercept", term))

    lines = [
        title,
        "=" * len(title),
        "",
        "Coefficients are followed by standard errors in parentheses.",
        "Significance: * p<0.10, ** p<0.05, *** p<0.01.",
        "",
    ]

    header = ["Variable"] + [DEPVAR_LABELS.get(dep, dep) for dep in fits]
    lines.append("\t".join(header))
    for term in terms:
        coef_cells = [label_for(term)]
        se_cells = [""]
        for depvar, fit in fits.items():
            coef = float(fit.params.get(term, np.nan))
            se = float(fit.bse.get(term, np.nan))
            p_value = float(fit.pvalues.get(term, np.nan))
            coef_cells.append(format_coef(coef, p_value))
            se_cells.append(format_se(se))
        lines.append("\t".join(coef_cells))
        lines.append("\t".join(se_cells))
    lines.append("")
    lines.append("\t".join(["Observations"] + [str(int(fit.nobs)) for fit in fits.values()]))
    lines.append("\t".join(["Pseudo R2"] + [f"{r2s[dep]:.3f}" for dep in fits]))
    lines.append("")
    lines.append("Selected variables")
    for depvar, variables in selected.items():
        lines.append(f"- {DEPVAR_LABELS.get(depvar, depvar)}: {', '.join(variables) if variables else '(none)'}")
    lines.append("")
    lines.append("Step history")
    for depvar, rows in histories.items():
        lines.append(f"- {DEPVAR_LABELS.get(depvar, depvar)}")
        if not rows:
            lines.append("  no candidate entered")
        for row in rows:
            lines.append(f"  step {row['step']}: {row['action']} {row['variable']} (p={row['p_value']:.4f})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


prepare_output()
df = load_data()
manifest_rows = []

for varset_name, candidates in VARSETS.items():
    fits = {}
    r2s = {}
    selected = {}
    histories = {}
    for base in ELASTICITY_BASES:
        for horizon in HORIZONS:
            depvar = f"{base}{horizon}"
            fit, entered, history = stepwise(depvar, candidates, df, "rlm")
            fits[depvar] = fit
            r2s[depvar] = pseudo_r2(fit, depvar, df)
            selected[depvar] = entered
            histories[depvar] = history
    output_path = TABLE_DIR / f"{varset_name}.txt"
    write_table(output_path, f"Stepwise robust outcome regressions: {varset_name}", fits, r2s, selected, histories)
    manifest_rows.append({"file": str(output_path.relative_to(OUTPUT_DIR)), "kind": "outcome", "varset": varset_name})

    fits = {}
    r2s = {}
    selected = {}
    histories = {}
    for depvar in TIMING_DEPVARS:
        fit, entered, history = stepwise(depvar, candidates, df, "count")
        fits[depvar] = fit
        r2s[depvar] = pseudo_r2(fit, depvar, df)
        selected[depvar] = entered
        histories[depvar] = history
    timing_name = varset_name.replace("nominal_rigidities", "nomrig").replace("real_rigidities", "realrig").replace("nonmod_attributes", "nonmod")
    output_path = TABLE_DIR / f"{timing_name}_timing.txt"
    write_table(output_path, f"Stepwise timing regressions: {varset_name}", fits, r2s, selected, histories)
    manifest_rows.append({"file": str(output_path.relative_to(OUTPUT_DIR)), "kind": "timing", "varset": varset_name})

pd.DataFrame(manifest_rows).to_csv(OUTPUT_DIR / "manifest.csv", index=False)
