#!/usr/bin/env python3
"""
Purpose:
  Measure whether models keep similar cross-model rankings across monetary
  policy rules.

Inputs:
  ../input/MMB_reg_format.dta
  ../../../../config/params.yaml

Outputs:
  ../output/cross_rule_rank_stability.csv
  ../output/cross_rule_rank_stability.tex
  ../output/cross_rule_rank_stability_heatmap.pdf
  ../output/cross_rule_rank_stability_heatmap.png
  ../output/cross_rule_rank_stability_heatmap_description.txt
  ../output/findings_note.md
  ../output/manifest.csv

Run:
  From this code directory, run: make all
"""

from pathlib import Path
import os
import shutil
import tempfile
import warnings

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mmb_matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ConstantInputWarning, pearsonr, spearmanr
import yaml


TASK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = Path(__file__).resolve().parents[4]
INPUT_DIR = TASK_DIR / "input"
OUTPUT_DIR = TASK_DIR / "output"
CONFIG_PATH = REPO_DIR / "config" / "params.yaml"

DATA_PATH = INPUT_DIR / "MMB_reg_format.dta"

EXPECTED_RULES = ["Taylor", "Inertial_Taylor", "Growth"]
RULE_PAIRS = [
    ("Taylor", "Inertial_Taylor", "Taylor vs Inertial Taylor"),
    ("Taylor", "Growth", "Taylor vs Growth"),
    ("Inertial_Taylor", "Growth", "Inertial Taylor vs Growth"),
]
OUTCOMES = [
    ("IScurve20", "y-slope"),
    ("infl_per_rr20", "pi-slope"),
    ("sacratio20", "sacrifice ratio"),
    ("y_timing_max", "y-timing"),
    ("piq_timing_max", "pi-timing"),
]
MIN_MATCHED_MODELS = 10

CSV_PATH = OUTPUT_DIR / "cross_rule_rank_stability.csv"
TEX_PATH = OUTPUT_DIR / "cross_rule_rank_stability.tex"
PDF_PATH = OUTPUT_DIR / "cross_rule_rank_stability_heatmap.pdf"
PNG_PATH = OUTPUT_DIR / "cross_rule_rank_stability_heatmap.png"
DESCRIPTION_PATH = OUTPUT_DIR / "cross_rule_rank_stability_heatmap_description.txt"
FINDINGS_PATH = OUTPUT_DIR / "findings_note.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Step 1: remove stale task-owned output files before writing the new run.
for path in OUTPUT_DIR.iterdir():
    if path.name == ".gitkeep":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

# Step 2: load the shared timing cutoff used to define the paper sample.
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

# Step 3: keep the same model-rule paper regression sample used in the tables.
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

# Step 4: compare each outcome's model ranking across rule pairs.
rows = []
for outcome, outcome_label in OUTCOMES:
    outcome_data = sample[["model", "rule", outcome]].dropna().copy()
    pivot = outcome_data.pivot(index="model", columns="rule", values=outcome)

    for rule_a, rule_b, pair_label in RULE_PAIRS:
        matched = pivot[[rule_a, rule_b]].dropna()
        n_models = int(matched.shape[0])

        spearman_rho = np.nan
        spearman_p = np.nan
        pearson_r = np.nan
        pearson_p = np.nan
        status = "estimated"

        if n_models < MIN_MATCHED_MODELS:
            status = "skipped_fewer_than_10_models"
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConstantInputWarning)
                spearman_rho, spearman_p = spearmanr(matched[rule_a], matched[rule_b])
                pearson_r, pearson_p = pearsonr(matched[rule_a], matched[rule_b])

        rows.append(
            {
                "outcome": outcome,
                "outcome_label": outcome_label,
                "rule_a": rule_a,
                "rule_b": rule_b,
                "rule_pair_label": pair_label,
                "n_models": n_models,
                "spearman_rho": float(spearman_rho) if np.isfinite(spearman_rho) else np.nan,
                "spearman_p": float(spearman_p) if np.isfinite(spearman_p) else np.nan,
                "pearson_r": float(pearson_r) if np.isfinite(pearson_r) else np.nan,
                "pearson_p": float(pearson_p) if np.isfinite(pearson_p) else np.nan,
                "status": status,
            }
        )

