#!/usr/bin/env python3
"""
LASSO stress test for MMB regression outcomes.

Elasticity outcomes:
  - Belloni-Chernozhukov-style feasible square-loss LASSO after residualizing
    the outcome and candidate features against policy-rule / estimation controls

Timing outcomes:
  - Poisson L1 screen with policy-rule / estimation controls included but
    unpenalized

Covariates:
  - All detected covariates in MMB_reg_format.dta
  - All pairwise (bivariate) interactions of those covariates

Inputs:
  - ../input/MMB_reg_format.dta

Outputs:
  - ../output/lasso/

Run:
  make
"""


from itertools import combinations
from math import comb
from pathlib import Path
import json
import shutil
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from sklearn.linear_model import Lasso


RANDOM_STATE = 42
ZERO_TOL = 1e-8
MIN_MODELS_FOR_BINARY_FEATURE = 5
BC_C = 1.1
BC_GAMMA_BASE = 0.1
BC_SCREENING_MULTIPLIER = 0.5
BC_MAX_LOADINGS_ITER = 15
BC_LOADINGS_TOL = 1e-3
BC_MIN_LOADING = 1e-6
TIMING_SENTINEL = 99


ELASTICITY_OUTCOMES = {
    "IScurve20": "y-slope",
    "infl_per_rr20": "pi-slope",
    "sacratio20": "sacratio",
}

TIMING_OUTCOMES = {
    "y_timing_max": "y-timing",
    "piq_timing_max": "pi-timing",
}

ALL_OUTCOMES = list(ELASTICITY_OUTCOMES.keys()) + list(TIMING_OUTCOMES.keys())


PAPER_BASE_COVARIATES = [
    # Policy-rule / estimation controls used in paper regressions
    "rule_itr",
    "rule_g",
    "estimated",
    # Nominal-rigidity primitives
    "stky_wg",
    "wg_ndx",
    "pr_ndx",
    # Real-rigidity primitives
    "firm_bs",
    "bank",
    "hh_demand",
    "labor_frict",
    "open",
    # Non-model primitives
    "cb_authors_ext",
    "ln_neq",
    "vint_mid",
    "vint_late",
]

FIXED_EFFECT_COLUMNS = [
    "rule_itr",
    "rule_g",
    "estimated",
]

EXCLUDE_FROM_INTERACTIONS = [
    "rule_itr",
    "rule_g",
]


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
sys.path.append(str(Path(__file__).resolve().parents[2]))

from regression_table_tools import apply_clustered_inference, independent_design


FEATURE_LABELS = {
    "rule_itr": "Inertial Taylor rule",
    "rule_g": "Growth rule",
    "estimated": "Estimated",
    "stky_wg": "Sticky wage",
    "wg_ndx": "Wage indexation",
    "pr_ndx": "Price indexation",
    "firm_bs": "Firm Balance Sheet",
    "bank": "Bank Lending",
    "hh_demand": "Constr. HH Demand",
    "labor_frict": "Labor Friction",
    "open": "Open economy",
    "cb_authors_ext": "Central bank authors",
    "ln_neq": "Ln(Number of equations)",
    "vint_mid": "Middle vintage",
    "vint_late": "Late vintage",
}


def get_covariate_frame(df):
    missing = [c for c in PAPER_BASE_COVARIATES if c not in df.columns]
    if missing:
        raise KeyError(f"Missing expected paper covariate columns: {missing}")

    x = df[PAPER_BASE_COVARIATES].copy()

    # Impute with median and drop zero-variance columns.
    for c in x.columns:
        x[c] = x[c].astype(float)
        med = x[c].median()
        x[c] = x[c].fillna(med if pd.notna(med) else 0.0)

    keep = []
    for c in x.columns:
        if np.nanstd(x[c].to_numpy(dtype=float)) > 0:
            keep.append(c)
    x = x[keep].copy()

    return x


def add_pairwise_interactions(x):
    out = x.copy()
    cols = [c for c in x.columns if c not in EXCLUDE_FROM_INTERACTIONS]
    interactions = {}
    for a, b in combinations(cols, 2):
        interactions[f"{a}__x__{b}"] = x[a].to_numpy() * x[b].to_numpy()
    if interactions:
        out = pd.concat([out, pd.DataFrame(interactions, index=x.index)], axis=1)
    return out


