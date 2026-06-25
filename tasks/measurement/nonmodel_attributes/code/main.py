#!/usr/bin/env python3
"""
Purpose:
  Build nonmodel-attribute regression tables for the MMB outcomes.

Inputs:
  ../input/MMB_reg_format.dta
  ../../../../config/params.yaml

Outputs:
  ../output/nonmodel_attributes_full_sample.txt
  ../output/nonmodel_attributes_estimated_models.txt
  ../output/table9_nonmodel_attributes_full_sample.tex
  ../output/table9_nonmodel_attributes_full_sample.csv
  ../output/table9_nonmodel_attributes_estimated_models.tex
  ../output/table9_nonmodel_attributes_estimated_models.csv
  ../output/table9_nonmodel_attributes_full_sample_citation_weighted.tex
  ../output/table9_nonmodel_attributes_full_sample_citation_weighted.csv
  ../output/table9_nonmodel_attributes_estimated_models_citation_weighted.tex
  ../output/table9_nonmodel_attributes_estimated_models_citation_weighted.csv
  ../output/manifest.csv

Run:
  make
"""

from pathlib import Path
import shutil
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices
from statsmodels.robust import norms, scale


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
sys.path.append(str(Path(__file__).resolve().parents[2]))

from regression_table_tools import (
    apply_clustered_inference,
    build_table,
    cluster_groups,
    fit_model,
    formula_for,
    independent_design,
    load_regression_data,
    load_table_params,
    pseudo_r2,
    stars,
)


SPEC_KEY = "nonmodel_attributes"

params = load_table_params(__file__)
spec = params["table_specs"][SPEC_KEY]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for path in OUTPUT_DIR.iterdir():
    if path.name == ".gitkeep":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

df = load_regression_data(INPUT_DIR, params)
samples = [
    ("full_sample", "full sample", df),
    ("estimated_models", "estimated models", df.loc[df["estimated"] == 1].copy()),
]

outcome_order = [
    ("IScurve20", "\\textit{y-slope}"),
    ("infl_per_rr20", "\\textit{$\\pi$-slope}"),
    ("sacratio20", "\\textit{sacratio}"),
    ("y_timing_max", "\\textit{y-timing}"),
    ("piq_timing_max", "\\textit{$\\pi$-timing}"),
]

display_terms = [
    ("cb_authors_ext", "Central bank authors"),
    ("ln_neq", "Ln(Number of equations)"),
    ("vint_mid", "Middle vintage"),
    ("vint_late", "Late vintage"),
    ("cb_authors_ext:vint_late", "Central bank authors*Late vintage"),
]


def adjusted_r2(r2_value, nobs, nparams):
    # Use the standard finite-sample adjustment for the fit statistic reported in each column.
    if not np.isfinite(r2_value) or nobs <= nparams:
        return np.nan
    return 1.0 - (1.0 - r2_value) * (nobs - 1.0) / (nobs - nparams)


def weighted_design(depvar, sample_df):
    formula = formula_for(depvar, spec["variables"], sample_df, params)
    y, x = dmatrices(formula, data=sample_df, return_type="dataframe")
    weights = pd.to_numeric(sample_df.loc[x.index, "citation_weight"], errors="coerce")
    keep = weights.notna() & np.isfinite(weights) & (weights > 0)
    y = y.loc[keep].copy()
    x = x.loc[keep].copy()
    weights = weights.loc[keep].astype(float)
    weights = weights / weights.mean()
    y, x = independent_design(y, x)
    return y, x, weights.loc[x.index]