results = pd.DataFrame(rows)
results.to_csv(CSV_PATH, index=False)

# Step 5: write a compact LaTeX table focused on Spearman rank correlations.
def rho_cell(row):
    if row.empty:
        return "--"
    row = row.iloc[0]
    if row["status"] != "estimated" or pd.isna(row["spearman_rho"]):
        return f"-- ({int(row['n_models'])})"
    return f"{row['spearman_rho']:.2f} ({int(row['n_models'])})"


latex_lines = [
    "\\begin{tabular}{lccc}",
    "\\hline",
    "Outcome & Taylor vs Inertial Taylor & Taylor vs Growth & Inertial Taylor vs Growth \\\\",
    "\\hline",
]
for outcome, outcome_label in OUTCOMES:
    outcome_rows = results.loc[results["outcome"] == outcome]
    cells = []
    for rule_a, rule_b, pair_label in RULE_PAIRS:
        pair_row = outcome_rows.loc[
            (outcome_rows["rule_a"] == rule_a) & (outcome_rows["rule_b"] == rule_b)
        ]
        cells.append(rho_cell(pair_row))
    latex_lines.append(f"{outcome_label} & {cells[0]} & {cells[1]} & {cells[2]} \\\\")
latex_lines.extend(
    [
        "\\hline",
        "\\end{tabular}",
        "",
        "% Cells report Spearman rank correlations, with the matched model count in parentheses.",
    ]
)
TEX_PATH.write_text("\n".join(latex_lines), encoding="utf-8")

# Step 6: build the heatmap from the CSV output, not from in-memory results.
plot_data = pd.read_csv(CSV_PATH)
heatmap = plot_data.pivot(index="outcome_label", columns="rule_pair_label", values="spearman_rho")
heatmap = heatmap.reindex(
    index=[label for outcome, label in OUTCOMES],
    columns=[pair_label for rule_a, rule_b, pair_label in RULE_PAIRS],
)
values = heatmap.to_numpy(dtype=float)
finite_values = values[np.isfinite(values)]
if finite_values.size == 0:
    raise ValueError("No finite Spearman correlations were available for the heatmap.")

if finite_values.min() >= 0:
    vmin = 0.0
    vmax = 1.0
    cmap = plt.get_cmap("Blues").copy()
    scale_note = "The color scale runs from 0 to 1 because all reported correlations are nonnegative."
else:
    vmin = -1.0
    vmax = 1.0
    cmap = plt.get_cmap("RdBu").copy()
    scale_note = "The color scale runs from -1 to 1 because at least one reported correlation is negative."
cmap.set_bad("#F2F2F2")

fig, ax = plt.subplots(figsize=(7.4, 4.6))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

image = ax.imshow(np.ma.masked_invalid(values), vmin=vmin, vmax=vmax, cmap=cmap, aspect="auto")
ax.set_title("Model rankings are largely stable across policy rules", loc="left", pad=28)
ax.text(
    0.0,
    1.03,
    "Cells report Spearman rank correlations across models for each pair of policy rules.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=9,
    color="#444444",
)
ax.set_xticks(np.arange(len(heatmap.columns)))
ax.set_xticklabels(["Taylor vs\nInertial Taylor", "Taylor vs\nGrowth", "Inertial Taylor\nvs Growth"])
ax.set_yticks(np.arange(len(heatmap.index)))
ax.set_yticklabels(heatmap.index)
ax.tick_params(axis="both", length=0)

for row_index in range(values.shape[0]):
    for col_index in range(values.shape[1]):
        value = values[row_index, col_index]
        if np.isfinite(value):
            text_color = "white" if value > 0.62 else "#222222"
            text = f"{value:.2f}"
        else:
            text_color = "#555555"
            text = "--"
        ax.text(col_index, row_index, text, ha="center", va="center", color=text_color, fontsize=9)

