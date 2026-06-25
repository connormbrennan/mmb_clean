#!/usr/bin/env python3
"""
Disentangle model heterogeneity in MMB policy-transmission results.

This script runs a deeper analysis layer beyond the paper's baseline regressions:
1) Rule-vs-model variance decomposition (fixed-effects OLS)
2) Cross-rule rank stability by outcome
3) IRF-shape archetype clustering and attribute contrasts
4) Nonlinear benchmark vs linear benchmark
5) Outlier sensitivity checks

Inputs:
  - ../input/MMB_reg_format.dta
  - ../input/MMB_IRF_format_full.dta

Outputs:
  - ../output/disentangle_spaghetti/

Run:
  make
"""


from pathlib import Path
import shutil
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm
import statsmodels.formula.api as smf
import statsmodels.api as sm

from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

sys.path.append(str(Path(__file__).resolve().parents[2]))
from regression_table_tools import apply_clustered_inference


OUTCOMES = ["IScurve20", "infl_per_rr20", "sacratio20", "y_timing_max", "piq_timing_max"]
RULE_PAIRS = [("Taylor", "Inertial_Taylor"), ("Taylor", "Growth"), ("Inertial_Taylor", "Growth")]
IRF_SHAPE_VARIABLES = ["y", "piq", "irate"]
ARCHETYPE_ATTRS = [
    "estimated",
    "cb_authors_ext",
    "hh_demand",
    "firm_bs",
    "bank",
    "labor_frict",
    "open",
    "rule_itr",
    "rule_g",
]
CORE_FEATURES = [
    "rule_itr",
    "rule_g",
    "estimated",
    "stky_wg",
    "wg_ndx",
    "pr_ndx",
    "hh_demand",
    "bank",
    "firm_bs",
    "labor_frict",
    "open",
    "cb_authors_ext",
    "ln_neq",
    "vint_mid",
    "vint_late",
]

ELASTICITY_OUTCOMES = ["IScurve20", "infl_per_rr20", "sacratio20"]
TIMING_OUTCOMES = ["y_timing_max", "piq_timing_max"]

DRIVER_CONTROL_FEATURES = ["rule_itr", "rule_g", "estimated"]
DRIVER_NOMINAL_FEATURES = ["sw_x_idx", "sw_x_noidx", "pr_ndx"]
DRIVER_REAL_FEATURES = [
    "hh_demand",
    "bank",
    "firm_bs",
    "labor_frict",
    "open",
    "hh_demand_x_bank",
    "firm_bs_x_bank",
    "hh_demand_x_firm_bs",
    "hh_demand_x_labor_frict",
    "firm_bs_x_labor_frict",
    "bank_x_labor_frict",
    "hh_demand_x_open",
    "firm_bs_x_open",
    "bank_x_open",
    "labor_frict_x_open",
]
DRIVER_NONMODEL_FEATURES = ["cb_authors_ext", "ln_neq", "vint_mid", "vint_late", "cb_x_late"]
DRIVER_ALL_FEATURES = (
    DRIVER_CONTROL_FEATURES
    + DRIVER_NOMINAL_FEATURES
    + DRIVER_REAL_FEATURES
    + DRIVER_NONMODEL_FEATURES
)
MIN_DRIVER_SUPPORT_MODELS = 5


TASK_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"


def load_data():
    reg = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")
    # Keep paper-like timing sample and non-missing model/rule IDs.
    reg = reg[(reg["y_timing_max"] != 99) & (reg["piq_timing_max"] != 99)].copy()
    reg = reg.dropna(subset=["model", "rule"]).copy()

    irf = pd.read_stata(INPUT_DIR / "MMB_IRF_format_full.dta")
    irf = irf[(irf["period"] <= 20)].copy()
    irf = irf.dropna(subset=["model", "rule"]).copy()

    # Restrict IRF panel to model-rule keys that survive the regression sample filter.
    valid_keys = set(reg["model"].astype(str) + "||" + reg["rule"].astype(str))
    irf["key"] = irf["model"].astype(str) + "||" + irf["rule"].astype(str)
    irf = irf[irf["key"].isin(valid_keys)].copy()

    return reg, irf


def variance_decomposition(reg):
    rows = []
    for outcome in OUTCOMES:
        d = reg[["model", "rule", outcome]].dropna().copy()
        if d.empty:
            continue
        m_rule = smf.ols(f"{outcome} ~ C(rule)", data=d).fit()
        m_model = smf.ols(f"{outcome} ~ C(model)", data=d).fit()
        m_both = smf.ols(f"{outcome} ~ C(rule) + C(model)", data=d).fit()
        rows.append(
            {
                "outcome": outcome,
                "n_obs": len(d),
                "r2_rule_only": m_rule.rsquared,
                "r2_model_only": m_model.rsquared,
                "r2_rule_plus_model": m_both.rsquared,
                "inc_rule_given_model": m_both.rsquared - m_model.rsquared,
                "inc_model_given_rule": m_both.rsquared - m_rule.rsquared,
            }
        )
    return pd.DataFrame(rows).sort_values("outcome").reset_index(drop=True)


def rule_rank_stability(reg):
    rows = []
    for outcome in OUTCOMES:
        piv = reg.pivot_table(index="model", columns="rule", values=outcome)
        for a, b in RULE_PAIRS:
            if a not in piv.columns or b not in piv.columns:
                continue
            d = piv[[a, b]].dropna()
            if len(d) < 10:
                continue
            sp = stats.spearmanr(d[a], d[b])
            pe = stats.pearsonr(d[a], d[b])
            rows.append(
                {
                    "outcome": outcome,
                    "rule_a": a,
                    "rule_b": b,
                    "n_models": len(d),
                    "spearman_rho": sp.statistic,
                    "spearman_p": sp.pvalue,
                    "pearson_r": pe.statistic,
                    "pearson_p": pe.pvalue,
                }
            )
    return pd.DataFrame(rows).sort_values(["outcome", "rule_a", "rule_b"]).reset_index(drop=True)


def within_model_rule_contrasts(reg):
    rows = []
    for outcome in OUTCOMES:
        piv = reg.pivot_table(index=["model", "estimated"], columns="rule", values=outcome)
        for a, b in RULE_PAIRS:
            if a not in piv.columns or b not in piv.columns:
                continue
            d = piv[[a, b]].dropna().copy()
            if len(d) < 10:
                continue
            d["delta"] = d[b] - d[a]
            rows.append(
                {
                    "outcome": outcome,
                    "contrast": f"{b} - {a}",
                    "group": "all_models",
                    "n_models": len(d),
                    "mean_delta": d["delta"].mean(),
                    "median_delta": d["delta"].median(),
                    "t_test_p": stats.ttest_1samp(d["delta"], 0.0, nan_policy="omit").pvalue,
                }
            )

            for est_flag, grp_name in [(0, "calibrated_models"), (1, "estimated_models")]:
                dg = d.loc[d.index.get_level_values("estimated") == est_flag, "delta"]
                if len(dg) < 5:
                    continue
                rows.append(
                    {
                        "outcome": outcome,
                        "contrast": f"{b} - {a}",
                        "group": grp_name,
                        "n_models": len(dg),
                        "mean_delta": dg.mean(),
                        "median_delta": dg.median(),
                        "t_test_p": stats.ttest_1samp(dg, 0.0, nan_policy="omit").pvalue,
                    }
                )

            d_cal = d.loc[d.index.get_level_values("estimated") == 0, "delta"]
            d_est = d.loc[d.index.get_level_values("estimated") == 1, "delta"]
            if len(d_cal) >= 5 and len(d_est) >= 5:
                rows.append(
                    {
                        "outcome": outcome,
                        "contrast": f"{b} - {a}",
                        "group": "estimated_minus_calibrated",
                        "n_models": min(len(d_cal), len(d_est)),
                        "mean_delta": d_est.mean() - d_cal.mean(),
                        "median_delta": d_est.median() - d_cal.median(),
                        "t_test_p": stats.ttest_ind(d_est, d_cal, equal_var=False, nan_policy="omit").pvalue,
                    }
                )

    return pd.DataFrame(rows).sort_values(["outcome", "contrast", "group"]).reset_index(drop=True)


def outlier_table(reg):
    d = reg[["model", "rule"] + OUTCOMES].copy()
    for c in OUTCOMES:
        q1, q99 = d[c].quantile([0.01, 0.99])
        d[f"{c}_out_1_99"] = (d[c] < q1) | (d[c] > q99)
    d["n_outlier_flags"] = d[[f"{c}_out_1_99" for c in OUTCOMES]].sum(axis=1)
    return d.loc[d["n_outlier_flags"] > 0].sort_values("n_outlier_flags", ascending=False).reset_index(drop=True)


