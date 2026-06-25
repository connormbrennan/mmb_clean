#!/usr/bin/env python3
"""
Purpose:
  Decompose monetary-transmission outcome variation into policy-rule and
  model fixed-effect components.

Inputs:
  ../input/MMB_reg_format.dta
  ../../../../config/params.yaml

Outputs:
  ../output/model_vs_rule_variance_decomposition.csv
  ../output/model_vs_rule_variance_decomposition.tex
  ../output/model_vs_rule_variance_decomposition.pdf
  ../output/model_vs_rule_variance_decomposition.png
  ../output/model_vs_rule_variance_decomposition_description.txt
  ../output/findings_note.md
  ../output/manifest.csv

Run:
  From this code directory, run: make all
"""

from pathlib import Path
import os
import shutil
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mmb_matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import yaml


TASK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = Path(__file__).resolve().parents[4]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
CONFIG_PATH = REPO_DIR / "config" / "params.yaml"

DATA_PATH = INPUT_DIR / "MMB_reg_format.dta"

EXPECTED_RULES = ["Taylor", "Inertial_Taylor", "Growth"]
OUTCOMES = [
    ("IScurve20", "y-slope"),
    ("infl_per_rr20", "pi-slope"),
    ("sacratio20", "sacrifice ratio"),
    ("y_timing_max", "y-timing"),
    ("piq_timing_max", "pi-timing"),
]
FIGURE_LABELS = {
    "y-slope": "y-slope",
    "pi-slope": "π-slope",
    "sacrifice ratio": "sacrifice ratio",
    "y-timing": "y-timing",
    "pi-timing": "π-timing",
}
RATIO_DENOMINATOR_MIN = 1.0e-10

CSV_PATH = OUTPUT_DIR / "model_vs_rule_variance_decomposition.csv"
TEX_PATH = OUTPUT_DIR / "model_vs_rule_variance_decomposition.tex"
PDF_PATH = OUTPUT_DIR / "model_vs_rule_variance_decomposition.pdf"
PNG_PATH = OUTPUT_DIR / "model_vs_rule_variance_decomposition.png"
DESCRIPTION_PATH = OUTPUT_DIR / "model_vs_rule_variance_decomposition_description.txt"
FINDINGS_PATH = OUTPUT_DIR / "findings_note.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Step 1: this task owns its output directory, so remove stale artifacts first.
for path in OUTPUT_DIR.iterdir():
    if path.name == ".gitkeep":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

# Step 2: load the paper-sample timing cutoff from the shared project params.
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

time_limit = config["mmb"]["time_limit"]
if time_limit != 99:
    raise ValueError(f"This task expects the paper timing cutoff to be 99, found {time_limit}.")

raw = pd.read_stata(DATA_PATH)

needed_columns = {"model", "rule", "y_timing_max", "piq_timing_max"}
needed_columns.update(outcome for outcome, label in OUTCOMES)
missing_columns = sorted(needed_columns - set(raw.columns))
if missing_columns:
    raise ValueError(f"MMB_reg_format.dta is missing required columns: {missing_columns}")

# Step 3: apply the paper regression sample before fitting any outcome equation.
sample = raw.loc[
    (raw["y_timing_max"] < time_limit) & (raw["piq_timing_max"] < time_limit)
].copy()
sample = sample.dropna(subset=["model", "rule"])
sample["model"] = sample["model"].astype(str)
sample["rule"] = sample["rule"].astype(str)

if sample.empty:
    raise ValueError("The filtered paper regression sample has zero rows.")

duplicates = int(sample.duplicated(["model", "rule"]).sum())
if duplicates:
    raise ValueError(f"Found {duplicates} duplicate model-rule rows after filtering.")

present_rules = set(sample["rule"].dropna().unique())
missing_rules = sorted(set(EXPECTED_RULES) - present_rules)
if missing_rules:
    raise ValueError(f"The filtered sample is missing expected policy rules: {missing_rules}")

