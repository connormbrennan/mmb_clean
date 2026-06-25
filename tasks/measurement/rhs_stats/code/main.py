#!/usr/bin/env python3
"""
Purpose:
  Build a descriptive table of model and non-model RHS attribute averages.

Inputs:
  ../input/MMB_reg_format.dta
  ../../../../config/params.yaml

Outputs:
  ../output/table_rhs_stats.tex
  ../output/table_rhs_stats.csv
  ../output/manifest.csv

Run:
  make -C tasks/measurement/rhs_stats
"""

from pathlib import Path
import shutil

import pandas as pd
import yaml


TASK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = Path(__file__).resolve().parents[4]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
for path in OUTPUT_DIR.iterdir():
    if path.name == ".gitkeep":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

with open(REPO_DIR / "config" / "params.yaml", "r", encoding="utf-8") as f:
    params = yaml.safe_load(f)

var_labels = params["mmb_regression_tables"]["var_labels"]

# Step 1: Load the final analysis dataset and collapse to one row per final model.
# This keeps the RHS attribute table on the same model universe as the analysis tables.
raw = pd.read_stata(INPUT_DIR / "MMB_reg_format.dta")

channel_vars = ["hh_demand", "firm_bs", "bank", "labor_frict"]
table_vars = [
    "stky_pr",
    "stky_wg",
    "pr_ndx",
    "wg_ndx",
    "open",
    "cb_authors_ext",
    "estimated",
    "neq",
    "vint_early",
    "vint_mid",
    "vint_late",
    "est_early",
    "est_late",
] + channel_vars

required_cols = ["model"] + table_vars
missing_cols = [col for col in required_cols if col not in raw.columns]
if missing_cols:
    raise ValueError(f"Missing required columns in MMB_reg_format.dta: {missing_cols}")

for col in table_vars:
    raw[col] = pd.to_numeric(raw[col], errors="coerce")

# Model-level attributes should not vary across policy-rule rows.
conflicts = []
for col in table_vars:
    nunique_by_model = raw.groupby("model")[col].nunique(dropna=False)
    bad_models = nunique_by_model[nunique_by_model > 1].index.tolist()
    if bad_models:
        conflicts.append((col, bad_models[:10]))

if conflicts:
    raise ValueError(
        "Model-level RHS variables vary within model across rows: "
        + "; ".join(f"{col}: {models}" for col, models in conflicts)
    )

rhs = raw.sort_values("model").drop_duplicates("model").copy()

# Step 2: Recompute the any-channel indicator from the four current channel codings.
rhs["channels_any"] = rhs[channel_vars].max(axis=1)

full_sample_n = int(rhs["model"].nunique())
estimated_sample = rhs.loc[rhs["estimated"] == 1].copy()
estimated_sample_n = int(estimated_sample["model"].nunique())

row_specs = [
    {"row_type": "section", "section": "Model attributes: Nominal rigidities", "label": "Model attributes: Nominal rigidities"},
    {"row_type": "data", "section": "Model attributes: Nominal rigidities", "number": "1.", "label": "Price stickiness (any source)", "variable": "stky_pr", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Nominal rigidities", "number": "2.", "label": var_labels["stky_wg"], "variable": "stky_wg", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Nominal rigidities", "number": "3.", "label": var_labels["pr_ndx"] + "*", "variable": "pr_ndx", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Nominal rigidities", "number": "4.", "label": var_labels["wg_ndx"] + "*", "variable": "wg_ndx", "sample": "full", "digits": 2},
    {"row_type": "section", "section": "Model attributes: Real rigidities", "label": "Model attributes: Real rigidities"},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": "5.", "label": "Channels (any source)", "variable": "channels_any", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": r"\quad a.", "label": var_labels["hh_demand"], "variable": "hh_demand", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": r"\quad b.", "label": var_labels["firm_bs"], "variable": "firm_bs", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": r"\quad c.", "label": var_labels["bank"], "variable": "bank", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": r"\quad d.", "label": var_labels["labor_frict"], "variable": "labor_frict", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Model attributes: Real rigidities", "number": "6.", "label": var_labels["open"], "variable": "open", "sample": "full", "digits": 2},
    {"row_type": "section", "section": "Non-model attributes", "label": "Non-model attributes"},
    {"row_type": "data", "section": "Non-model attributes", "number": "7.", "label": "At least one central bank author", "variable": "cb_authors_ext", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "8.", "label": "Estimated model", "variable": "estimated", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "9.", "label": "Number of structural equations", "variable": "neq", "sample": "full", "digits": 1},
    {"row_type": "data", "section": "Non-model attributes", "number": "10.", "label": r"Early vintage publication ($<$ 2000)", "variable": "vint_early", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "11.", "label": r"Middle vintage publication (2000--2007)", "variable": "vint_mid", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "12.", "label": r"Late vintage publication ($>$ 2007)", "variable": "vint_late", "sample": "full", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "13.", "label": r"Early sample estimation data ($<$ 1980)**", "variable": "est_early", "sample": "estimated", "digits": 2},
    {"row_type": "data", "section": "Non-model attributes", "number": "14.", "label": "Late sample estimation data (1980+)**", "variable": "est_late", "sample": "estimated", "digits": 2},
]