def build_irf_shape_features(irf):
    rows = []
    for key, g in irf.groupby("key"):
        g = g.sort_values("period")
        row = {"key": key, "model": g["model"].iloc[0], "rule": g["rule"].iloc[0]}
        # Cluster on primitive output, inflation, and policy-rate responses.
        # Exclude rrate because it is a lagged linear combination of irate and piq.
        for v in IRF_SHAPE_VARIABLES:
            vals = g[v].to_numpy(dtype=float)
            row[f"{v}_cum20"] = np.nansum(vals)
            row[f"{v}_peak"] = np.nanmax(vals)
            row[f"{v}_trough"] = np.nanmin(vals)
            row[f"{v}_std"] = np.nanstd(vals)
            row[f"{v}_tpeak"] = int(g.iloc[np.nanargmax(vals)]["period"])
            row[f"{v}_ttrough"] = int(g.iloc[np.nanargmin(vals)]["period"])
        rows.append(row)
    return pd.DataFrame(rows)


def build_irf_path_features(irf):
    periods = sorted(irf["period"].dropna().astype(int).unique())
    rows = []
    for key, g in irf.groupby("key"):
        g = g.sort_values("period")
        row = {"key": key, "model": g["model"].iloc[0], "rule": g["rule"].iloc[0]}
        for v in IRF_SHAPE_VARIABLES:
            vals = g.set_index("period")[v].reindex(periods)
            for period, val in vals.items():
                row[f"{v}_h{int(period):02d}"] = val
        rows.append(row)
    return pd.DataFrame(rows)


def robust_scaled_matrix(x):
    x = x.copy().astype(float)
    x = x.replace([np.inf, -np.inf], np.nan)
    for c in x.columns:
        med = x[c].median()
        x[c] = x[c].fillna(med if pd.notna(med) else 0.0)
        lo, hi = x[c].quantile([0.02, 0.98])
        x[c] = x[c].clip(lo, hi)
    x_scaled = RobustScaler().fit_transform(x)
    return x, x_scaled


def select_kmeans_labels(x_scaled):
    best = None
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=50).fit(x_scaled)
        s = silhouette_score(x_scaled, km.labels_)
        if best is None or s > best["silhouette"]:
            best = {"selected_k": k, "silhouette": float(s), "labels": km.labels_}
    return best


def summarize_cluster_tables(assignments, reg):
    merged = assignments.merge(
        reg[["model", "rule"] + OUTCOMES + ARCHETYPE_ATTRS],
        on=["model", "rule"],
        how="left",
    )

    cluster_outcomes = (
        merged.groupby("cluster_raw")
        .agg(
            n_model_rules=("key", "size"),
            IScurve20=("IScurve20", "mean"),
            infl_per_rr20=("infl_per_rr20", "mean"),
            sacratio20=("sacratio20", "mean"),
            y_timing_max=("y_timing_max", "mean"),
            piq_timing_max=("piq_timing_max", "mean"),
        )
        .reset_index()
    )
    cluster_prevalence = (
        merged.groupby("cluster_raw")
        .agg(
            n_model_rules=("key", "size"),
            estimated=("estimated", "mean"),
            cb_authors_ext=("cb_authors_ext", "mean"),
            hh_demand=("hh_demand", "mean"),
            firm_bs=("firm_bs", "mean"),
            bank=("bank", "mean"),
            labor_frict=("labor_frict", "mean"),
            open=("open", "mean"),
            rule_itr=("rule_itr", "mean"),
            rule_g=("rule_g", "mean"),
        )
        .reset_index()
    )

    return merged, cluster_outcomes, cluster_prevalence


def run_alternative_archetypes(reg, irf, shape_features, summary_x_scaled):
    base = shape_features[["key", "model", "rule", "cluster_raw"]].copy()
    base = base.rename(columns={"cluster_raw": "summary_kmeans"})

    method_rows = [
        {
            "method": "summary_kmeans",
            "feature_basis": "18 summary moments: cum20, peak, trough, std, tpeak, ttrough for y/piq/irate",
            "selection_rule": "max silhouette over k=2..6",
            "selected_k": int(shape_features["k_selected"].iloc[0]),
            "silhouette": float(shape_features["silhouette"].iloc[0]),
            "bic": np.nan,
            "pca_components": np.nan,
            "pca_variance_explained": np.nan,
            "ari_vs_summary_kmeans": 1.0,
        }
    ]
    method_labels = {"summary_kmeans": base["summary_kmeans"].to_numpy()}

    path = build_irf_path_features(irf)
    path = shape_features[["key", "model", "rule"]].merge(path, on=["key", "model", "rule"], how="left")
    path_cols = [c for c in path.columns if c not in ["key", "model", "rule"]]
    _, path_scaled = robust_scaled_matrix(path[path_cols])
    pca_full = PCA().fit(path_scaled)
    cumulative = np.cumsum(pca_full.explained_variance_ratio_)
    n_components = int(np.searchsorted(cumulative, 0.90) + 1)
    n_components = max(2, min(n_components, 10, path_scaled.shape[1], path_scaled.shape[0] - 1))
    pca = PCA(n_components=n_components, random_state=42)
    fpca_scores = pca.fit_transform(path_scaled)
    fpca_best = select_kmeans_labels(fpca_scores)
    method_labels["functional_pca_kmeans"] = fpca_best["labels"]
    method_rows.append(
        {
            "method": "functional_pca_kmeans",
            "feature_basis": "full y/piq/irate paths, horizons 0..20, reduced by PCA",
            "selection_rule": "components explain at least 90 percent variance, max silhouette over k=2..6",
            "selected_k": int(fpca_best["selected_k"]),
            "silhouette": float(fpca_best["silhouette"]),
            "bic": np.nan,
            "pca_components": int(n_components),
            "pca_variance_explained": float(pca.explained_variance_ratio_.sum()),
            "ari_vs_summary_kmeans": float(adjusted_rand_score(base["summary_kmeans"], fpca_best["labels"])),
        }
    )
    fpca_variance = pd.DataFrame(
        {
            "component": np.arange(1, len(pca.explained_variance_ratio_) + 1),
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance": np.cumsum(pca.explained_variance_ratio_),
        }
    )

    best_hier = None
    for k in range(2, 7):
        labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(summary_x_scaled)
        s = silhouette_score(summary_x_scaled, labels)
        if best_hier is None or s > best_hier["silhouette"]:
            best_hier = {"selected_k": k, "silhouette": float(s), "labels": labels}
    method_labels["hierarchical_ward"] = best_hier["labels"]
    method_rows.append(
        {
            "method": "hierarchical_ward",
            "feature_basis": "18 summary moments for y/piq/irate",
            "selection_rule": "Ward linkage, max silhouette over k=2..6",
            "selected_k": int(best_hier["selected_k"]),
            "silhouette": float(best_hier["silhouette"]),
            "bic": np.nan,
            "pca_components": np.nan,
            "pca_variance_explained": np.nan,
            "ari_vs_summary_kmeans": float(adjusted_rand_score(base["summary_kmeans"], best_hier["labels"])),
        }
    )

    best_gmm = None
    for k in range(2, 7):
        gmm = GaussianMixture(
            n_components=k,
            covariance_type="diag",
            reg_covar=1e-6,
            n_init=20,
            random_state=42,
        )
        labels = gmm.fit_predict(summary_x_scaled)
        bic = gmm.bic(summary_x_scaled)
        s = silhouette_score(summary_x_scaled, labels)
        if best_gmm is None or bic < best_gmm["bic"]:
            best_gmm = {"selected_k": k, "silhouette": float(s), "bic": float(bic), "labels": labels}
    method_labels["gaussian_mixture"] = best_gmm["labels"]
    method_rows.append(
        {
            "method": "gaussian_mixture",
            "feature_basis": "18 summary moments for y/piq/irate",
            "selection_rule": "diagonal-covariance GMM, min BIC over k=2..6",
            "selected_k": int(best_gmm["selected_k"]),
            "silhouette": float(best_gmm["silhouette"]),
            "bic": float(best_gmm["bic"]),
            "pca_components": np.nan,
            "pca_variance_explained": np.nan,
            "ari_vs_summary_kmeans": float(adjusted_rand_score(base["summary_kmeans"], best_gmm["labels"])),
        }
    )

    wide_assignments = base.copy()
    for method, labels in method_labels.items():
        if method != "summary_kmeans":
            wide_assignments[method] = labels

    long_rows = []
    outcome_tables = []
    prevalence_tables = []
    stability_model_tables = []
    stability_summary_tables = []

    for method, labels in method_labels.items():
        assignments = shape_features[["key", "model", "rule"]].copy()
        assignments["cluster_raw"] = labels
        _, outcomes, prevalence = summarize_cluster_tables(assignments, reg)
        stability_models, stability_summary = cluster_stability(assignments, outcomes)

        for df in [outcomes, prevalence, stability_models, stability_summary]:
            df.insert(0, "method", method)

        outcome_tables.append(outcomes)
        prevalence_tables.append(prevalence)
        stability_model_tables.append(stability_models)
        stability_summary_tables.append(stability_summary)

        for _, r in assignments.iterrows():
            long_rows.append(
                {
                    "method": method,
                    "key": r["key"],
                    "model": r["model"],
                    "rule": r["rule"],
                    "cluster_raw": r["cluster_raw"],
                }
            )

    return (
        wide_assignments,
        pd.DataFrame(long_rows),
        pd.DataFrame(method_rows),
        pd.concat(outcome_tables, ignore_index=True),
        pd.concat(prevalence_tables, ignore_index=True),
        pd.concat(stability_model_tables, ignore_index=True),
        pd.concat(stability_summary_tables, ignore_index=True),
        fpca_variance,
    )