def filter_sparse_binary_features(
    x,
    model_ids,
    min_models_for_one = MIN_MODELS_FOR_BINARY_FEATURE,
):
    keep_cols = []
    dropped_rows = []

    # Ensure aligned index.
    mids = model_ids.loc[x.index].astype(str)

    for c in x.columns:
        vals = x[c].to_numpy(dtype=float)
        uniq = np.unique(np.round(vals, 12))
        is_binary_like = np.all(np.isin(uniq, [0.0, 1.0]))

        if is_binary_like:
            n_models_with_one = int(pd.Index(mids[vals == 1.0]).nunique())
            if n_models_with_one < min_models_for_one:
                dropped_rows.append(
                    {
                        "feature": c,
                        "n_models_with_value_1": n_models_with_one,
                    }
                )
                continue

        keep_cols.append(c)

    dropped_df = pd.DataFrame(dropped_rows).sort_values(
        "n_models_with_value_1", ascending=True
    ) if dropped_rows else pd.DataFrame(columns=["feature", "n_models_with_value_1"])

    return x[keep_cols].copy(), dropped_df


def residualize_wrt_fixed_effects(
    y,
    x,
    fe,
    weights = None,
):
    if fe.shape[1] == 0:
        return y.copy(), x.copy()

    y_np = y.to_numpy(dtype=float)
    x_np = x.to_numpy(dtype=float)
    fe_np = fe.to_numpy(dtype=float)

    # Include an intercept in the projection space.
    f = np.column_stack([np.ones(len(y_np)), fe_np])
    if weights is None:
        p = f @ np.linalg.pinv(f)
    else:
        w = np.asarray(weights, dtype=float)
        w = w / np.nanmean(w)
        fw = f * w[:, None]
        p = f @ np.linalg.pinv(fw.T @ f) @ fw.T

    y_res = y_np - p @ y_np
    x_res = x_np - p @ x_np

    y_out = pd.Series(y_res, index=y.index, name=y.name)
    x_out = pd.DataFrame(x_res, index=x.index, columns=x.columns)
    return y_out, x_out


def weighted_mean(values, weights):
    if weights is None:
        return np.nanmean(values, axis=0)
    return np.average(values, axis=0, weights=weights)


def weighted_rms(values, weights):
    if weights is None:
        return np.sqrt(np.nanmean(values ** 2, axis=0))
    return np.sqrt(np.average(values ** 2, axis=0, weights=weights))


def bc_penalty_level(nobs, nfeatures):
    # Belloni-Chernozhukov-style high-dimensional penalty level.
    gamma = BC_GAMMA_BASE / np.log(max(nobs, 3))
    return (
        BC_SCREENING_MULTIPLIER
        * 2.0
        * BC_C
        * np.sqrt(nobs)
        * norm.ppf(1.0 - gamma / (2.0 * max(nfeatures, 1)))
    )


def fit_bc_lasso(
    x,
    y,
    sample_weights = None,
):
    x_np = x.to_numpy(dtype=float)
    y_np = y.to_numpy(dtype=float)
    nobs, nfeatures = x_np.shape
    if nfeatures == 0:
        return pd.Series(dtype=float), np.nan, np.nan

    weights = None
    if sample_weights is not None:
        weights = np.asarray(sample_weights, dtype=float)
        weights = weights / np.nanmean(weights)

    # Residualization already includes an intercept. Recenter here to absorb
    # small numerical drift and to make fit_intercept=False transparent.
    x_center = weighted_mean(x_np, weights)
    x_dm = x_np - x_center
    x_scale = weighted_rms(x_dm, weights)
    x_scale = np.where(x_scale <= 0, 1.0, x_scale)
    x_std = x_dm / x_scale

    y_center = weighted_mean(y_np, weights)
    y_dm = y_np - y_center

    lambda_value = bc_penalty_level(nobs, nfeatures)
    alpha_value = lambda_value / (2.0 * nobs)

    loadings = weighted_rms(x_std * y_dm[:, None], weights)
    loadings = np.where(loadings <= BC_MIN_LOADING, BC_MIN_LOADING, loadings)

    beta_std = np.zeros(nfeatures)
    sqrt_weights = None if weights is None else np.sqrt(weights)

    for _ in range(BC_MAX_LOADINGS_ITER):
        x_loaded = x_std / loadings
        if sqrt_weights is None:
            x_fit = x_loaded
            y_fit = y_dm
        else:
            x_fit = x_loaded * sqrt_weights[:, None]
            y_fit = y_dm * sqrt_weights

        model = Lasso(
            alpha=float(alpha_value),
            fit_intercept=False,
            max_iter=50000,
            tol=1e-7,
            selection="cyclic",
        )
        model.fit(x_fit, y_fit)
        beta_next = model.coef_ / loadings
        resid = y_dm - x_std @ beta_next
        next_loadings = weighted_rms(x_std * resid[:, None], weights)
        next_loadings = np.where(next_loadings <= BC_MIN_LOADING, BC_MIN_LOADING, next_loadings)

        diff = np.max(np.abs(next_loadings - loadings) / np.maximum(loadings, BC_MIN_LOADING))
        beta_std = beta_next
        loadings = next_loadings
        if diff < BC_LOADINGS_TOL:
            break

    coef = pd.Series(beta_std, index=x.columns, name="coefficient")
    return coef, lambda_value, alpha_value