# Step 3: Compute simple model-level averages and keep row counts visible in the CSV.
table_rows = []
for spec in row_specs:
    if spec["row_type"] == "section":
        table_rows.append(
            {
                "row_type": "section",
                "section": spec["section"],
                "number": "",
                "label": spec["label"],
                "variable": "",
                "sample": "",
                "average": pd.NA,
                "n": pd.NA,
                "formatted_average": "",
            }
        )
        continue

    sample_df = rhs
    if spec["sample"] == "estimated":
        sample_df = estimated_sample

    values = pd.to_numeric(sample_df[spec["variable"]], errors="coerce")
    average = values.mean()
    formatted_average = f"{average:.{spec['digits']}f}"
    table_rows.append(
        {
            "row_type": "data",
            "section": spec["section"],
            "number": spec["number"],
            "label": spec["label"],
            "variable": spec["variable"],
            "sample": spec["sample"],
            "average": average,
            "n": int(values.notna().sum()),
            "formatted_average": formatted_average,
        }
    )

table = pd.DataFrame(table_rows)
table.to_csv(OUTPUT_DIR / "table_rhs_stats.csv", index=False)

# Step 4: Render the manuscript-style LaTeX table.
latex_lines = [
    r"\begin{table}[H]",
    r"\centering",
    r"\caption{ \\ \underline{Model and non-model attribute variables}}",
    r"\label{tab:rhs_attributes}",
    r"\small",
    r"\begin{tabular}{l c}",
    r"\toprule",
    r"\textit{Variable} & \textit{Average value} \\",
    r"\midrule",
]

for _, row in table.iterrows():
    if row["row_type"] == "section":
        latex_lines.append(r"\textbf{" + row["label"] + r"} & \\")
    else:
        latex_lines.append(row["number"] + " " + row["label"] + " & " + row["formatted_average"] + r" \\")

note = (
    r"\multicolumn{2}{p{12cm}}{\footnotesize Notes: * Price (or wage) indexation "
    r"implies sticky prices (or wages); the converse is not always true. "
    r"Channels (any source) is the union of the four current channel indicators. "
    rf"$n = {full_sample_n}$. **Estimation-sample rows use estimated models only, "
    rf"for which $n = {estimated_sample_n}$; otherwise, $n = {full_sample_n}$. "
    r"Source: authors' calculations based on hand-coded MMB model attributes.}"
)

latex_lines.extend(
    [
        r"\bottomrule",
        note,
        r"\end{tabular}",
        r"\end{table}",
    ]
)

(OUTPUT_DIR / "table_rhs_stats.tex").write_text("\n".join(latex_lines) + "\n", encoding="utf-8")

manifest = pd.DataFrame(
    [
        {"file": "table_rhs_stats.tex", "description": "LaTeX table of model and non-model RHS attribute averages."},
        {"file": "table_rhs_stats.csv", "description": "Underlying row-level averages and sample sizes for the RHS attributes table."},
        {"file": "manifest.csv", "description": "Manifest of RHS-stats task outputs."},
    ]
)
manifest.to_csv(OUTPUT_DIR / "manifest.csv", index=False)