def cluster_archetypes(reg, irf):
    shape = build_irf_shape_features(irf)
    feature_cols = [c for c in shape.columns if c not in ["key", "model", "rule"]]
    _, x_scaled = robust_scaled_matrix(shape[feature_cols])

    best = select_kmeans_labels(x_scaled)

    shape["cluster_raw"] = best["labels"]
    shape["k_selected"] = best["selected_k"]
    shape["silhouette"] = best["silhouette"]

    assignments = shape[["key", "model", "rule", "cluster_raw"]].copy()
    merged, cluster_outcomes, cluster_prevalence = summarize_cluster_tables(assignments, reg)

    # Orient binary cluster label for k=2: slow cluster has higher y_timing mean.
    if best["selected_k"] == 2:
        means = merged.groupby("cluster_raw")["y_timing_max"].mean()
        slow_cluster = int(means.idxmax())
        merged["cluster_slow"] = (merged["cluster_raw"] == slow_cluster).astype(int)
    else:
        merged["cluster_slow"] = np.nan

    (
        method_assignments_wide,
        method_assignments_long,
        method_comparison,
        method_outcomes,
        method_prevalence,
        method_stability_models,
        method_stability_summary,
        fpca_variance,
    ) = run_alternative_archetypes(reg, irf, shape, x_scaled)

    return (
        shape,
        merged,
        cluster_outcomes,
        cluster_prevalence,
        method_assignments_wide,
        method_assignments_long,
        method_comparison,
        method_outcomes,
        method_prevalence,
        method_stability_models,
        method_stability_summary,
        fpca_variance,
    )


def cluster_stability(shape_features, cluster_outcomes):
    d = shape_features[["model", "rule", "cluster_raw"]].copy()
    cluster_order = (
        cluster_outcomes[["cluster_raw", "y_timing_max"]]
        .sort_values("y_timing_max")
        .reset_index(drop=True)
    )
    if len(cluster_order) >= 2:
        fast_cluster = int(cluster_order.loc[0, "cluster_raw"])
        slow_cluster = int(cluster_order.loc[len(cluster_order) - 1, "cluster_raw"])
    else:
        fast_cluster = slow_cluster = int(cluster_order.loc[0, "cluster_raw"])

    model_cluster_counts = d.groupby(["model", "cluster_raw"]).size().unstack(fill_value=0)
    share = model_cluster_counts.div(model_cluster_counts.sum(axis=1), axis=0)
    dominant_cluster = share.idxmax(axis=1)
    dominant_share = share.max(axis=1)
    n_clusters_seen = (model_cluster_counts > 0).sum(axis=1)
    n_rules = model_cluster_counts.sum(axis=1)

    model_table = pd.DataFrame(
        {
            "model": share.index,
            "n_rules_present": n_rules.values,
            "n_clusters_seen": n_clusters_seen.values,
            "dominant_cluster": dominant_cluster.values,
            "dominant_share": dominant_share.values,
        }
    )

    def classify(r):
        if r["n_clusters_seen"] == 1 and int(r["dominant_cluster"]) == fast_cluster:
            return "stable_low_y_timing_cluster"
        if r["n_clusters_seen"] == 1 and int(r["dominant_cluster"]) == slow_cluster:
            return "stable_high_y_timing_cluster"
        if r["n_clusters_seen"] == 1:
            return "stable_other_cluster"
        return "rule_switcher"

    model_table["stability_class"] = model_table.apply(classify, axis=1)
    model_table = model_table.sort_values(["stability_class", "model"]).reset_index(drop=True)

    summary = (
        model_table.groupby("stability_class")
        .agg(n_models=("model", "size"), avg_dominant_share=("dominant_share", "mean"))
        .reset_index()
        .sort_values("n_models", ascending=False)
    )
    return model_table, summary


def build_driver_features(d):
    x = pd.DataFrame(index=d.index)
    x["rule_itr"] = d["rule_itr"].astype(float)
    x["rule_g"] = d["rule_g"].astype(float)
    x["estimated"] = d["estimated"].astype(float)
    x["sw_x_idx"] = d["stky_wg"].astype(float) * d["wg_ndx"].astype(float)
    x["sw_x_noidx"] = d["stky_wg"].astype(float) * (1.0 - d["wg_ndx"].astype(float))
    x["pr_ndx"] = d["pr_ndx"].astype(float)
    x["hh_demand"] = d["hh_demand"].astype(float)
    x["bank"] = d["bank"].astype(float)
    x["firm_bs"] = d["firm_bs"].astype(float)
    x["labor_frict"] = d["labor_frict"].astype(float)
    x["open"] = d["open"].astype(float)
    x["hh_demand_x_bank"] = x["hh_demand"] * x["bank"]
    x["firm_bs_x_bank"] = x["firm_bs"] * x["bank"]
    x["hh_demand_x_firm_bs"] = x["hh_demand"] * x["firm_bs"]
    x["hh_demand_x_labor_frict"] = x["hh_demand"] * x["labor_frict"]
    x["firm_bs_x_labor_frict"] = x["firm_bs"] * x["labor_frict"]
    x["bank_x_labor_frict"] = x["bank"] * x["labor_frict"]
    x["hh_demand_x_open"] = x["hh_demand"] * x["open"]
    x["firm_bs_x_open"] = x["firm_bs"] * x["open"]
    x["bank_x_open"] = x["bank"] * x["open"]
    x["labor_frict_x_open"] = x["labor_frict"] * x["open"]
    x["cb_authors_ext"] = d["cb_authors_ext"].astype(float)
    x["ln_neq"] = d["ln_neq"].astype(float)
    x["vint_mid"] = d["vint_mid"].astype(float)
    x["vint_late"] = d["vint_late"].astype(float)
    x["cb_x_late"] = x["cb_authors_ext"] * x["vint_late"]
    x = x.replace([np.inf, -np.inf], np.nan)
    for col in x.columns:
        med = x[col].median()
        x[col] = x[col].fillna(med if pd.notna(med) else 0.0)
    return x


def driver_feature_support(reg, x, feature, outcome):
    # Count support at the model level because rule rows repeat the same model attributes.
    usable = reg[outcome].notna()
    if feature not in x.columns:
        return int(reg.loc[usable, "model"].nunique()), int(usable.sum())

    vals = pd.to_numeric(x[feature], errors="coerce")
    nonzero = vals.fillna(0.0) != 0.0
    keep = usable & nonzero
    return int(reg.loc[keep, "model"].nunique()), int(keep.sum())


def interpret_effect(outcome, coef):
    if outcome in ["IScurve20", "infl_per_rr20"]:
        return "stronger policy power (larger absolute slope)" if coef < 0 else "weaker policy power (smaller absolute slope)"
    if outcome == "sacratio20":
        return "higher output cost of disinflation" if coef > 0 else "lower output cost of disinflation"
    if outcome in TIMING_OUTCOMES:
        return "longer lag to peak effect" if coef > 0 else "shorter lag to peak effect"
    return ""


def drop_collinear_columns(x, return_dropped=False):
    keep = []
    dropped = []
    rank = 0
    for col in x.columns:
        trial = x[keep + [col]]
        trial_rank = np.linalg.matrix_rank(trial.to_numpy(dtype=float))
        if trial_rank > rank:
            keep.append(col)
            rank = trial_rank
        else:
            dropped.append(col)
    if return_dropped:
        return x[keep], dropped
    return x[keep]