for spine in ax.spines.values():
    spine.set_visible(False)

colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
colorbar.set_label("Spearman rho")
colorbar.outline.set_visible(False)

fig.tight_layout()
fig.savefig(PDF_PATH, bbox_inches="tight")
fig.savefig(PNG_PATH, dpi=300, bbox_inches="tight")
plt.close(fig)

description_text = f"""Figure: cross_rule_rank_stability_heatmap.pdf and .png

What it shows:
  Heatmap cells report Spearman rank correlations across models for each pair
  of policy rules and each monetary-transmission outcome.

Axes:
  Rows list the five monetary-transmission outcomes.
  Columns list policy-rule pairs.

Data source:
  ../input/MMB_reg_format.dta, filtered to the paper regression sample.

Color scale:
  {scale_note}

Key takeaway:
  Most model rankings remain similar across policy rules, with inflation-slope
  rankings less stable when the Growth rule is involved.
"""
DESCRIPTION_PATH.write_text(description_text, encoding="utf-8")

# Step 7: write a paper-language interpretation from the generated estimates.
estimated = results.loc[results["status"] == "estimated"].copy()
rho_min = estimated["spearman_rho"].min()
rho_max = estimated["spearman_rho"].max()
sacrifice = estimated.loc[estimated["outcome_label"] == "sacrifice ratio", "spearman_rho"]
timing = estimated.loc[estimated["outcome_label"].isin(["y-timing", "pi-timing"]), "spearman_rho"]
pi_growth = estimated.loc[
    (estimated["outcome_label"] == "pi-slope") & (estimated["rule_b"] == "Growth"),
    "spearman_rho",
]
pi_taylor_inertial = estimated.loc[
    (estimated["outcome_label"] == "pi-slope")
    & (estimated["rule_a"] == "Taylor")
    & (estimated["rule_b"] == "Inertial_Taylor"),
    "spearman_rho",
]

findings_text = f"""# Findings Note

Policy rules change the level and timing of model-implied responses, but they
generally do not reshuffle the cross-model ranking. Across the generated
rule-pair comparisons, Spearman rank correlations range from {rho_min:.2f} to
{rho_max:.2f}. Sacrifice-ratio rankings are especially stable, ranging from
{sacrifice.min():.2f} to {sacrifice.max():.2f}, and timing rankings range from
{timing.min():.2f} to {timing.max():.2f}. Inflation-slope rankings are less
stable when the Growth rule is involved, with correlations from
{pi_growth.min():.2f} to {pi_growth.max():.2f}, compared with
{pi_taylor_inertial.iloc[0]:.2f} for Taylor versus inertial Taylor. This
supports treating cross-model disagreement as persistent model-level
heterogeneity rather than an artifact of a single policy-rule choice.
"""
FINDINGS_PATH.write_text(findings_text, encoding="utf-8")

# Step 8: list every produced output, including this manifest.
manifest_rows = [
    {
        "file": CSV_PATH.name,
        "description": "Outcome-by-rule-pair rank and level correlations across models.",
    },
    {
        "file": TEX_PATH.name,
        "description": "Compact LaTeX table of Spearman rank correlations and matched model counts.",
    },
    {
        "file": PDF_PATH.name,
        "description": "PDF heatmap of Spearman rank correlations across policy rules.",
    },
    {
        "file": PNG_PATH.name,
        "description": "PNG heatmap of Spearman rank correlations across policy rules.",
    },
    {
        "file": DESCRIPTION_PATH.name,
        "description": "Plain-text metadata for the heatmap outputs.",
    },
    {
        "file": FINDINGS_PATH.name,
        "description": "Paper-language interpretation of the generated rank-stability estimates.",
    },
    {
        "file": MANIFEST_PATH.name,
        "description": "Manifest listing every produced output file.",
    },
]
pd.DataFrame(manifest_rows).to_csv(MANIFEST_PATH, index=False)
