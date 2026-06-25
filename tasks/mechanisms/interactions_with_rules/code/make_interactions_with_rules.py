#!/usr/bin/env python3
"""
Purpose:
  Estimate how selected model attributes interact with policy rules.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/interactions_with_rules/
  ../output/manifest.csv

Run:
  make
"""

from pathlib import Path
import os
import shutil
import warnings

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.robust import norms, scale


task_dir = Path(__file__).resolve().parents[1]
input_dir = task_dir / "input"
output_dir = task_dir / "output"
table_dir = output_dir / "interactions_with_rules"

if table_dir.exists():
    shutil.rmtree(table_dir)
table_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_stata(input_dir / "MMB_reg_format.dta")

attributes = [
    "bank",
    "firm_bs",
    "hh_demand",
    "labor_frict",
    "other_channel",
    "stky_pr",
    "stky_pr_calvo",
    "stky_pr_other",
    "stky_pr_rotemberg",
]

outcome_bases = [
    "IScurve",
    "infl_per_rr",
    "sacratio",
    "Billsacrat",
]

horizons = [20, 40, 60]

manifest_rows = []
for outcome_base in outcome_bases:
    for attribute in attributes:
        records = []
        for horizon in horizons:
            depvar = f"{outcome_base}{horizon}"
            if depvar not in df.columns or attribute not in df.columns:
                continue
            data = df[[depvar, attribute, "rule_g", "rule_itr"]].dropna().copy()
            formula = f"{depvar} ~ {attribute} + rule_g + rule_itr + {attribute}:rule_g + {attribute}:rule_itr"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = smf.rlm(
                    formula,
                    data=data,
                    M=norms.TukeyBiweight(c=4.685),
                ).fit(
                    scale_est=scale.HuberScale(),
                    update_scale=True,
                    cov="H1",
                    conv="coefs",
                )
            for term in fit.params.index:
                records.append(
                    {
                        "horizon": horizon,
                        "term": term,
                        "coef": fit.params[term],
                        "se": fit.bse[term],
                        "p_value": fit.pvalues[term],
                        "nobs": int(fit.nobs),
                    }
                )

        result = pd.DataFrame(records)
        csv_path = table_dir / f"{outcome_base}_{attribute}.csv"
        result.to_csv(csv_path, index=False)

        fig, ax = plt.subplots(figsize=(10, 6))
        plot_terms = [f"{attribute}:rule_g", f"{attribute}:rule_itr"]
        for term, color in [(plot_terms[0], "#2f6f3e"), (plot_terms[1], "#1f4e79")]:
            d = result.loc[result["term"] == term].copy()
            if d.empty:
                continue
            ax.errorbar(
                d["horizon"],
                d["coef"],
                yerr=1.645 * d["se"],
                marker="o",
                capsize=3,
                label=term,
                color=color,
            )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"{outcome_base}: {attribute} interactions with rules")
        ax.set_xlabel("Horizon")
        ax.set_ylabel("Interaction coefficient")
        ax.legend(frameon=False)
        fig.tight_layout()
        pdf_path = table_dir / f"{outcome_base}_{attribute}.pdf"
        fig.savefig(pdf_path)
        plt.close(fig)

        with open(table_dir / f"{outcome_base}_{attribute}_description.txt", "w", encoding="utf-8") as f:
            f.write(f"Figure: {pdf_path.name}\n")
            f.write(f"Shows robust-regression interaction coefficients for {attribute} with rule_g and rule_itr.\n")
            f.write(f"Outcome family: {outcome_base}; horizons: 20, 40, 60.\n")
            f.write("Intervals: 90 percent confidence intervals.\n")
            f.write("Data source: ../input/MMB_reg_format.dta.\n")

        manifest_rows.append(
            {
                "file": f"interactions_with_rules/{pdf_path.name}",
                "table": f"interactions_with_rules/{csv_path.name}",
                "outcome": outcome_base,
                "attribute": attribute,
            }
        )

pd.DataFrame(manifest_rows).to_csv(output_dir / "manifest.csv", index=False)
print(f"Wrote {len(manifest_rows)} interaction figures to {table_dir}.")