def fit_citation_weighted_model(depvar, sample_df):
    y, x, weights = weighted_design(depvar, sample_df)
    groups = cluster_groups(sample_df, x, params)
    glm_fit_kwargs = {"cov_type": "HC0"}
    if groups is not None:
        glm_fit_kwargs = {"cov_type": "cluster", "cov_kwds": {"groups": groups}}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # Timing outcomes keep the count-model logic, now using citation weights.
        if depvar in params["timing_outcomes"]:
            poisson = sm.GLM(y, x, family=sm.families.Poisson(), freq_weights=weights).fit(**glm_fit_kwargs)
            mu = poisson.fittedvalues.squeeze()
            aux_y = ((y.squeeze() - mu) ** 2) - y.squeeze()
            aux_x = mu ** 2
            aux = sm.WLS(aux_y, aux_x, weights=weights).fit(cov_type="HC0")
            alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
            p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0
            if p_over < 0.05 and alpha_hat > 0:
                nb = sm.families.NegativeBinomial(alpha=alpha_hat)
                fit = sm.GLM(y, x, family=nb, freq_weights=weights).fit(**glm_fit_kwargs)
            else:
                fit = poisson
            fit.fittedvalues_original = fit.fittedvalues.copy()
            fit.citation_weights = weights.copy()
            fit.nobs_unweighted = int(y.shape[0])
            return fit

        # RLM has no citation-weight argument, so apply the usual sqrt(weight) design transform.
        sqrt_weights = np.sqrt(weights)
        weighted_y = y.squeeze().mul(sqrt_weights, axis=0)
        weighted_x = x.mul(sqrt_weights, axis=0)
        fit = sm.RLM(weighted_y, weighted_x, M=norms.TukeyBiweight(c=4.685)).fit(
            scale_est=scale.HuberScale(),
            update_scale=True,
            cov="H1",
            conv="coefs",
        )
        fit = apply_clustered_inference(fit, weighted_x, weighted_y, groups, weights=fit.weights)
        fit.fittedvalues_original = pd.Series(
            np.asarray(x, dtype=float) @ fit.params.to_numpy(dtype=float),
            index=x.index,
        )
        fit.citation_weights = weights.copy()
        fit.nobs_unweighted = int(y.shape[0])
        return fit


def ordinary_r2_stats(depvar, sample_df, citation_weighted=False):
    # Elasticity columns report ordinary R-squared diagnostics for the same design matrix.
    if citation_weighted:
        y, x, weights = weighted_design(depvar, sample_df)
        model = sm.WLS(y.squeeze(), x, weights=weights).fit()
    else:
        y, x = dmatrices(formula_for(depvar, spec["variables"], sample_df, params), data=sample_df, return_type="dataframe")
        y, x = independent_design(y, x)
        model = sm.OLS(y.squeeze(), x).fit()
    return float(model.rsquared), float(model.rsquared_adj)


def robust_weighted_r2(fit, sample_df, depvar):
    # Combine citation weights, when present, with the RLM robustness weights.
    if not hasattr(fit, "weights"):
        return np.nan
    if hasattr(fit, "fittedvalues_original"):
        y = pd.to_numeric(sample_df.loc[fit.fittedvalues_original.index, depvar], errors="coerce").to_numpy(dtype=float)
        fitted = np.asarray(fit.fittedvalues_original, dtype=float)
        weights = np.asarray(fit.weights, dtype=float) * np.asarray(fit.citation_weights, dtype=float)
    else:
        y = pd.to_numeric(sample_df.loc[fit.fittedvalues.index, depvar], errors="coerce").to_numpy(dtype=float)
        fitted = np.asarray(fit.fittedvalues, dtype=float)
        weights = np.asarray(fit.weights, dtype=float)
    ybar = np.average(y, weights=weights)
    denom = np.sum(weights * (y - ybar) ** 2)
    if denom <= 0:
        return np.nan
    return 1.0 - np.sum(weights * (y - fitted) ** 2) / denom


def fit_see(fit, sample_df, depvar):
    if hasattr(fit, "fittedvalues_original"):
        y = pd.to_numeric(sample_df.loc[fit.fittedvalues_original.index, depvar], errors="coerce").to_numpy(dtype=float)
        resid = y - np.asarray(fit.fittedvalues_original, dtype=float)
        weights = np.asarray(fit.citation_weights, dtype=float)
    else:
        y = pd.to_numeric(sample_df.loc[fit.fittedvalues.index, depvar], errors="coerce").to_numpy(dtype=float)
        resid = y - np.asarray(fit.fittedvalues, dtype=float)
        weights = np.ones(len(y))
    df_resid = len(y) - len(fit.params)
    if df_resid <= 0:
        return np.nan
    return np.sqrt(np.sum(weights * resid ** 2) / df_resid)


def fit_r2(fit, sample_df, depvar):
    if hasattr(fit, "fittedvalues_original"):
        y = pd.to_numeric(sample_df.loc[fit.fittedvalues_original.index, depvar], errors="coerce").to_numpy(dtype=float)
        fitted = np.asarray(fit.fittedvalues_original, dtype=float)
        weights = np.asarray(fit.citation_weights, dtype=float)
        ybar = np.average(y, weights=weights)
        denom = np.sum(weights * (y - ybar) ** 2)
        if denom <= 0:
            return np.nan
        return 1.0 - np.sum(weights * (y - fitted) ** 2) / denom
    return pseudo_r2(fit, sample_df, depvar)