def fit_timing_glm_with_overdispersion(y, x, groups):
    # Match the paper tables: Poisson first, then negative binomial only when overdispersion is visible.
    with np.errstate(all="ignore"):
        poisson = sm.GLM(
            y,
            x,
            family=sm.families.Poisson(),
        ).fit(
            maxiter=200,
            disp=0,
            cov_type="cluster",
            cov_kwds={"groups": groups},
        )

    mu = poisson.fittedvalues.squeeze()
    aux_y = ((y - mu) ** 2) - y
    aux_x = mu ** 2
    try:
        aux = sm.OLS(aux_y, aux_x).fit(cov_type="HC0")
        alpha_hat = float(aux.params.squeeze()) if np.isfinite(aux.params.squeeze()) else 0.0
        p_over = float(aux.pvalues.squeeze()) if np.isfinite(aux.pvalues.squeeze()) else 1.0
    except Exception:
        alpha_hat = 0.0
        p_over = 1.0

    if p_over < 0.05 and alpha_hat > 0:
        return sm.GLM(
            y,
            x,
            family=sm.families.NegativeBinomial(alpha=alpha_hat),
        ).fit(
            maxiter=200,
            disp=0,
            cov_type="cluster",
            cov_kwds={"groups": groups},
        )
    return poisson


def attribute_driver_models(reg):
    x_panel = build_driver_features(reg)
    x_panel = sm.add_constant(x_panel, has_constant="add")

    panel_rows = []
    driver_dropped_rows = []
    for outcome in OUTCOMES:
        y = pd.to_numeric(reg[outcome], errors="coerce")
        m = y.notna()
        xi, dropped_cols = drop_collinear_columns(x_panel.loc[m].copy(), return_dropped=True)
        yi = y.loc[m].astype(float)
        groups = reg.loc[m, "model"]
        driver_dropped_rows.append(
            {
                "sample": "panel_with_rule_controls",
                "outcome": outcome,
                "original_columns": ",".join(x_panel.columns),
                "kept_columns": ",".join(xi.columns),
                "dropped_columns": ",".join(dropped_cols),
            }
        )

        if outcome in ELASTICITY_OUTCOMES:
            fit = sm.RLM(yi, xi, M=sm.robust.norms.HuberT()).fit(maxiter=200)
            fit = apply_clustered_inference(fit, xi, yi, groups, weights=fit.weights)
            params = fit.params
            ses = fit.bse
            pvals = fit.pvalues
        else:
            fit = fit_timing_glm_with_overdispersion(yi, xi, groups)
            params = fit.params
            ses = fit.bse
            pvals = fit.pvalues

        for f in params.index:
            support_models, support_rows = driver_feature_support(reg.loc[m], x_panel.loc[m], f, outcome)
            panel_rows.append(
                {
                    "sample": "panel_with_rule_controls",
                    "outcome": outcome,
                    "feature": f,
                    "coef": float(params[f]),
                    "se": float(ses[f]),
                    "p_value": float(pvals[f]),
                    "support_models": support_models,
                    "support_rows": support_rows,
                    "interpretation": interpret_effect(outcome, float(params[f])),
                }
            )

    panel_coef = pd.DataFrame(panel_rows)
    panel_sig = panel_coef[
        (panel_coef["feature"] != "const")
        & (~panel_coef["feature"].isin(DRIVER_CONTROL_FEATURES))
        & (panel_coef["p_value"] <= 0.10)
        & (panel_coef["support_models"] >= MIN_DRIVER_SUPPORT_MODELS)
    ].copy()
    panel_sig = panel_sig.sort_values(["outcome", "p_value"]).reset_index(drop=True)
    panel_sparse_sig = panel_coef[
        (panel_coef["feature"] != "const")
        & (~panel_coef["feature"].isin(DRIVER_CONTROL_FEATURES))
        & (panel_coef["p_value"] <= 0.10)
        & (panel_coef["support_models"] < MIN_DRIVER_SUPPORT_MODELS)
    ].copy()
    panel_sparse_sig = panel_sparse_sig.sort_values(["outcome", "p_value"]).reset_index(drop=True)

    # Model-level check: average outcomes across rules to isolate cross-model differences.
    reg_model = reg.groupby("model", as_index=False).mean(numeric_only=True)
    x_model = build_driver_features(reg_model).drop(columns=["rule_itr", "rule_g"], errors="ignore")
    x_model = sm.add_constant(x_model, has_constant="add")

    model_rows = []
    for outcome in OUTCOMES:
        y = pd.to_numeric(reg_model[outcome], errors="coerce")
        m = y.notna()
        xi, dropped_cols = drop_collinear_columns(x_model.loc[m].copy(), return_dropped=True)
        yi = y.loc[m].astype(float)
        driver_dropped_rows.append(
            {
                "sample": "model_average_across_rules",
                "outcome": outcome,
                "original_columns": ",".join(x_model.columns),
                "kept_columns": ",".join(xi.columns),
                "dropped_columns": ",".join(dropped_cols),
            }
        )

        if outcome in ELASTICITY_OUTCOMES:
            fit = sm.RLM(yi, xi, M=sm.robust.norms.HuberT()).fit(maxiter=200)
            pvals = 2.0 * norm.sf(np.abs(fit.params / fit.bse))
            pvals = pd.Series(pvals, index=fit.params.index)
            params = fit.params
            ses = fit.bse
        else:
            fit = sm.OLS(yi, xi).fit(cov_type="HC1")
            params = fit.params
            ses = fit.bse
            pvals = fit.pvalues

        for f in params.index:
            support_models, support_rows = driver_feature_support(reg_model.loc[m], x_model.loc[m], f, outcome)
            model_rows.append(
                {
                    "sample": "model_average_across_rules",
                    "outcome": outcome,
                    "feature": f,
                    "coef": float(params[f]),
                    "se": float(ses[f]),
                    "p_value": float(pvals[f]),
                    "support_models": support_models,
                    "support_rows": support_rows,
                    "interpretation": interpret_effect(outcome, float(params[f])),
                }
            )

    model_coef = pd.DataFrame(model_rows)
    model_sig = model_coef[
        (model_coef["feature"] != "const")
        & (model_coef["feature"] != "estimated")
        & (model_coef["p_value"] <= 0.10)
    ].copy()
    model_sig = model_sig.sort_values(["outcome", "p_value"]).reset_index(drop=True)
    driver_dropped = pd.DataFrame(driver_dropped_rows)

    return panel_coef, panel_sig, panel_sparse_sig, model_coef, model_sig, driver_dropped


def rf_driver_importance(reg):
    x = build_driver_features(reg)[DRIVER_ALL_FEATURES].copy()
    group_map = {
        "rules": DRIVER_CONTROL_FEATURES[:2],  # rule_itr, rule_g
        "nominal": DRIVER_NOMINAL_FEATURES,
        "real": DRIVER_REAL_FEATURES,
        "nonmodel": ["estimated"] + DRIVER_NONMODEL_FEATURES,
    }

    cv = GroupKFold(n_splits=5)
    rng = np.random.default_rng(42)

    feat_rows = []
    grp_rows = []

    for outcome in OUTCOMES:
        y = pd.to_numeric(reg[outcome], errors="coerce")
        m = y.notna()
        xi = x.loc[m].copy()
        yi = y.loc[m].to_numpy(dtype=float)
        groups = reg.loc[m, "model"].astype(str).to_numpy()

        feat_imp = np.zeros(xi.shape[1], dtype=float)
        grp_drop = {k: [] for k in group_map}
        base_scores = []

        for tr, te in cv.split(xi, yi, groups):
            xtr, xte = xi.iloc[tr].copy(), xi.iloc[te].copy()
            ytr, yte = yi[tr], yi[te]
            rf = RandomForestRegressor(
                n_estimators=250,
                random_state=42,
                min_samples_leaf=3,
                n_jobs=-1,
            )
            rf.fit(xtr, ytr)
            pred = rf.predict(xte)
            base_r2 = float(1.0 - np.sum((yte - pred) ** 2) / np.sum((yte - yte.mean()) ** 2)) if np.var(yte) > 0 else 0.0
            base_scores.append(base_r2)
            feat_imp += rf.feature_importances_

            for gname, cols in group_map.items():
                xp = xte.copy()
                idx = rng.permutation(len(xp))
                xp.loc[:, cols] = xp[cols].to_numpy()[idx]
                pred_p = rf.predict(xp)
                perm_r2 = float(1.0 - np.sum((yte - pred_p) ** 2) / np.sum((yte - yte.mean()) ** 2)) if np.var(yte) > 0 else 0.0
                grp_drop[gname].append(base_r2 - perm_r2)

        feat_imp = feat_imp / cv.get_n_splits()
        for f, imp in zip(xi.columns, feat_imp):
            feat_rows.append({"outcome": outcome, "feature": f, "rf_importance": float(imp)})

        for gname, vals in grp_drop.items():
            grp_rows.append(
                {
                    "outcome": outcome,
                    "group": gname,
                    "base_cv_r2": float(np.mean(base_scores)),
                    "group_permute_r2_drop": float(np.mean(vals)),
                }
            )

    feature_importance = pd.DataFrame(feat_rows).sort_values(["outcome", "rf_importance"], ascending=[True, False]).reset_index(drop=True)
    group_importance = pd.DataFrame(grp_rows).sort_values(["outcome", "group_permute_r2_drop"], ascending=[True, False]).reset_index(drop=True)
    return feature_importance, group_importance