# Step 4: estimate rule-only, model-only, and saturated model-rule fixed-effect fits.
rows = []
for outcome, outcome_label in OUTCOMES:
    outcome_sample = sample[["model", "rule", outcome]].dropna().copy()
    if outcome_sample.empty:
        raise ValueError(f"No usable observations remain for outcome {outcome}.")

    rule_only = smf.ols(f"{outcome} ~ C(rule)", data=outcome_sample).fit()
    model_only = smf.ols(f"{outcome} ~ C(model)", data=outcome_sample).fit()
    rule_plus_model = smf.ols(f"{outcome} ~ C(rule) + C(model)", data=outcome_sample).fit()

    r2_rule_only = float(rule_only.rsquared)
    r2_model_only = float(model_only.rsquared)
    r2_rule_plus_model = float(rule_plus_model.rsquared)
    incremental_rule_given_model = r2_rule_plus_model - r2_model_only
    incremental_model_given_rule = r2_rule_plus_model - r2_rule_only

    if abs(incremental_rule_given_model) <= RATIO_DENOMINATOR_MIN:
        model_to_rule_increment_ratio = np.nan
    else:
        model_to_rule_increment_ratio = incremental_model_given_rule / incremental_rule_given_model

    rows.append(
        {
            "outcome": outcome,
            "outcome_label": outcome_label,
            "n_obs": int(rule_plus_model.nobs),
            "r2_rule_only": r2_rule_only,
            "r2_model_only": r2_model_only,
            "r2_rule_plus_model": r2_rule_plus_model,
            "incremental_rule_given_model": incremental_rule_given_model,
            "incremental_model_given_rule": incremental_model_given_rule,
            "model_to_rule_increment_ratio": model_to_rule_increment_ratio,
        }
    )

results = pd.DataFrame(rows)
results.to_csv(CSV_PATH, index=False)

# Step 5: write a compact LaTeX table with paper-facing outcome labels.
def tex_number(value, digits=3):
    if pd.isna(value) or not np.isfinite(value):
        return "--"
    text = f"{value:.{digits}f}"
    if text == "-0.000":
        text = "0.000"
    return text


latex_lines = [
    "\\begin{tabular}{lrrrrrr}",
    "\\hline",
    "Outcome & N & Rule-only $R^2$ & Model-only $R^2$ & Both $R^2$ & Add rule & Add model \\\\",
    "\\hline",
]
for row in results.to_dict("records"):
    latex_lines.append(
        f"{row['outcome_label']} & "
        f"{row['n_obs']} & "
        f"{tex_number(row['r2_rule_only'])} & "
        f"{tex_number(row['r2_model_only'])} & "
        f"{tex_number(row['r2_rule_plus_model'])} & "
        f"{tex_number(row['incremental_rule_given_model'])} & "
        f"{tex_number(row['incremental_model_given_rule'])} \\\\"
    )
latex_lines.extend(
    [
        "\\hline",
        "\\end{tabular}",
        "",
        "% Add rule is the incremental R-squared from adding rule fixed effects after model fixed effects.",
        "% Add model is the incremental R-squared from adding model fixed effects after rule fixed effects.",
    ]
)
TEX_PATH.write_text("\n".join(latex_lines), encoding="utf-8")

# Step 6: build the figure from the CSV so the plot and table use the same data.
plot_data = pd.read_csv(CSV_PATH)
plot_data["outcome_label"] = pd.Categorical(
    plot_data["outcome_label"],
    categories=[label for outcome, label in OUTCOMES],
    ordered=True,
)
plot_data = plot_data.sort_values("outcome_label")

fig, ax = plt.subplots(figsize=(7.2, 4.8))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

y_positions = np.arange(plot_data.shape[0])
bar_height = 0.34
model_values = plot_data["incremental_model_given_rule"].to_numpy(dtype=float)
rule_values = plot_data["incremental_rule_given_model"].to_numpy(dtype=float)
max_value = float(np.nanmax([np.nanmax(model_values), np.nanmax(rule_values)]))
x_limit = max(0.05, max_value * 1.18)

model_bars = ax.barh(
    y_positions - bar_height / 2,
    model_values,
    height=bar_height,
    color="#4C78A8",
    label="Add model FE after rule FE",
)
rule_bars = ax.barh(
    y_positions + bar_height / 2,
    rule_values,
    height=bar_height,
    color="#D8A657",
    label="Add rule FE after model FE",
)