def latex_coef(fit, term):
    if term not in fit.params.index:
        return ""
    coef = float(fit.params[term])
    p_value = float(fit.pvalues[term]) if term in fit.pvalues.index else np.nan
    coef_text = f"{coef:.2f}"
    if coef_text == "-0.00":
        coef_text = "0.00"
    coef_stars = stars(p_value)
    if coef_stars:
        return f"${coef_text}^{{{coef_stars}}}$"
    if coef < 0:
        return f"${coef_text}$"
    return coef_text


def latex_se(fit, term):
    if term not in fit.bse.index:
        return ""
    se_text = f"{float(fit.bse[term]):.2f}"
    if se_text == "-0.00":
        se_text = "0.00"
    return f"({se_text})"


def stat_number(value):
    if isinstance(value, str):
        return value
    if not np.isfinite(value):
        return "--"
    text = f"{value:.2f}"
    if text == "-0.00":
        text = "0.00"
    return text


def build_manuscript_table(sample_name, sample_label, sample_df, citation_weighted=False):
    fits = {}
    diagnostics = {}
    source_rows = []

    for depvar, _ in outcome_order:
        if citation_weighted:
            fit = fit_citation_weighted_model(depvar, sample_df)
        else:
            fit = fit_model(depvar, spec["variables"], sample_df, params)
        fits[depvar] = fit
        nobs = float(fit.nobs_unweighted) if hasattr(fit, "nobs_unweighted") else float(fit.nobs)
        nparams = len(fit.params)

        if depvar in params["timing_outcomes"]:
            r2_value = fit_r2(fit, sample_df, depvar)
            rw2_value = "--"
        else:
            r2_value, adj_value = ordinary_r2_stats(depvar, sample_df, citation_weighted=citation_weighted)
            rw2_value = robust_weighted_r2(fit, sample_df, depvar)

        if depvar in params["timing_outcomes"]:
            adj_value = adjusted_r2(r2_value, nobs, nparams)

        diagnostics[depvar] = {
            "r2": r2_value,
            "adj_r2": adj_value,
            "rw2": rw2_value,
            "see": fit_see(fit, sample_df, depvar),
            "n": int(nobs),
        }

        for term in fit.params.index:
            source_rows.append(
                {
                    "sample": sample_name,
                    "citation_weighted": citation_weighted,
                    "outcome": depvar,
                    "term": term,
                    "coef": float(fit.params[term]),
                    "se": float(fit.bse[term]),
                    "p_value": float(fit.pvalues[term]) if term in fit.pvalues.index else np.nan,
                }
            )

    caption = "Effects of Non-Model Attributes on Macro Outcomes (full sample)"
    label = "tab:nonmodel_attributes"
    note_tail = "See Table~\\ref{tab:nonmodel_attributes_B} for statistics with estimated models only."
    output_stem = "table9_nonmodel_attributes_full_sample"
    if sample_name == "estimated_models":
        caption = "Effects of Non-Model Attributes on Macro Outcomes (estimated models only)"
        label = "tab:nonmodel_attributes_B"
        note_tail = "See Table~\\ref{tab:nonmodel_attributes} for full-sample statistics."
        output_stem = "table9_nonmodel_attributes_estimated_models"
    if citation_weighted:
        caption = caption.replace(")", ", citation weighted)")
        label = label + "_cw"
        output_stem = output_stem + "_citation_weighted"
        note_tail = note_tail + " Citation weights are age-adjusted, log-transformed, and normalized to mean one within each regression sample."

    if sample_name == "full_sample":
        controls_note = "Regressions include dummy variables for policy rules and for estimated models as controls. "
    else:
        controls_note = "Regressions include dummy variables for policy rules as controls. "

    latex_lines = [
        "\\begin{table}[H]",
        "\\centering",
        f"\\caption{{ \\\\ \\underline{{{caption}}} }}",
        f"\\label{{{label}}}",
        "",
        "\\begin{tabular}{l c c c c c}",
        "\\toprule",
        "& \\multicolumn{3}{c}{\\textbf{Elasticities}$^{\\dagger}$}",
        "& \\multicolumn{2}{c}{\\textbf{Timing}$^{\\dagger\\dagger}$} \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-6}",
        "& \\textit{y-slope} & \\textit{$\\pi$-slope} & \\textit{sacratio}",
        "& \\textit{y-timing} & \\textit{$\\pi$-timing} \\\\",
        "\\midrule",
        "",
    ]

    displayed_terms = [
        (term, label_text)
        for term, label_text in display_terms
        if any(term in fits[depvar].params.index for depvar, _ in outcome_order)
    ]

    for row_index, (term, label_text) in enumerate(displayed_terms):
        latex_lines.append(label_text)
        latex_lines.append("& " + " & ".join(latex_coef(fits[depvar], term) for depvar, _ in outcome_order) + " \\\\")
        latex_lines.append("& " + " & ".join(latex_se(fits[depvar], term) for depvar, _ in outcome_order) + " \\\\")
        if row_index < len(displayed_terms) - 1:
            latex_lines.append("\\addlinespace[0.5em]")
            latex_lines.append("")

    stat_rows = [
        ("$R^{2}$", "r2"),
        ("$\\bar{R}^{2}$", "adj_r2"),
        ("$R_{w}^{2}$", "rw2"),
        ("S.E.E.", "see"),
        ("$N$", "n"),
    ]

    latex_lines.extend(["", "\\midrule", ""])
    for row_label, stat_key in stat_rows:
        cells = []
        for depvar, _ in outcome_order:
            value = diagnostics[depvar][stat_key]
            if stat_key == "n":
                cells.append(str(int(value)))
            else:
                cells.append(stat_number(value))
        latex_lines.append(row_label + " & " + " & ".join(cells) + " \\\\")

    latex_lines.extend(
        [
            "",
            "\\bottomrule",
            "\\multicolumn{6}{p{14cm}}{\\footnotesize Notes: $\\dagger$ Robust least squares with standard errors clustered by model. See Table~\\ref{tab:baseline_reg} for details. $\\dagger\\dagger$ Timing columns are estimated by Poisson GLM, with a negative-binomial GLM used when an auxiliary overdispersion test rejects equidispersion. GLM covariances are clustered by model. See Table~\\ref{tab:baseline_reg} for details. " + controls_note + "Early vintage is the omitted vintage category. *, **, *** indicate statistical significance at 10, 5, and 1 percent, respectively. See Table~\\ref{tab:outcome_vars} for definitions of variables. " + note_tail + "}",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )

    tex_path = OUTPUT_DIR / f"{output_stem}.tex"
    csv_path = OUTPUT_DIR / f"{output_stem}.csv"
    tex_path.write_text("\n".join(latex_lines) + "\n", encoding="utf-8")

    for depvar, _ in outcome_order:
        for stat_key, stat_value in diagnostics[depvar].items():
            source_rows.append(
                {
                    "sample": sample_name,
                    "citation_weighted": citation_weighted,
                    "outcome": depvar,
                    "term": stat_key,
                    "coef": stat_value if not isinstance(stat_value, str) else np.nan,
                    "se": np.nan,
                    "p_value": np.nan,
                }
            )
    pd.DataFrame(source_rows).to_csv(csv_path, index=False)
    return tex_path, csv_path


manifest_rows = []
for sample_name, sample_label, sample_df in samples:
    table_path = OUTPUT_DIR / f"{SPEC_KEY}_{sample_name}.txt"
    title = f"{spec['title']} ({sample_label})"
    build_table(sample_df, spec["variables"], title, table_path, params)
    manifest_rows.append(
        {
            "file": table_path.name,
            "spec": SPEC_KEY,
            "sample": sample_name,
            "citation_weighted": False,
            "description": title,
        }
    )
    for citation_weighted in [False, True]:
        tex_path, csv_path = build_manuscript_table(
            sample_name,
            sample_label,
            sample_df,
            citation_weighted=citation_weighted,
        )
        weight_label = " citation-weighted" if citation_weighted else ""
        manifest_rows.append(
            {
                "file": tex_path.name,
                "spec": SPEC_KEY,
                "sample": sample_name,
                "citation_weighted": citation_weighted,
                "description": f"Manuscript LaTeX{weight_label} Table 9 for {sample_label}.",
            }
        )
        manifest_rows.append(
            {
                "file": csv_path.name,
                "spec": SPEC_KEY,
                "sample": sample_name,
                "citation_weighted": citation_weighted,
                "description": f"Source values for manuscript{weight_label} Table 9 for {sample_label}.",
            }
        )

manifest_rows.append(
    {
        "file": "manifest.csv",
        "spec": SPEC_KEY,
        "sample": "all",
        "citation_weighted": False,
        "description": "Manifest of nonmodel-attributes task outputs.",
    }
)
pd.DataFrame(manifest_rows).to_csv(OUTPUT_DIR / "manifest.csv", index=False)