def nonlinear_benchmark(reg):
    x = reg[CORE_FEATURES].copy()
    cv = GroupKFold(n_splits=5)

    models = {
        "Ridge": Pipeline(
            [("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("m", Ridge(alpha=1.0))]
        ),
        "RF": Pipeline(
            [
                ("imp", SimpleImputer(strategy="median")),
                ("m", RandomForestRegressor(n_estimators=120, random_state=42, min_samples_leaf=3, n_jobs=-1)),
            ]
        ),
        "HGB": Pipeline(
            [
                ("imp", SimpleImputer(strategy="median")),
                (
                    "m",
                    HistGradientBoostingRegressor(
                        random_state=42,
                        max_depth=4,
                        learning_rate=0.05,
                        max_iter=120,
                        min_samples_leaf=8,
                    ),
                ),
            ]
        ),
    }

    rows = []
    for outcome in OUTCOMES:
        y = reg[outcome]
        m = y.notna()
        xi = x.loc[m]
        yi = y.loc[m]
        groups = reg.loc[m, "model"].astype(str)
        for name, model in models.items():
            r2 = cross_val_score(model, xi, yi, cv=cv, groups=groups, scoring="r2")
            mae = -cross_val_score(model, xi, yi, cv=cv, groups=groups, scoring="neg_mean_absolute_error")
            rows.append(
                {
                    "outcome": outcome,
                    "model": name,
                    "n_obs": int(len(yi)),
                    "cv_r2_mean": float(r2.mean()),
                    "cv_r2_sd": float(r2.std()),
                    "cv_mae_mean": float(mae.mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(["outcome", "model"]).reset_index(drop=True)


def outlier_sensitivity(reg):
    # 1/99-tail flag on each outcome; keep rows with no flags in trimmed sample.
    flag = pd.Series(False, index=reg.index)
    for outcome in OUTCOMES:
        q1, q99 = reg[outcome].quantile([0.01, 0.99])
        flag = flag | ((reg[outcome] < q1) | (reg[outcome] > q99))

    subsets = {"full": reg.copy(), "trimmed_1_99_any": reg.loc[~flag].copy()}
    models = {
        "Ridge": Pipeline(
            [("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("m", Ridge(alpha=1.0))]
        ),
        "RF": Pipeline(
            [
                ("imp", SimpleImputer(strategy="median")),
                ("m", RandomForestRegressor(n_estimators=200, random_state=42, min_samples_leaf=3, n_jobs=-1)),
            ]
        ),
    }
    cv = GroupKFold(n_splits=5)
    rows = []

    for subset_name, d in subsets.items():
        x = d[CORE_FEATURES]
        for outcome in OUTCOMES:
            y = d[outcome]
            m = y.notna()
            xi = x.loc[m]
            yi = y.loc[m]
            groups = d.loc[m, "model"].astype(str)
            for model_name, model in models.items():
                r2 = cross_val_score(model, xi, yi, cv=cv, groups=groups, scoring="r2")
                rows.append(
                    {
                        "subset": subset_name,
                        "outcome": outcome,
                        "model": model_name,
                        "n_obs": int(len(yi)),
                        "cv_r2_mean": float(r2.mean()),
                    }
                )
    return pd.DataFrame(rows).sort_values(["outcome", "subset", "model"]).reset_index(drop=True)


def write_ward_archetype_figure(out_dir, shape_features, archetype_assignments_wide, archetype_method_outcomes, irf):
    ward = archetype_assignments_wide[["key", "model", "rule", "hierarchical_ward"]].copy()
    ward = ward.rename(columns={"hierarchical_ward": "cluster_raw"})
    ward_outcomes = archetype_method_outcomes[
        archetype_method_outcomes["method"] == "hierarchical_ward"
    ].copy()
    ward_outcomes = ward_outcomes.sort_values("cluster_raw").reset_index(drop=True)

    feature_cols = [c for c in shape_features.columns if c not in ["key", "model", "rule", "cluster_raw", "k_selected", "silhouette"]]
    _, x_scaled = robust_scaled_matrix(shape_features[feature_cols])
    pca = PCA(n_components=2, random_state=42)
    pc = pca.fit_transform(x_scaled)
    plot_df = shape_features[["key", "model", "rule"]].copy()
    plot_df["pc1"] = pc[:, 0]
    plot_df["pc2"] = pc[:, 1]
    plot_df = plot_df.merge(ward, on=["key", "model", "rule"], how="left")

    irf_plot = irf.merge(ward[["key", "cluster_raw"]], on="key", how="inner")
    mean_irf = (
        irf_plot.groupby(["cluster_raw", "period"])[IRF_SHAPE_VARIABLES]
        .mean()
        .reset_index()
        .sort_values(["cluster_raw", "period"])
    )

    clusters = sorted(ward["cluster_raw"].dropna().unique())
    cmap = plt.get_cmap("tab10")
    colors = {c: cmap(i % 10) for i, c in enumerate(clusters)}
    markers = {"Taylor": "o", "Inertial_Taylor": "s", "Growth": "^"}

    fig = plt.figure(figsize=(14, 8.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0])
    ax_scatter = fig.add_subplot(gs[0, :2])
    ax_table = fig.add_subplot(gs[0, 2])
    ax_y = fig.add_subplot(gs[1, 0])
    ax_piq = fig.add_subplot(gs[1, 1])
    ax_irate = fig.add_subplot(gs[1, 2])

    for cluster in clusters:
        dc = plot_df[plot_df["cluster_raw"] == cluster]
        for rule, marker in markers.items():
            dr = dc[dc["rule"] == rule]
            if dr.empty:
                continue
            ax_scatter.scatter(
                dr["pc1"],
                dr["pc2"],
                s=46,
                marker=marker,
                color=colors[cluster],
                edgecolor="white",
                linewidth=0.6,
                alpha=0.85,
            )

    for cluster in clusters:
        dc = plot_df[plot_df["cluster_raw"] == cluster]
        ax_scatter.scatter([], [], color=colors[cluster], label=f"Cluster {int(cluster)} (n={len(dc)})")
    ax_scatter.set_title("Ward archetypes in summary-feature PCA space")
    ax_scatter.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}% of variance)")
    ax_scatter.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}% of variance)")
    ax_scatter.axhline(0, color="#bbbbbb", linewidth=0.7)
    ax_scatter.axvline(0, color="#bbbbbb", linewidth=0.7)
    ax_scatter.grid(color="#e5e5e5", linewidth=0.6)
    ax_scatter.legend(frameon=False, loc="best", fontsize=9)

    for rule, marker in markers.items():
        ax_scatter.scatter([], [], color="#333333", marker=marker, label=rule)
    handles, labels = ax_scatter.get_legend_handles_labels()
    cluster_handles = handles[: len(clusters)]
    cluster_labels = labels[: len(clusters)]
    rule_handles = handles[len(clusters) :]
    rule_labels = labels[len(clusters) :]
    leg1 = ax_scatter.legend(cluster_handles, cluster_labels, frameon=False, loc="upper right", fontsize=9)
    ax_scatter.add_artist(leg1)
    ax_scatter.legend(rule_handles, rule_labels, frameon=False, loc="lower right", fontsize=8)

    ax_table.axis("off")
    table_cols = ["cluster_raw", "n_model_rules", "IScurve20", "infl_per_rr20", "sacratio20", "y_timing_max", "piq_timing_max"]
    table_df = ward_outcomes[table_cols].copy()
    table_df.columns = ["C", "n", "IS", "infl/rr", "sac", "y t*", "pi t*"]
    cell_text = []
    for _, row in table_df.iterrows():
        cell_text.append(
            [
                f"{int(row['C'])}",
                f"{int(row['n'])}",
                f"{row['IS']:.2f}",
                f"{row['infl/rr']:.2f}",
                f"{row['sac']:.1f}",
                f"{row['y t*']:.1f}",
                f"{row['pi t*']:.1f}",
            ]
        )
    table = ax_table.table(
        cellText=cell_text,
        colLabels=table_df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.45)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#d0d0d0")
        if row == 0:
            cell.set_facecolor("#eeeeee")
            cell.set_text_props(weight="bold")
    ax_table.set_title("Ward cluster outcome means", pad=10)

    for ax, var, title in [
        (ax_y, "y", "Mean output IRF"),
        (ax_piq, "piq", "Mean inflation IRF"),
        (ax_irate, "irate", "Mean nominal-rate IRF"),
    ]:
        for cluster in clusters:
            dc = mean_irf[mean_irf["cluster_raw"] == cluster]
            ax.plot(
                dc["period"],
                dc[var],
                color=colors[cluster],
                linewidth=2.0,
                label=f"C{int(cluster)}",
            )
        ax.axhline(0, color="#999999", linewidth=0.8)
        ax.set_title(title)
        ax.set_xlabel("Quarter after shock")
        ax.grid(color="#e5e5e5", linewidth=0.6)
    ax_y.set_ylabel("Response")
    ax_piq.legend(frameon=False, loc="best", ncol=2, fontsize=8)

    fig.suptitle("Ward IRF Archetypes: y, piq, and irate only", fontsize=15, fontweight="bold")
    figure_path = out_dir / "ward_archetype_summary.png"
    fig.savefig(figure_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    description = [
        "Figure: Ward IRF archetype summary.",
        "",
        "What the figure shows: The top-left panel plots each model-rule observation in the first two principal components of the 18 rrate-free IRF summary features used for Ward clustering. Colors indicate Ward clusters and marker shapes indicate policy rules. The top-right table reports cluster sizes and mean outcome measures. The bottom row plots mean IRFs by Ward cluster for output (y), inflation (piq), and the nominal policy rate (irate).",
        "",
        "Axes and units: The scatter axes are principal-component scores from robust-scaled IRF summary features. Bottom-row x-axes are quarters after the monetary policy shock, horizons 0 through 20. Bottom-row y-axes are mean IRF responses in the units of the MMB input data.",
        "",
        "Data source: tasks/data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta and MMB_reg_format.dta, restricted to the disentangle_spaghetti regression sample.",
        "",
        "Key takeaways: Ward clustering separates a broad core group from smaller timing, low-sacrifice, and delayed/high-cost transmission regimes. The Growth rule is prominent in the delayed/high-cost cluster, so archetype membership is partly rule-dependent rather than a pure fixed model type.",
    ]
    (out_dir / "ward_archetype_summary_description.txt").write_text("\n".join(description), encoding="utf-8")


def md_table(df, float_digits=4):
    if df.empty:
        return "(none)"

    rows = []
    cols = list(df.columns)
    int_cols = {c for c in cols if pd.api.types.is_integer_dtype(df[c])}
    rows.append("| " + " | ".join(cols) + " |")
    rows.append("| " + " | ".join(["---"] * len(cols)) + " |")

    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if pd.isna(v):
                vals.append("")
            elif c in int_cols:
                vals.append(str(int(v)))
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{v:.{float_digits}f}")
            else:
                vals.append(str(v).replace("|", "\\|").replace("\n", " "))
        rows.append("| " + " | ".join(vals) + " |")

    return "\n".join(rows)


def build_report(
    out_dir,
    var_decomp,
    rank_stability,
    rule_contrasts,
    panel_driver_sig,
    panel_driver_sparse_sig,
    model_driver_sig,
    rf_feature_importance,
    rf_group_importance,
    cluster_outcomes,
    cluster_prevalence,
    cluster_stability_summary,
    cluster_stability_models,
    archetype_method_comparison,
    archetype_method_outcomes,
    archetype_method_prevalence,
    archetype_method_stability_summary,
    fpca_variance,
    nonlinear,
    sensitivity,
    outliers,
):
    ratio_df = var_decomp.copy()
    ratio_df["model_to_rule_increment_ratio"] = (
        ratio_df["inc_model_given_rule"] / ratio_df["inc_rule_given_model"].replace(0.0, np.nan)
    )

    switchers = cluster_stability_models[cluster_stability_models["stability_class"] == "rule_switcher"].copy()
    n_models = int(cluster_stability_summary["n_models"].sum())
    n_switchers = len(switchers)
    n_stable = n_models - n_switchers
    baseline_k = int(cluster_outcomes["cluster_raw"].nunique())
    fast_cluster = int(cluster_outcomes.sort_values("y_timing_max").iloc[0]["cluster_raw"])
    slow_cluster = int(cluster_outcomes.sort_values("y_timing_max").iloc[-1]["cluster_raw"])
    fast_means = cluster_outcomes.loc[cluster_outcomes["cluster_raw"] == fast_cluster].iloc[0]
    slow_means = cluster_outcomes.loc[cluster_outcomes["cluster_raw"] == slow_cluster].iloc[0]

    panel_sig_short = panel_driver_sig[
        [
            "outcome",
            "feature",
            "coef",
            "p_value",
            "support_models",
            "support_rows",
            "interpretation",
        ]
    ].copy()
    panel_sparse_short = panel_driver_sparse_sig[
        [
            "outcome",
            "feature",
            "coef",
            "p_value",
            "support_models",
            "support_rows",
            "interpretation",
        ]
    ].copy()
    model_sig_short = model_driver_sig[
        [
            "outcome",
            "feature",
            "coef",
            "p_value",
            "support_models",
            "support_rows",
            "interpretation",
        ]
    ].copy()

    rf_top = (
        rf_feature_importance.sort_values(["outcome", "rf_importance"], ascending=[True, False])
        .groupby("outcome")
        .head(8)
        .reset_index(drop=True)
    )

    lines = []
    lines.append("# Disentangle Spaghetti Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("Dataset and scope:")
    lines.append("- Inputs are `MMB_reg_format.dta` and `MMB_IRF_format_full.dta` from `tasks/data/build_mmb_analysis_dataset/output`.")
    lines.append("- The regression sample drops model-rule observations with timing sentinels equal to 99 and observations missing model or rule IDs.")
    lines.append("- IRF archetypes use horizons 0 through 20 and are built from `y`, `piq`, and `irate` only; `rrate` is excluded because it is a lagged linear combination of `irate` and `piq`.")
    lines.append("")
    lines.append("Identification used for driver analysis:")
    lines.append("- Main inference uses regressions with **rule controls** (`rule_itr`, `rule_g`) and model/non-model attributes as regressors.")
    lines.append("- We **do not** use model fixed effects to infer attribute effects, because model FE absorb time-invariant attributes.")
    lines.append("- Model FE analysis is included only as a diagnostic for where raw variance sits.")
    lines.append("")
    lines.append("Main conclusions:")
    lines.append(
        f"- Timing heterogeneity is driven most consistently by non-model features: `estimated` and `cb_authors_ext` are positive and significant in timing regressions; `cb_x_late` is negative for inflation timing."
    )
    lines.append(
        f"- Output-power heterogeneity is linked to real-friction channels and nominal wage structure, while sparse interaction terms are separated from the headline evidence."
    )
    lines.append(
        f"- Inflation-power and disinflation-cost heterogeneity are tied to wage indexation structure: `sw_x_idx` raises `infl_per_rr20` (weaker inflation response) and raises `sacratio20` (higher disinflation cost), while `pr_ndx` lowers `sacratio20`."
    )
    lines.append(
        f"- Excluding `rrate` changes the baseline archetype structure: summary-feature k-means selects {baseline_k} clusters; {n_stable} of {n_models} models are stable across rules and {n_switchers} switch clusters across rules."
    )
    lines.append("")

    lines.append("## 1) Diagnostic: Model vs Rule Variance Decomposition")
    lines.append("")
    lines.append("What this does: for each outcome, estimate rule-only, model-only, and rule-plus-model fixed-effect regressions. The incremental columns ask how much R-squared is added by rules after model fixed effects and by models after rule fixed effects.")
    lines.append("")
    lines.append(md_table(var_decomp))
    lines.append("")
    lines.append("Model-vs-rule dominance ratio (`inc_model_given_rule / inc_rule_given_model`):")
    lines.append(md_table(ratio_df[["outcome", "model_to_rule_increment_ratio"]], float_digits=2))
    lines.append("")
    lines.append("Finding: raw heterogeneity sits overwhelmingly at the model level rather than the policy-rule level. This section is diagnostic only; it does not identify attribute effects because model fixed effects absorb time-invariant model attributes.")
    lines.append("")
    lines.append("Paper interpretation: rule choice matters for levels, but the paper should frame cross-model heterogeneity as a model-architecture object first and a rule-choice object second.")
    lines.append("")

    lines.append("## 2) Driver Regressions (Rule-Controlled, No Model FE)")
    lines.append("")
    lines.append("What this does: regress each outcome on rule controls and model/non-model attributes. Elasticity and sacrifice-ratio outcomes use robust linear models with model-clustered inference; timing outcomes use Poisson GLMs, with negative-binomial GLMs used when an auxiliary overdispersion test rejects equidispersion, and model-clustered covariance. A model-averaged check collapses observations to one row per model; timing outcomes in that check are treated as continuous averaged outcomes and fit by linear regressions with HC1 standard errors.")
    lines.append("")
    lines.append(f"Sparse significant terms with fewer than {MIN_DRIVER_SUPPORT_MODELS} supporting models are excluded from the headline driver table and reported separately.")
    lines.append("")
    lines.append("Significant attribute drivers (panel, p<=0.10; rules forced in and omitted from this list):")
    if panel_sig_short.empty:
        lines.append("(none)")
    else:
        lines.append(md_table(panel_sig_short))
    lines.append("")
    lines.append(f"Sparse significant panel terms excluded from the headline table (p<=0.10 and support models < {MIN_DRIVER_SUPPORT_MODELS}):")
    if panel_sparse_short.empty:
        lines.append("(none)")
    else:
        lines.append(md_table(panel_sparse_short))
    lines.append("")
    lines.append("Significant attribute drivers in model-averaged check (p<=0.10):")
    if model_sig_short.empty:
        lines.append("(none)")
    else:
        lines.append(md_table(model_sig_short))
    lines.append("")
    lines.append("Finding: output-power differences are tied to banking, firm balance sheet, and household demand, while sparse interaction terms need separate caveating. Inflation-power and sacrifice-ratio differences are most clearly tied to wage-indexation structure. Timing differences are much more closely associated with non-model attributes such as estimated-model status, central-bank authorship, equation count, and vintage interactions.")
    lines.append("")
    lines.append("Paper interpretation: the paper can argue that heterogeneity is structured rather than purely residual, but it should avoid treating any one structural friction as a universal sufficient statistic for transmission.")
    lines.append("")

    lines.append("## 3) Cross-Rule Rank Stability")
    lines.append("")
    lines.append("What this does: pivot each outcome to a model-by-rule matrix and compute Spearman rank correlations and Pearson raw-value correlations for each rule pair.")
    lines.append("")
    lines.append(md_table(rank_stability))
    lines.append("")
    lines.append("Finding: model ranking persistence across rules is high, especially for timing and sacrifice ratios. Inflation-slope rankings are less stable when the Growth rule is involved.")
    lines.append("")
    lines.append("Paper interpretation: policy rules shift outcomes, but they usually do not reshuffle which models are high- or low-transmission models.")
    lines.append("")

    lines.append("## 4) Within-Model Rule Contrasts")
    lines.append("")
    lines.append("What this does: for each model observed under a pair of rules, compute the within-model difference between rules and test whether the mean difference is zero. The same contrast is also split by calibrated versus estimated models.")
    lines.append("")
    lines.append(md_table(rule_contrasts))
    lines.append("")
    lines.append("Finding: rules shift levels and timing. Growth and inertial Taylor rules often produce stronger output/inflation responses than Taylor in estimated models, while timing tends to move later under Growth and inertial Taylor.")
    lines.append("")
    lines.append("Paper interpretation: the rule dimension is still economically meaningful, but it is mostly a level/timing shift layered on persistent model heterogeneity.")
    lines.append("")

    lines.append("## 5) ML Cross-Check on Drivers")
    lines.append("")
    lines.append("Cross-validation folds are grouped by model, so all rule observations for a given model are assigned to the same fold.")
    lines.append("")
    lines.append("Top random-forest feature importances by outcome (rule controls included):")
    lines.append(md_table(rf_top))
    lines.append("")
    lines.append("Grouped importance via group-permutation drop in holdout R2:")
    lines.append(md_table(rf_group_importance))
    lines.append("")
    lines.append("Finding: non-model features dominate timing predictability; rules and real frictions are important for inflation-slope predictability; nominal variables are especially important for sacrifice-ratio predictability.")
    lines.append("")
    lines.append("Paper interpretation: nonlinear prediction results reinforce the regression interpretation for timing and nominal-rigidity channels, but weak or negative holdout R-squared in some slope/cost outcomes means these should remain cross-checks rather than headline estimates.")
    lines.append("")

    lines.append("## 6) IRF Archetypes")
    lines.append("")
    lines.append("What this does: summarize each model-rule IRF through horizon 20 using cumulative response, peak, trough, within-path standard deviation, time to peak, and time to trough for `y`, `piq`, and `irate`. Each feature is winsorized at the 2nd/98th percentiles and robust-scaled. K-means is run for k=2 through k=6, and the k with the best silhouette score is selected.")
    lines.append("")
    lines.append("Additional archetype checks use three alternatives: functional PCA plus k-means on the full y/piq/irate paths, Ward hierarchical clustering on the same 18 summary features, and a diagonal-covariance Gaussian mixture model selected by BIC.")
    lines.append("")
    lines.append("GMM is included as an exploratory fine-clustering check; even with diagonal covariance, its selected k should not be interpreted as a preferred taxonomy.")
    lines.append("")
    lines.append("![Ward archetype summary](ward_archetype_summary.png)")
    lines.append("")
    lines.append("Cluster outcome means:")
    lines.append(md_table(cluster_outcomes))
    lines.append("")
    lines.append("Cluster attribute prevalence:")
    lines.append(md_table(cluster_prevalence))
    lines.append("")
    lines.append("Model-level cluster stability:")
    lines.append(md_table(cluster_stability_summary))
    lines.append("")
    lines.append(
        f"Lowest-output-timing cluster {fast_cluster} has mean y_timing={fast_means['y_timing_max']:.2f}, pi_timing={fast_means['piq_timing_max']:.2f}, "
        f"IScurve20={fast_means['IScurve20']:.2f}, and sacratio20={fast_means['sacratio20']:.2f}. "
        f"Highest-output-timing cluster {slow_cluster} has mean y_timing={slow_means['y_timing_max']:.2f}, pi_timing={slow_means['piq_timing_max']:.2f}, "
        f"IScurve20={slow_means['IScurve20']:.2f}, and sacratio20={slow_means['sacratio20']:.2f}."
    )
    lines.append("")
    lines.append("Rule-switcher models:")
    if switchers.empty:
        lines.append("(none)")
    else:
        lines.append(md_table(switchers))
    lines.append("")
    lines.append(f"Finding: after removing `rrate`, the baseline summary-feature k-means specification selects {baseline_k} clusters rather than the earlier two-cluster split. The broad middle cluster is large, but {n_switchers} of {n_models} models switch cluster across rules, so rule-dependent archetype movement is no longer a negligible edge case.")
    lines.append("")
    lines.append("Paper interpretation: the archetype evidence still supports structured transmission heterogeneity, but the rrate-free result is better described as a broad middle plus smaller timing and path-shape groups, not as a clean binary taxonomy.")
    lines.append("")
    lines.append("### Archetype Method Comparison")
    lines.append("")
    lines.append("What this does: compare the baseline summary-feature k-means clusters with the requested alternatives. `ari_vs_summary_kmeans` is the adjusted Rand index relative to the baseline; 1 means identical assignments up to label permutation, 0 means chance-level agreement, and negative values mean less agreement than chance.")
    lines.append("")
    lines.append(md_table(archetype_method_comparison))
    lines.append("")
    lines.append("FPCA variance retained:")
    lines.append(md_table(fpca_variance))
    lines.append("")
    lines.append("Outcome means by method and cluster:")
    lines.append(md_table(archetype_method_outcomes))
    lines.append("")
    lines.append("Attribute prevalence by method and cluster:")
    lines.append(md_table(archetype_method_prevalence))
    lines.append("")
    lines.append("Model-level stability by method:")
    lines.append(md_table(archetype_method_stability_summary))
    lines.append("")
    lines.append("Finding: hierarchical Ward clustering is close to the baseline summary-feature k-means split, while FPCA on the full paths isolates a small extreme timing group and diagonal-covariance GMM selects finer subclusters. The existence of structure is robust; the exact number and interpretation of clusters is method-sensitive.")
    lines.append("")
    lines.append("Paper interpretation: use the simple summary-feature k-means archetypes for exposition only if the paper wants a transparent descriptive compression. The safer claim is that IRF paths contain stable low-dimensional structure, while the exact archetype labels should be treated as empirical summaries rather than primitives.")
    lines.append("")

    lines.append("## 7) Nonlinear vs Linear Benchmark (CV)")
    lines.append("")
    lines.append("What this does: compare cross-validated predictive performance of ridge, random forest, and histogram gradient boosting models using the core rule/model attributes. Cross-validation folds are grouped by model.")
    lines.append("")
    lines.append(md_table(nonlinear))
    lines.append("")
    lines.append("Finding: nonlinear models materially improve fit for timing. Predictive fit remains weak or unstable for several slope/cost outcomes, especially in the full sample.")
    lines.append("")
    lines.append("Paper interpretation: interactions and nonlinearities matter, but the paper should not oversell predictive completeness. Large residual heterogeneity remains.")
    lines.append("")

    lines.append("## 8) Outlier Sensitivity")
    lines.append("")
    lines.append("What this does: flag any model-rule observation lying outside the 1st/99th percentile for any outcome, then compare full-sample and trimmed-sample cross-validated prediction.")
    lines.append("")
    lines.append("Extreme rows (1/99-tail on any outcome):")
    lines.append(md_table(outliers, float_digits=6))
    lines.append("")
    lines.append("Predictive sensitivity (full vs trimmed):")
    lines.append(md_table(sensitivity))
    lines.append("")
    lines.append("Finding: a small number of extreme model-rule observations matter for predictive fit. Trimming improves some outcomes substantially, especially inflation slope and sacrifice ratio.")
    lines.append("")
    lines.append("Paper interpretation: the paper should either report outlier-robust checks or explicitly discuss that a few extreme model-rule cases carry meaningful leverage in predictive exercises.")
    lines.append("")

    lines.append("## 9) So What")
    lines.append("")
    lines.append("- The main empirical split is **speed/persistence**, not just slope magnitudes.")
    lines.append("- `estimated`, `cb_authors_ext`, and vintage interactions matter most for timing outcomes.")
    lines.append("- Wage-indexation design is the clearest nominal-rigidity driver of inflation effectiveness/cost tradeoffs.")
    lines.append("- Real-friction interactions matter for output power but do not robustly map one-for-one into inflation power.")
    lines.append("- Therefore, “not much explains differences” is too pessimistic: differences are structured around a few recurring channels, with large residual heterogeneity still present.")
    lines.append("")

    (out_dir / "findings_report.md").write_text("\n".join(lines), encoding="utf-8")


out_dir = OUTPUT_DIR / "disentangle_spaghetti"
if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

reg, irf = load_data()

print("Loaded regression rows:", len(reg))
print("Loaded IRF rows (<=20q):", len(irf))

var_decomp = variance_decomposition(reg)
rank_stability = rule_rank_stability(reg)
rule_contrasts = within_model_rule_contrasts(reg)
(
    panel_driver_coef,
    panel_driver_sig,
    panel_driver_sparse_sig,
    model_driver_coef,
    model_driver_sig,
    driver_dropped_terms,
) = attribute_driver_models(reg)
rf_feature_importance, rf_group_importance = rf_driver_importance(reg)
outliers = outlier_table(reg)
(
    shape_features,
    cluster_merged,
    cluster_outcomes,
    cluster_prevalence,
    archetype_assignments_wide,
    archetype_assignments_long,
    archetype_method_comparison,
    archetype_method_outcomes,
    archetype_method_prevalence,
    archetype_method_stability_models,
    archetype_method_stability_summary,
    fpca_variance,
) = cluster_archetypes(reg, irf)
cluster_stability_models, cluster_stability_summary = cluster_stability(shape_features, cluster_outcomes)
nonlinear = nonlinear_benchmark(reg)
sensitivity = outlier_sensitivity(reg)

# Save raw outputs
var_decomp.to_csv(out_dir / "variance_decomposition.csv", index=False)
rank_stability.to_csv(out_dir / "rule_rank_stability.csv", index=False)
rule_contrasts.to_csv(out_dir / "within_model_rule_contrasts.csv", index=False)
panel_driver_coef.to_csv(out_dir / "attribute_driver_panel_coefficients.csv", index=False)
panel_driver_sig.to_csv(out_dir / "attribute_driver_panel_significant.csv", index=False)
panel_driver_sparse_sig.to_csv(out_dir / "attribute_driver_panel_sparse_significant.csv", index=False)
model_driver_coef.to_csv(out_dir / "attribute_driver_modelavg_coefficients.csv", index=False)
model_driver_sig.to_csv(out_dir / "attribute_driver_modelavg_significant.csv", index=False)
driver_dropped_terms.to_csv(out_dir / "attribute_driver_dropped_collinear_terms.csv", index=False)
rf_feature_importance.to_csv(out_dir / "rf_feature_importance.csv", index=False)
rf_group_importance.to_csv(out_dir / "rf_group_importance.csv", index=False)
outliers.to_csv(out_dir / "outlier_table_1_99.csv", index=False)
shape_features.to_csv(out_dir / "irf_shape_features.csv", index=False)
cluster_merged.to_csv(out_dir / "irf_archetype_assignments.csv", index=False)
cluster_outcomes.to_csv(out_dir / "irf_archetype_outcome_means.csv", index=False)
cluster_prevalence.to_csv(out_dir / "irf_archetype_attribute_prevalence.csv", index=False)
cluster_stability_models.to_csv(out_dir / "irf_archetype_model_stability.csv", index=False)
cluster_stability_summary.to_csv(out_dir / "irf_archetype_stability_summary.csv", index=False)
archetype_assignments_wide.to_csv(out_dir / "irf_archetype_assignments_wide_methods.csv", index=False)
archetype_assignments_long.to_csv(out_dir / "irf_archetype_assignments_long_methods.csv", index=False)
archetype_method_comparison.to_csv(out_dir / "irf_archetype_method_comparison.csv", index=False)
archetype_method_outcomes.to_csv(out_dir / "irf_archetype_method_outcome_means.csv", index=False)
archetype_method_prevalence.to_csv(out_dir / "irf_archetype_method_attribute_prevalence.csv", index=False)
archetype_method_stability_models.to_csv(out_dir / "irf_archetype_method_model_stability.csv", index=False)
archetype_method_stability_summary.to_csv(out_dir / "irf_archetype_method_stability_summary.csv", index=False)
fpca_variance.to_csv(out_dir / "irf_archetype_fpca_variance.csv", index=False)
nonlinear.to_csv(out_dir / "nonlinear_benchmark_cv.csv", index=False)
sensitivity.to_csv(out_dir / "outlier_sensitivity_cv.csv", index=False)

build_report(
    out_dir=out_dir,
    var_decomp=var_decomp,
    rank_stability=rank_stability,
    rule_contrasts=rule_contrasts,
    panel_driver_sig=panel_driver_sig,
    panel_driver_sparse_sig=panel_driver_sparse_sig,
    model_driver_sig=model_driver_sig,
    rf_feature_importance=rf_feature_importance,
    rf_group_importance=rf_group_importance,
    cluster_outcomes=cluster_outcomes,
    cluster_prevalence=cluster_prevalence,
    cluster_stability_summary=cluster_stability_summary,
    cluster_stability_models=cluster_stability_models,
    archetype_method_comparison=archetype_method_comparison,
    archetype_method_outcomes=archetype_method_outcomes,
    archetype_method_prevalence=archetype_method_prevalence,
    archetype_method_stability_summary=archetype_method_stability_summary,
    fpca_variance=fpca_variance,
    nonlinear=nonlinear,
    sensitivity=sensitivity,
    outliers=outliers,
)

write_ward_archetype_figure(
    out_dir=out_dir,
    shape_features=shape_features,
    archetype_assignments_wide=archetype_assignments_wide,
    archetype_method_outcomes=archetype_method_outcomes,
    irf=irf,
)

manifest = pd.DataFrame(
    [
        {"file": p.name, "description": "Disentangle spaghetti output file."}
        for p in sorted(out_dir.iterdir())
        if p.is_file()
    ]
)
manifest.to_csv(OUTPUT_DIR / "manifest.csv", index=False)

print("Wrote disentangle outputs to:", out_dir)
print(" -", out_dir / "findings_report.md")
print(" -", out_dir / "variance_decomposition.csv")
print(" -", out_dir / "rule_rank_stability.csv")
print(" -", out_dir / "within_model_rule_contrasts.csv")
print(" -", out_dir / "attribute_driver_panel_significant.csv")
print(" -", out_dir / "attribute_driver_panel_sparse_significant.csv")
print(" -", out_dir / "rf_group_importance.csv")
print(" -", out_dir / "irf_archetype_assignments.csv")
print(" -", out_dir / "irf_archetype_stability_summary.csv")
print(" -", out_dir / "irf_archetype_method_comparison.csv")
print(" -", out_dir / "ward_archetype_summary.png")
print(" -", out_dir / "nonlinear_benchmark_cv.csv")
print(" -", OUTPUT_DIR / "manifest.csv")