for bars in [model_bars, rule_bars]:
    for bar in bars:
        width = bar.get_width()
        if np.isfinite(width) and width >= x_limit * 0.035:
            ax.text(
                width + x_limit * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.3f}",
                va="center",
                ha="left",
                fontsize=8,
                color="#222222",
            )

ax.set_yticks(y_positions)
ax.set_yticklabels([FIGURE_LABELS[label] for label in plot_data["outcome_label"]])
ax.invert_yaxis()
ax.set_xlim(0, x_limit)
ax.set_xlabel("Incremental $R^2$")
ax.set_title("Model differences explain most transmission heterogeneity", loc="left", pad=24)
ax.text(
    0.0,
    1.02,
    "Bars show incremental R² from adding fixed effects to the alternative fixed-effect baseline.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=9,
    color="#444444",
)
ax.xaxis.grid(True, color="#E6E6E6", linewidth=0.8)
ax.set_axisbelow(True)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
ax.legend(frameon=False, loc="upper right")

fig.tight_layout()
fig.savefig(PDF_PATH, bbox_inches="tight")
fig.savefig(PNG_PATH, dpi=300, bbox_inches="tight")
plt.close(fig)

description_text = """Figure: model_vs_rule_variance_decomposition.pdf and .png

What it shows:
  Horizontal grouped bars compare incremental R-squared values from adding
  model fixed effects after rule fixed effects versus adding rule fixed effects
  after model fixed effects.

Axes:
  Y-axis lists the five monetary-transmission outcomes.
  X-axis reports incremental R-squared.

Data source:
  ../input/MMB_reg_format.dta, filtered to the paper regression sample.

Key takeaway:
  Model fixed effects add substantially more explanatory power than rule fixed
  effects for the slope, timing, and sacrifice-ratio outcomes.
"""
DESCRIPTION_PATH.write_text(description_text, encoding="utf-8")

# Step 7: write a short interpretation with the generated numbers.
model_min = results.loc[results["r2_model_only"].idxmin()]
model_max = results.loc[results["r2_model_only"].idxmax()]
rule_min = results.loc[results["r2_rule_only"].idxmin()]
rule_max = results.loc[results["r2_rule_only"].idxmax()]
avg_model_increment = results["incremental_model_given_rule"].mean()
avg_rule_increment = results["incremental_rule_given_model"].mean()

findings_text = f"""# Findings Note

Cross-model differences account for far more variation in monetary-transmission
outcomes than policy-rule differences. In the paper regression sample, model
fixed effects alone explain {model_min['r2_model_only']:.3f} to
{model_max['r2_model_only']:.3f} of outcome variation, from
{model_min['outcome_label']} to {model_max['outcome_label']}. Rule fixed
effects alone explain {rule_min['r2_rule_only']:.3f} to
{rule_max['r2_rule_only']:.3f}, from {rule_min['outcome_label']} to
{rule_max['outcome_label']}. Adding model fixed effects after rule fixed
effects raises R-squared by {avg_model_increment:.3f} on average, compared with
{avg_rule_increment:.3f} for adding rule fixed effects after model fixed
effects. This does not identify which model features matter, but it establishes
that disagreement is primarily a model-architecture phenomenon rather than
merely a policy-rule phenomenon.
"""
FINDINGS_PATH.write_text(findings_text, encoding="utf-8")

# Step 8: list every produced output, including this manifest.
manifest_rows = [
    {
        "file": CSV_PATH.name,
        "description": "Outcome-level R-squared decomposition for rule and model fixed effects.",
    },
    {
        "file": TEX_PATH.name,
        "description": "Compact LaTeX version of the variance-decomposition table.",
    },
    {
        "file": PDF_PATH.name,
        "description": "PDF figure comparing incremental R-squared values.",
    },
    {
        "file": PNG_PATH.name,
        "description": "PNG figure comparing incremental R-squared values.",
    },
    {
        "file": DESCRIPTION_PATH.name,
        "description": "Plain-text metadata for the figure outputs.",
    },
    {
        "file": FINDINGS_PATH.name,
        "description": "Paper-language interpretation of the generated estimates.",
    },
    {
        "file": MANIFEST_PATH.name,
        "description": "Manifest listing every produced output file.",
    },
]
pd.DataFrame(manifest_rows).to_csv(MANIFEST_PATH, index=False)
