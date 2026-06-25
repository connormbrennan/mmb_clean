from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from patsy import dmatrices
from scipy import stats
from statsmodels.robust import norms, scale


def load_table_params(code_file):
    repo_dir = Path(code_file).resolve().parents[4]
    config_path = repo_dir / "config" / "params.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    params = dict(config["mmb_regression_tables"])
    params["time_limit"] = config["mmb"]["time_limit"]
    return params


def load_regression_data(input_dir, params):
    df = pd.read_stata(input_dir / "MMB_reg_format.dta")

    # Keep only finite timing observations so elasticities and timing use the same sample.
    time_limit = params["time_limit"]
    df = df.loc[df["y_timing_max"] < time_limit].copy()
    df = df.loc[df["piq_timing_max"] < time_limit].copy()

    # Interaction specs use explicit non-indexed wage terms.
    if "wg_ndx" in df.columns:
        df["not_wg_ndx"] = 1 - df["wg_ndx"]
    return df


def active_controls(data, params):
    controls = []
    for var in params["fixed_vars"]:
        if data[var].nunique(dropna=True) > 1:
            controls.append(var)
    return controls


def formula_for(depvar, variables, data, params):
    rhs = active_controls(data, params) + list(variables)
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


def cluster_groups(data, design, params):
    cluster_var = params.get("cluster_var")
    if not cluster_var:
        return None
    return data.loc[design.index, cluster_var]


def apply_clustered_inference(fit, exog, endog, groups, weights=None):
    if groups is None:
        return fit

    # Statsmodels RLM does not provide clustered covariance directly. Treat the
    # converged RLM robustness weights as WLS weights and cluster score sums.
    exog_arr = np.asarray(exog, dtype=float)
    endog_arr = np.asarray(endog, dtype=float).reshape(-1)
    params = fit.params.to_numpy(dtype=float) if hasattr(fit.params, "to_numpy") else np.asarray(fit.params, dtype=float)
    group_values = pd.Series(groups).to_numpy()

    if weights is None:
        weights_arr = np.ones(exog_arr.shape[0])
    else:
        weights_arr = np.asarray(weights, dtype=float).reshape(-1)

    resid = endog_arr - exog_arr @ params
    keep = np.isfinite(resid) & np.isfinite(weights_arr) & pd.notna(group_values)
    exog_arr = exog_arr[keep]
    resid = resid[keep]
    weights_arr = weights_arr[keep]
    group_values = group_values[keep]

    sqrt_weights = np.sqrt(np.clip(weights_arr, 0.0, np.inf))
    weighted_x = exog_arr * sqrt_weights[:, None]
    weighted_resid = resid * sqrt_weights
    bread = np.linalg.pinv(weighted_x.T @ weighted_x)

    scores = weighted_x * weighted_resid[:, None]
    meat = np.zeros((weighted_x.shape[1], weighted_x.shape[1]))
    for group in pd.unique(group_values):
        group_score = scores[group_values == group].sum(axis=0)
        meat += np.outer(group_score, group_score)

    cov = bread @ meat @ bread
    nobs = weighted_x.shape[0]
    nparams = weighted_x.shape[1]
    ngroups = pd.Series(group_values).nunique()
    if ngroups > 1 and nobs > nparams:
        cov *= (ngroups / (ngroups - 1.0)) * ((nobs - 1.0) / (nobs - nparams))

    bse = np.sqrt(np.clip(np.diag(cov), 0.0, np.inf))
    with np.errstate(divide="ignore", invalid="ignore"):
        z_scores = params / bse
    pvalues = 2.0 * stats.norm.sf(np.abs(z_scores))
    pvalues[~np.isfinite(z_scores)] = np.nan

    index = fit.params.index if hasattr(fit.params, "index") else exog.columns
    fit.bse = pd.Series(bse, index=index)
    fit.pvalues = pd.Series(pvalues, index=index)
    fit.clustered_by = pd.Series(groups).name if pd.Series(groups).name else "cluster"
    return fit


def fit_model(depvar, variables, data, params):
    formula = formula_for(depvar, variables, data, params)
    y, x = dmatrices(formula, data=data, return_type="dataframe")
    y, x = independent_design(y, x)
    groups = cluster_groups(data, x, params)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # Timing outcomes are counts, with a negative-binomial fallback when overdispersion is visible.
        if depvar in params["timing_outcomes"]:
            fit_kwargs = {}
            if groups is not None:
                fit_kwargs = {"cov_type": "cluster", "cov_kwds": {"groups": groups}}
            else:
                fit_kwargs = {"cov_type": "HC0"}
            poisson = sm.GLM(y, x, family=sm.families.Poisson()).fit(**fit_kwargs)
            mu = poisson.fittedvalues.squeeze()
            aux_y = ((y.squeeze() - mu) ** 2) - y.squeeze()
            aux_x = mu ** 2
            aux = sm.OLS(aux_y, aux_x).fit(cov_type="HC0")
            alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
            p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0
            if p_over < 0.05 and alpha_hat > 0:
                nb = sm.families.NegativeBinomial(alpha=alpha_hat)
                return sm.GLM(y, x, family=nb).fit(**fit_kwargs)
            return poisson

        # Elasticity outcomes use robust linear regression to reduce outlier influence.
        fit = sm.RLM(y.squeeze(), x, M=norms.TukeyBiweight(c=4.685)).fit(
            scale_est=scale.HuberScale(),
            update_scale=True,
            cov="H1",
            conv="coefs",
        )
        return apply_clustered_inference(fit, x, y.squeeze(), groups, weights=fit.weights)


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


def label_for(term, params):
    var_labels = params["var_labels"]
    if term in var_labels:
        return var_labels[term]
    if ":" in term:
        return " x ".join(var_labels.get(part, part) for part in term.split(":"))
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


def write_table(path, title, fits, r2s, params):
    terms = []
    for fit in fits.values():
        for term in fit.params.index:
            if term not in terms:
                terms.append(term)
    terms = sorted(terms, key=lambda term: (term != "Intercept", term))

    outcome_labels = params["outcome_labels"]
    lines = [
        title,
        "=" * len(title),
        "",
        "Coefficients are followed by model-clustered standard errors in parentheses.",
        "Significance: * p<0.10, ** p<0.05, *** p<0.01.",
        "",
        "\t".join(["Variable"] + [outcome_labels.get(dep, dep) for dep in fits]),
    ]

    for term in terms:
        lines.append("\t".join([label_for(term, params)] + [format_coef(fit, term) for fit in fits.values()]))
        lines.append("\t".join([""] + [format_se(fit, term) for fit in fits.values()]))

    lines.append("")
    lines.append("\t".join(["Observations"] + [str(int(fit.nobs)) for fit in fits.values()]))
    lines.append("\t".join(["Pseudo R2"] + [f"{r2s[dep]:.3f}" for dep in fits]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_table(data, variables, title, path, params):
    fits = {}
    r2s = {}
    for depvar in params["outcomes"]:
        fit = fit_model(depvar, variables, data, params)
        fits[depvar] = fit
        r2s[depvar] = pseudo_r2(fit, data, depvar)
    write_table(path, title, fits, r2s, params)
    return path