def fit_poisson_l1_with_unpenalized_controls(
    x_pen,
    x_fe,
    y,
    sample_weights = None,
):
    x_np = x_pen.to_numpy(dtype=float)
    y_np = np.clip(y.to_numpy(dtype=float), a_min=0.0, a_max=None)
    nobs, nfeatures = x_np.shape
    if nfeatures == 0:
        return pd.Series(dtype=float), np.nan, np.nan

    weights = None
    if sample_weights is not None:
        weights = np.asarray(sample_weights, dtype=float)
        weights = weights / np.nanmean(weights)

    x_center = weighted_mean(x_np, weights)
    x_dm = x_np - x_center
    x_scale = weighted_rms(x_dm, weights)
    x_scale = np.where(x_scale <= 0, 1.0, x_scale)
    x_std = pd.DataFrame(x_dm / x_scale, index=x_pen.index, columns=x_pen.columns)

    x_design = pd.concat([x_fe.loc[x_pen.index].astype(float), x_std], axis=1)
    x_design = sm.add_constant(x_design, has_constant="add")

    lambda_value = bc_penalty_level(nobs, nfeatures)
    alpha_value = lambda_value / (2.0 * nobs)
    n_unpenalized = x_design.shape[1] - nfeatures
    alpha_vec = np.concatenate(
        [
            np.zeros(n_unpenalized),
            np.repeat(alpha_value, nfeatures),
        ]
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.GLM(
            y_np,
            x_design,
            family=sm.families.Poisson(),
            freq_weights=weights,
        )
        fit = model.fit_regularized(
            alpha=alpha_vec,
            L1_wt=1.0,
            maxiter=5000,
            cnvrg_tol=1e-8,
        )

    params = pd.Series(np.asarray(fit.params, dtype=float), index=x_design.columns)
    coef = params[x_pen.columns] / pd.Series(x_scale, index=x_pen.columns)
    coef.name = "coefficient"
    return coef, lambda_value, alpha_value


def choose_timing_glm_family(y_series, x_sm, weights=None):
    y_for_fit = np.clip(y_series.astype(float), a_min=0.0, a_max=None)
    fit_kwargs = {"maxiter": 200, "disp": 0}

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            poisson = sm.GLM(
                y_for_fit,
                x_sm,
                family=sm.families.Poisson(),
                freq_weights=weights,
            ).fit(**fit_kwargs)

        mu = poisson.fittedvalues.squeeze()
        aux_y = ((pd.Series(y_for_fit, index=x_sm.index) - mu) ** 2) - pd.Series(y_for_fit, index=x_sm.index)
        aux_x = mu ** 2

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if weights is None:
                aux = sm.OLS(aux_y, aux_x).fit(cov_type="HC0")
            else:
                aux = sm.WLS(aux_y, aux_x, weights=weights).fit(cov_type="HC0")

        alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
        p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0
    except Exception:
        alpha_hat = 0.0
        p_over = 1.0

    if p_over < 0.05 and alpha_hat > 0:
        return sm.families.NegativeBinomial(alpha=alpha_hat), "NegativeBinomial", alpha_hat, p_over
    return sm.families.Poisson(), "Poisson", alpha_hat, p_over


def post_lasso_refit(
    x_pen,
    x_fe,
    y,
    selected_features,
    model_family,
    model_groups,
    sample_weights = None,
):
    # Default: NA estimates unless the post-selection refit succeeds.
    out = {
        f: {
            "post_coef": np.nan,
            "post_se": np.nan,
            "post_p_value": np.nan,
        }
        for f in selected_features
    }
    if not selected_features:
        return out, {
            "nobs": int(pd.to_numeric(y, errors="coerce").notna().sum()),
            "n_selected": 0,
            "n_refit_terms": 0,
            "dropped_zero_variance_cols": "",
            "dropped_refit_cols": "",
            "timing_glm_family": "",
            "timing_overdispersion_alpha": np.nan,
            "timing_overdispersion_p_value": np.nan,
            "refit_used_fallback": False,
        }

    x_sel = x_pen[selected_features].copy()
    y_sel = pd.to_numeric(y, errors="coerce")
    groups = model_groups.loc[y_sel.index].copy()

    valid = y_sel.notna() & groups.notna()
    if sample_weights is not None:
        weights = pd.Series(sample_weights, index=y_sel.index).astype(float)
        valid = valid & weights.notna() & np.isfinite(weights) & (weights > 0)
        weights = weights.loc[valid]
        weights = weights / weights.mean()
    else:
        weights = None
    if valid.sum() == 0:
        return out, {
            "nobs": 0,
            "n_selected": int(len(selected_features)),
            "n_refit_terms": 0,
            "dropped_zero_variance_cols": "",
            "dropped_refit_cols": "",
            "timing_glm_family": "",
            "timing_overdispersion_alpha": np.nan,
            "timing_overdispersion_p_value": np.nan,
            "refit_used_fallback": False,
        }

    x_sel = x_sel.loc[valid].astype(float)
    y_series = y_sel.loc[valid].astype(float)
    x_fe_ref = x_fe.loc[valid].astype(float) if x_fe.shape[1] > 0 else pd.DataFrame(index=y_series.index)
    groups = groups.loc[valid]

    # Drop columns with near-zero variance in the selected sample.
    keep = [c for c in x_sel.columns if np.nanstd(x_sel[c].to_numpy(dtype=float)) > 0]
    if not keep and x_fe_ref.shape[1] == 0:
        return out, {
            "nobs": int(len(y_series)),
            "n_selected": int(len(selected_features)),
            "n_refit_terms": 0,
            "dropped_zero_variance_cols": ",".join(selected_features),
            "dropped_refit_cols": "",
            "timing_glm_family": "",
            "timing_overdispersion_alpha": np.nan,
            "timing_overdispersion_p_value": np.nan,
            "refit_used_fallback": False,
        }

    dropped_zero_variance_cols = [c for c in x_sel.columns if c not in keep]
    if keep:
        x_sel = x_sel[keep]
    else:
        x_sel = pd.DataFrame(index=x_fe_ref.index)

    x_refit = pd.concat([x_fe_ref, x_sel], axis=1)
    # Remove zero-variance columns before refit.
    x_refit_keep = [c for c in x_refit.columns if np.nanstd(x_refit[c].to_numpy(dtype=float)) > 0]
    dropped_zero_variance_cols = dropped_zero_variance_cols + [c for c in x_refit.columns if c not in x_refit_keep]
    x_refit = x_refit.loc[:, x_refit_keep]

    # Remove exact collinearity before post-selection refit.
    dummy_y = pd.DataFrame({"_y": y_series}, index=y_series.index)
    _, x_refit_independent = independent_design(dummy_y, x_refit)
    dropped_refit_cols = [c for c in x_refit.columns if c not in x_refit_independent.columns]
    x_refit = x_refit_independent

    x_sm = sm.add_constant(x_refit, has_constant="add")

    fit = None
    timing_glm_family = ""
    timing_overdispersion_alpha = np.nan
    timing_overdispersion_p_value = np.nan
    refit_used_fallback = False

    # Primary refit by model family.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if model_family in ["huber_l1", "bc_lasso_rlm"]:
                if weights is None:
                    fit = sm.RLM(y_series, x_sm, M=sm.robust.norms.HuberT()).fit(maxiter=200)
                    fit = apply_clustered_inference(fit, x_sm, y_series, groups, weights=fit.weights)
                else:
                    sqrt_weights = np.sqrt(weights)
                    weighted_y = y_series.mul(sqrt_weights, axis=0)
                    weighted_x = x_sm.mul(sqrt_weights, axis=0)
                    fit = sm.RLM(weighted_y, weighted_x, M=sm.robust.norms.HuberT()).fit(maxiter=200)
                    fit = apply_clustered_inference(fit, weighted_x, weighted_y, groups, weights=fit.weights)
            else:
                family, timing_glm_family, timing_overdispersion_alpha, timing_overdispersion_p_value = choose_timing_glm_family(
                    y_series,
                    x_sm,
                    weights=weights,
                )
                fit = sm.GLM(
                    np.clip(y_series, a_min=0.0, a_max=None),
                    x_sm,
                    family=family,
                    freq_weights=weights,
                ).fit(
                    maxiter=200,
                    disp=0,
                    cov_type="cluster",
                    cov_kwds={"groups": groups},
                )
    except Exception:
        fit = None

    # Fallback if family-specific refit fails. This keeps the table usable while
    # making failed family-specific estimates visible as a methodological issue.
    if fit is None:
        refit_used_fallback = True
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if weights is None:
                    fit = sm.OLS(y_series, x_sm).fit(cov_type="cluster", cov_kwds={"groups": groups})
                else:
                    fit = sm.WLS(y_series, x_sm, weights=weights).fit(cov_type="cluster", cov_kwds={"groups": groups})
        except Exception:
            return out, {
                "nobs": int(len(y_series)),
                "n_selected": int(len(selected_features)),
                "n_refit_terms": 0,
                "dropped_zero_variance_cols": ",".join(dropped_zero_variance_cols),
                "dropped_refit_cols": ",".join(dropped_refit_cols),
                "timing_glm_family": timing_glm_family,
                "timing_overdispersion_alpha": timing_overdispersion_alpha,
                "timing_overdispersion_p_value": timing_overdispersion_p_value,
                "refit_used_fallback": refit_used_fallback,
            }

    for f in selected_features:
        if f in fit.params.index:
            out[f] = {
                "post_coef": float(fit.params[f]),
                "post_se": float(fit.bse[f]) if f in fit.bse.index else np.nan,
                "post_p_value": float(fit.pvalues[f]) if f in fit.pvalues.index else np.nan,
            }
    diagnostics = {
        "nobs": int(len(y_series)),
        "n_selected": int(len(selected_features)),
        "n_refit_terms": int(len(fit.params)),
        "dropped_zero_variance_cols": ",".join(dropped_zero_variance_cols),
        "dropped_refit_cols": ",".join(dropped_refit_cols),
        "timing_glm_family": timing_glm_family,
        "timing_overdispersion_alpha": timing_overdispersion_alpha,
        "timing_overdispersion_p_value": timing_overdispersion_p_value,
        "refit_used_fallback": refit_used_fallback,
    }
    return out, diagnostics


def feature_label(feature):
    parts = feature.split("__x__")
    return "*".join(FEATURE_LABELS.get(part, part) for part in parts)


def sig_stars(p_value):
    if not np.isfinite(p_value):
        return ""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


def format_coef(value, p_value):
    if not np.isfinite(value):
        return ""
    text = f"{value:.2f}"
    if text == "-0.00":
        text = "0.00"
    stars = sig_stars(p_value)
    if stars:
        return f"${text}^{{{stars}}}$"
    if value < 0:
        return f"${text}$"
    return text


def format_se(value):
    if not np.isfinite(value):
        return ""
    text = f"{value:.2f}"
    if text == "-0.00":
        text = "0.00"
    return f"({text})"


def write_post_selection_table(path, post_df, summary_df, citation_weighted=False):
    outcome_labels = {**ELASTICITY_OUTCOMES, **TIMING_OUTCOMES}
    outcome_order = ALL_OUTCOMES
    selected = post_df.loc[post_df["selected"]].copy()
    if selected.empty:
        ordered_features = []
    else:
        order = (
            selected.groupby("feature")["abs_screen_coefficient"]
            .max()
            .sort_values(ascending=False)
        )
        ordered_features = order.index.tolist()

    caption = "LASSO-selected variables and post-selection regressions"
    label = "tab:lasso_post_selection"
    if citation_weighted:
        caption = caption + " (citation weighted)"
        label = label + "_cw"

    lines = [
        "\\begin{table}[H]",
        "\\centering",
        f"\\caption{{ \\\\ \\underline{{{caption}}} }}",
        f"\\label{{{label}}}",
        "\\scriptsize",
        "\\begin{tabular}{l c c c c c}",
        "\\toprule",
        "& \\textit{y-slope} & \\textit{$\\pi$-slope} & \\textit{sacratio} & \\textit{y-timing} & \\textit{$\\pi$-timing} \\\\",
        "\\midrule",
    ]

    for row_index, feature in enumerate(ordered_features):
        label_text = feature_label(feature)
        coef_cells = []
        se_cells = []
        for outcome in outcome_order:
            match = selected.loc[(selected["feature"] == feature) & (selected["outcome"] == outcome)]
            if match.empty:
                coef_cells.append("")
                se_cells.append("")
            else:
                row = match.iloc[0]
                coef_cells.append(format_coef(float(row["post_coef"]), float(row["post_p_value"])))
                se_cells.append(format_se(float(row["post_se"])))
        lines.append(label_text + " & " + " & ".join(coef_cells) + " \\\\")
        lines.append(" & " + " & ".join(se_cells) + " \\\\")
        if row_index < len(ordered_features) - 1:
            lines.append("\\addlinespace[0.5em]")
            lines.append("")

    lines.append("\\midrule")
    n_cells = []
    selected_cells = []
    for outcome in outcome_order:
        srow = summary_df.loc[summary_df["outcome"] == outcome].iloc[0]
        n_cells.append(str(int(srow["n_obs"])))
        selected_cells.append(str(int(srow["n_nonzero"])))
    lines.append("$N$ & " + " & ".join(n_cells) + " \\\\")
    lines.append("Selected variables & " + " & ".join(selected_cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            f"\\multicolumn{{6}}{{p{{14cm}}}}{{\\footnotesize Notes: Entries are post-selection refit coefficients for variables selected by the LASSO screen with screening multiplier {BC_SCREENING_MULTIPLIER:.2f}. Elasticity outcomes use a Belloni--Chernozhukov-style feasible square-loss screen after residualizing controls. Timing outcomes use a Poisson L1 screen with policy-rule and estimated-model controls included but unpenalized. Standard errors in parentheses are clustered by model. Post-selection elasticity columns use robust linear regressions; timing columns use Poisson GLM with a negative-binomial GLM used when an auxiliary overdispersion test rejects equidispersion. Blank cells for selected variables indicate a post-selection term dropped from the refit because of zero variance or exact collinearity. *, **, *** indicate statistical significance at 10, 5, and 1 percent, respectively."
            + (" Citation weights are age-adjusted, log-transformed, and normalized to mean one within each outcome sample." if citation_weighted else "")
            + "}",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def lasso_output_name(base_name, citation_weighted=False):
    if not citation_weighted:
        return base_name
    stem, suffix = base_name.rsplit(".", 1)
    return f"{stem}_citation_weighted.{suffix}"


def run_lasso_screen(df, x_full, dropped_sparse_df, out_dir, citation_weighted=False):
    records = []
    summaries = []
    post_records = []
    post_refit_diagnostics = []
    outcome_sparse_drops = []

    weight_label = "citation-weighted" if citation_weighted else "unweighted"
    print(f"Running LASSO screen: {weight_label}")

    for outcome, pretty in {**ELASTICITY_OUTCOMES, **TIMING_OUTCOMES}.items():
        y_raw = pd.to_numeric(df[outcome], errors="coerce")
        mask = y_raw.notna()
        if citation_weighted:
            raw_weights = pd.to_numeric(df["citation_weight"], errors="coerce")
            mask = mask & raw_weights.notna() & np.isfinite(raw_weights) & (raw_weights > 0)

        y = y_raw.loc[mask].astype(float)
        x_raw = x_full.loc[mask].copy()
        x, dropped_outcome_sparse_df = filter_sparse_binary_features(
            x_raw,
            df.loc[mask, "model"],
            min_models_for_one=MIN_MODELS_FOR_BINARY_FEATURE,
        )
        dropped_outcome_sparse_df["outcome"] = outcome
        dropped_outcome_sparse_df["citation_weighted"] = citation_weighted
        outcome_sparse_drops.append(dropped_outcome_sparse_df)

        groups = df.loc[mask, "model"].astype(str)

        sample_weights = None
        if citation_weighted:
            sample_weights = raw_weights.loc[mask].astype(float)
            sample_weights = sample_weights / sample_weights.mean()

        if outcome in TIMING_OUTCOMES:
            y = np.clip(y, a_min=0.0, a_max=None)

        fe_cols = [c for c in FIXED_EFFECT_COLUMNS if c in df.columns]
        x_fe = df.loc[mask, fe_cols].copy()
        for c in x_fe.columns:
            x_fe[c] = pd.to_numeric(x_fe[c], errors="coerce")
            med = x_fe[c].median()
            x_fe[c] = x_fe[c].fillna(med if pd.notna(med) else 0.0)
        # Keep only FE columns with variation.
        x_fe = x_fe.loc[:, [c for c in x_fe.columns if np.nanstd(x_fe[c].to_numpy(dtype=float)) > 0]].copy()

        # Penalized feature set excludes FE main effects.
        x_pen = x.drop(columns=[c for c in FIXED_EFFECT_COLUMNS if c in x.columns], errors="ignore").copy()

        if outcome in TIMING_OUTCOMES:
            # Count outcomes keep their level form; controls enter the Poisson
            # L1 screen directly and are unpenalized.
            pen_keep = [c for c in x_pen.columns if np.nanstd(x_pen[c].to_numpy(dtype=float)) > 1e-12]
            x_pen_lasso = x_pen[pen_keep].copy()
            lasso_weights = None if sample_weights is None else sample_weights.loc[x_pen_lasso.index]
            if x_pen_lasso.shape[1] > 0:
                coef_fit, theory_lambda, lasso_alpha = fit_poisson_l1_with_unpenalized_controls(
                    x_pen_lasso,
                    x_fe,
                    y,
                    sample_weights=lasso_weights,
                )
            else:
                coef_fit = pd.Series(dtype=float)
                theory_lambda, lasso_alpha = np.nan, np.nan
            model_family = "poisson_l1_count_glm"
        else:
            y_lasso, x_pen_lasso = residualize_wrt_fixed_effects(y, x_pen, x_fe, weights=sample_weights)

            # Drop near-zero residualized variance columns from penalized problem only.
            pen_keep = [c for c in x_pen_lasso.columns if np.nanstd(x_pen_lasso[c].to_numpy(dtype=float)) > 1e-12]
            x_pen_lasso = x_pen_lasso[pen_keep].copy()
            lasso_weights = None if sample_weights is None else sample_weights.loc[x_pen_lasso.index]

            if x_pen_lasso.shape[1] > 0:
                coef_fit, theory_lambda, lasso_alpha = fit_bc_lasso(
                    x_pen_lasso,
                    y_lasso,
                    sample_weights=lasso_weights,
                )
            else:
                coef_fit = pd.Series(dtype=float)
                theory_lambda, lasso_alpha = np.nan, np.nan
            model_family = "bc_lasso_rlm"

        # Re-embed coefficients into full penalized feature space (dropped residual cols => 0).
        coef = pd.Series(0.0, index=x_pen.columns, name="coefficient")
        for c in coef_fit.index:
            if c in coef.index:
                coef.loc[c] = float(coef_fit.loc[c])

        abs_coef = coef.abs()
        is_zero = abs_coef <= ZERO_TOL
        selected = coef.index[~is_zero].tolist()
        post_map, post_diag = post_lasso_refit(
            x_pen=x_pen,
            x_fe=x_fe,
            y=y,
            selected_features=selected,
            model_family=model_family,
            model_groups=groups,
            sample_weights=sample_weights,
        )
        post_refit_diagnostics.append(
            {
                "outcome": outcome,
                "label": pretty,
                "model_family": model_family,
                "citation_weighted": citation_weighted,
                **post_diag,
            }
        )

        summaries.append(
            {
                "outcome": outcome,
                "label": pretty,
                "model_family": model_family,
                "citation_weighted": citation_weighted,
                "n_obs": int(post_diag.get("nobs", len(y))),
                "n_features": int(len(coef)),
                "n_zero": int(is_zero.sum()),
                "n_nonzero": int((~is_zero).sum()),
                "share_zero": float(is_zero.mean()),
                "theory_lambda": float(theory_lambda),
                "sklearn_alpha": float(lasso_alpha),
            }
        )

        tmp = pd.DataFrame(
            {
                "outcome": outcome,
                "label": pretty,
                "model_family": model_family,
                "citation_weighted": citation_weighted,
                "feature": coef.index,
                "coefficient": coef.values,
                "abs_coefficient": abs_coef.values,
                "is_zero": is_zero.values,
                "post_p_value": [post_map.get(f, {}).get("post_p_value", np.nan) for f in coef.index],
            }
        )
        records.append(tmp)

        for feature in coef.index:
            post = post_map.get(feature, {})
            post_records.append(
                {
                    "outcome": outcome,
                    "label": pretty,
                    "model_family": model_family,
                    "citation_weighted": citation_weighted,
                    "feature": feature,
                    "feature_label": feature_label(feature),
                    "screen_coefficient": float(coef.loc[feature]),
                    "abs_screen_coefficient": float(abs_coef.loc[feature]),
                    "selected": bool(not is_zero.loc[feature]),
                    "post_coef": post.get("post_coef", np.nan),
                    "post_se": post.get("post_se", np.nan),
                    "post_p_value": post.get("post_p_value", np.nan),
                }
            )

        print(
            f"[{outcome}] {weight_label} family={model_family} lambda={theory_lambda:.6g} "
            f"zero={int(is_zero.sum())}/{len(is_zero)}"
        )

    coef_df = pd.concat(records, ignore_index=True)
    summary_df = pd.DataFrame(summaries).sort_values("outcome").reset_index(drop=True)
    zero_df = coef_df.loc[coef_df["is_zero"]].copy().sort_values(["outcome", "feature"])
    nonzero_df = (
        coef_df.loc[~coef_df["is_zero"]]
        .copy()
        .sort_values(["outcome", "abs_coefficient"], ascending=[True, False])
    )
    post_df = pd.DataFrame(post_records)
    post_refit_diagnostics_df = pd.DataFrame(post_refit_diagnostics)
    if outcome_sparse_drops:
        outcome_sparse_dropped_df = pd.concat(outcome_sparse_drops, ignore_index=True)
    else:
        outcome_sparse_dropped_df = pd.DataFrame(
            columns=["feature", "n_models_with_value_1", "outcome", "citation_weighted"]
        )

    coef_df.to_csv(out_dir / lasso_output_name("lasso_coefficients_long.csv", citation_weighted), index=False)
    summary_df.to_csv(out_dir / lasso_output_name("lasso_zeroed_summary.csv", citation_weighted), index=False)
    zero_df.to_csv(out_dir / lasso_output_name("lasso_zeroed_features.csv", citation_weighted), index=False)
    nonzero_df.to_csv(out_dir / lasso_output_name("lasso_nonzero_features.csv", citation_weighted), index=False)
    post_df.to_csv(out_dir / lasso_output_name("lasso_post_selection_table.csv", citation_weighted), index=False)
    post_refit_diagnostics_df.to_csv(
        out_dir / lasso_output_name("post_refit_diagnostics.csv", citation_weighted),
        index=False,
    )
    outcome_sparse_dropped_df.to_csv(
        out_dir / lasso_output_name("lasso_sparse_dropped_features_by_outcome.csv", citation_weighted),
        index=False,
    )
    write_post_selection_table(
        out_dir / lasso_output_name("lasso_post_selection_table.tex", citation_weighted),
        post_df,
        summary_df,
        citation_weighted=citation_weighted,
    )

    # Human-readable report.
    report_lines = []
    report_lines.append(f"LASSO zeroed-feature report ({weight_label})")
    report_lines.append("")
    for _, row in summary_df.iterrows():
        out = row["outcome"]
        report_lines.append(
            f"{out} ({row['model_family']}): "
            f"zeroed {int(row['n_zero'])} of {int(row['n_features'])} features"
        )
        feats = zero_df.loc[zero_df["outcome"] == out, "feature"].tolist()
        for f in feats:
            report_lines.append(f"  - {f}")
        report_lines.append("")
    (out_dir / lasso_output_name("lasso_zeroed_report.txt", citation_weighted)).write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    return summary_df


data_path = INPUT_DIR / "MMB_reg_format.dta"
out_dir = OUTPUT_DIR / "lasso"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
for path in OUTPUT_DIR.iterdir():
    if path.name == ".gitkeep":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
out_dir.mkdir(parents=True, exist_ok=True)

print("Reading:", data_path)
df = pd.read_stata(data_path)

# Align with paper sample where timing extremes are removed.
if "y_timing_max" in df.columns and "piq_timing_max" in df.columns:
    df = df[(df["y_timing_max"] < TIMING_SENTINEL) & (df["piq_timing_max"] < TIMING_SENTINEL)].copy()

x_base = get_covariate_frame(df)
x_full = add_pairwise_interactions(x_base)
x_full, dropped_sparse_df = filter_sparse_binary_features(
    x_full,
    df["model"],
    min_models_for_one=MIN_MODELS_FOR_BINARY_FEATURE,
)

n_interaction_candidates = len([c for c in x_base.columns if c not in EXCLUDE_FROM_INTERACTIONS])
n_pre_features = int(x_base.shape[1] + comb(n_interaction_candidates, 2))

print(f"Base covariates: {x_base.shape[1]}")
print(f"With pairwise interactions (pre-filter): {n_pre_features}")
print(f"After sparse-binary filter: {x_full.shape[1]}")
print(f"Sparse binary features dropped: {len(dropped_sparse_df)}")

dropped_sparse_df.to_csv(out_dir / "lasso_sparse_dropped_features.csv", index=False)
summary_unweighted = run_lasso_screen(df, x_full, dropped_sparse_df, out_dir, citation_weighted=False)
summary_weighted = run_lasso_screen(df, x_full, dropped_sparse_df, out_dir, citation_weighted=True)

metadata = {
    "data_path": str(data_path.relative_to(TASK_DIR)),
    "n_rows_after_timing_filter": int(len(df)),
    "timing_sentinel_exclusion_value": TIMING_SENTINEL,
    "paper_base_covariates": PAPER_BASE_COVARIATES,
    "fixed_effect_columns": FIXED_EFFECT_COLUMNS,
    "exclude_from_interactions": EXCLUDE_FROM_INTERACTIONS,
    "n_base_covariates": int(x_base.shape[1]),
    "n_covariates_with_interactions_after_sparse_filter": int(x_full.shape[1]),
    "min_models_for_binary_feature_value_1": MIN_MODELS_FOR_BINARY_FEATURE,
    "n_sparse_binary_features_dropped": int(len(dropped_sparse_df)),
    "zero_tolerance": ZERO_TOL,
    "bc_penalty_c": BC_C,
    "bc_gamma_base": BC_GAMMA_BASE,
    "bc_screening_multiplier": BC_SCREENING_MULTIPLIER,
    "bc_max_loadings_iter": BC_MAX_LOADINGS_ITER,
    "bc_loadings_tolerance": BC_LOADINGS_TOL,
    "elasticity_outcomes": ELASTICITY_OUTCOMES,
    "timing_outcomes": TIMING_OUTCOMES,
    "selection_method": "Elasticity outcomes use Belloni-Chernozhukov-style feasible square-loss LASSO with iterated heteroskedastic penalty loadings after residualizing controls; timing outcomes use Poisson L1 selection with controls unpenalized.",
    "post_selection_standard_errors": "clustered by model",
    "post_selection_timing_refit": "Poisson GLM, with negative-binomial GLM used when an auxiliary overdispersion test rejects equidispersion.",
    "citation_weighted_outputs": True,
}
(out_dir / "lasso_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

print("Wrote LASSO outputs to:", out_dir)
