#!/usr/bin/env python3
"""
Purpose:
  Make Tables 3-5 summary statistics and timing histograms for the MMB analysis dataset.

Inputs:
  ../input/MMB_reg_format.dta

Outputs:
  ../output/summarystats/table3_summary_stats.tex
  ../output/summarystats/table3_summary_stats.csv
  ../output/summarystats/table4_elasticity_stats.tex
  ../output/summarystats/table4_elasticity_stats.csv
  ../output/summarystats/table5_timing_stats.tex
  ../output/summarystats/table5_timing_stats.csv
  ../output/summarystats/
  ../output/manifest.csv

Run:
  make
"""

from pathlib import Path
import os
import shutil

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml


task_dir = Path(__file__).resolve().parents[1]
repo_dir = Path(__file__).resolve().parents[4]
input_dir = task_dir / "input"
output_dir = task_dir / "output"
stats_dir = output_dir / "summarystats"

if stats_dir.exists():
    shutil.rmtree(stats_dir)
stats_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_stata(input_dir / "MMB_reg_format.dta")

with open(repo_dir / "config" / "params.yaml", "r", encoding="utf-8") as f:
    summary_time_limit = yaml.safe_load(f)["mmb"]["time_limit"]

# Use one timing-outlier rule for every summary artifact so tables, CSVs,
# and histograms describe the same main sample.
valid_summary_sample = (
    (pd.to_numeric(df["y_timing_max"], errors="coerce") < summary_time_limit)
    & (pd.to_numeric(df["piq_timing_max"], errors="coerce") < summary_time_limit)
)
table_df = df.loc[valid_summary_sample].copy()

table_variables = [
    ("IScurve20", "\\textit{y-slope}"),
    ("infl_per_rr20", "\\textit{$\\pi$-slope}"),
    ("sacratio20", "\\textit{sacratio}"),
    ("y_timing_max", "\\textit{y-timing}"),
    ("piq_timing_max", "\\textit{$\\pi$-timing}"),
]

table_groups = [
    ("Full sample", table_df),
    ("Calibrated models", table_df.loc[table_df["calibrated"] == 1].copy()),
    ("Estimated models", table_df.loc[table_df["estimated"] == 1].copy()),
]

table_stats = [
    ("Mean", "mean"),
    ("Median", "median"),
    ("Std deviation", "sd"),
    ("Skewness", "skew"),
    ("N", "n"),
]


def population_skew(x):
    # Match the manuscript tables: third central moment divided by the population standard deviation cubed.
    if x.shape[0] == 0:
        return pd.NA
    std = x.std(ddof=0)
    if std == 0:
        return 0.0
    return ((x - x.mean()) ** 3).mean() / (std ** 3)


summary_rows = []
for group_name, group_df in table_groups:
    for var, column_label in table_variables:
        x = pd.to_numeric(group_df[var], errors="coerce").dropna()
        summary_rows.append(
            {
                "group": group_name,
                "variable": var,
                "column_label": column_label,
                "mean": x.mean(),
                "median": x.median(),
                "sd": x.std(),
                "skew": population_skew(x),
                "n": int(x.shape[0]),
            }
        )

table_summary = pd.DataFrame(summary_rows)
table_summary.to_csv(stats_dir / "table3_summary_stats.csv", index=False)


def latex_number(value):
    text = f"{value:.2f}"
    if text == "-0.00":
        text = "0.00"
    if value < 0:
        return f"${text}$"
    return text


latex_lines = [
    "\\begin{table}[H]",
    "\\centering",
    "\\caption{ ",
    "\\\\",
    "\\underline{Summary statistics for the constructed data}}",
    "\\label{tab:summary_stats}",
    "\\small",
    "\\begin{tabular}{l c c c c c}",
    "\\toprule",
]

for group_index, (group_name, group_df) in enumerate(table_groups):
    if group_index > 0:
        latex_lines.append("\\midrule")
    latex_lines.append(f"\\textbf{{{group_name}}} & & & & & \\\\")
    latex_lines.append(" & " + " & ".join(label for _, label in table_variables) + " \\\\")
    latex_lines.append("\\midrule")

    group_summary = table_summary.loc[table_summary["group"] == group_name].set_index("variable")
    for row_label, stat_name in table_stats:
        cells = []
        for var, _ in table_variables:
            value = group_summary.loc[var, stat_name]
            if stat_name == "n":
                cells.append(str(int(value)))
            else:
                cells.append(latex_number(float(value)))
        latex_lines.append(f"{row_label} & " + " & ".join(cells) + " \\\\")

latex_lines.extend(
    [
        "\\bottomrule",
        "\\multicolumn{6}{p{13cm}}{\\footnotesize Notes: See Table~\\ref{tab:outcome_vars} for definitions of variables. Source: authors' calculations based on simulations of MMB models.}",
        "\\end{tabular}",
        "\\end{table}",
    ]
)

table3_latex = "\n".join(latex_lines) + "\n"
(stats_dir / "table3_summary_stats.tex").write_text(table3_latex, encoding="utf-8")

elasticity_variables = [
    ("IScurve20", "\\textit{y-slope}"),
    ("infl_per_rr20", "\\textit{$\\pi$-slope}"),
    ("sacratio20", "\\textit{sacratio}"),
]

elasticity_rules = [
    ("Taylor", "\\textit{Taylor}"),
    ("Inertial_Taylor", "\\textit{Inertial}"),
    ("Growth", "\\textit{Growth}"),
]

elasticity_rows = []
for group_name, group_df in table_groups:
    for var, variable_label in elasticity_variables:
        for rule_name, rule_label in elasticity_rules:
            x = pd.to_numeric(group_df.loc[group_df["rule"] == rule_name, var], errors="coerce").dropna()
            elasticity_rows.append(
                {
                    "group": group_name,
                    "variable": var,
                    "variable_label": variable_label,
                    "rule": rule_name,
                    "rule_label": rule_label,
                    "mean": x.mean(),
                    "median": x.median(),
                    "sd": x.std(),
                    "skew": population_skew(x),
                    "n": int(x.shape[0]),
                }
            )

elasticity_summary = pd.DataFrame(elasticity_rows)
elasticity_summary.to_csv(stats_dir / "table4_elasticity_stats.csv", index=False)

latex_lines = [
    "\\begin{table}[H]",
    "\\centering",
    "\\caption{ \\\\  \\underline{Summary statistics for macroeconomic elasticity variables}}",
    "\\label{tab:elasticity_stats}",
    "",
    "\\scriptsize",
    "\\begin{tabular}{l ccc ccc ccc}",
    "\\toprule",
    "& \\multicolumn{3}{c}{\\textit{y-slope}} & \\multicolumn{3}{c}{\\textit{$\\pi$-slope}} & \\multicolumn{3}{c}{\\textit{sacratio}} \\\\",
    "\\textit{Rules $\\to$} & \\textit{Taylor} & \\textit{Inertial} & \\textit{Growth} & \\textit{Taylor} & \\textit{Inertial} & \\textit{Growth} & \\textit{Taylor} & \\textit{Inertial} & \\textit{Growth} \\\\",
    "\\midrule",
]

for group_index, (group_name, group_df) in enumerate(table_groups):
    if group_index > 0:
        latex_lines.append("\\midrule")
    latex_lines.append(f"\\multicolumn{{10}}{{l}}{{\\textbf{{{group_name}}}}} \\\\")
    group_summary = elasticity_summary.loc[elasticity_summary["group"] == group_name]
    for row_label, stat_name in table_stats:
        cells = []
        for var, _ in elasticity_variables:
            for rule_name, _ in elasticity_rules:
                value = group_summary.loc[
                    (group_summary["variable"] == var) & (group_summary["rule"] == rule_name),
                    stat_name,
                ].iloc[0]
                if stat_name == "n":
                    cells.append(str(int(value)))
                else:
                    cells.append(latex_number(float(value)))
        latex_lines.append(f"{row_label.replace('Std deviation', 'Std Deviation')} & " + " & ".join(cells) + " \\\\")

latex_lines.extend(
    [
        "\\bottomrule",
        "\\multicolumn{10}{p{15cm}}{\\footnotesize Notes: See Table~\\ref{tab:outcome_vars} for variable definitions. Source: authors' calculations based on simulations of MMB models.}",
        "\\end{tabular}",
        "\\end{table}",
    ]
)

table4_latex = "\n".join(latex_lines) + "\n"
(stats_dir / "table4_elasticity_stats.tex").write_text(table4_latex, encoding="utf-8")

timing_table_variables = [
    ("y_timing_max", "\\textit{y-timing}"),
    ("piq_timing_max", "\\textit{$\\pi$-timing}"),
]

timing_rows = []
for group_name, group_df in table_groups:
    for var, variable_label in timing_table_variables:
        for rule_name, rule_label in elasticity_rules:
            x = pd.to_numeric(group_df.loc[group_df["rule"] == rule_name, var], errors="coerce").dropna()
            timing_rows.append(
                {
                    "group": group_name,
                    "variable": var,
                    "variable_label": variable_label,
                    "rule": rule_name,
                    "rule_label": rule_label,
                    "mean": x.mean(),
                    "median": x.median(),
                    "sd": x.std(),
                    "skew": population_skew(x),
                    "n": int(x.shape[0]),
                }
            )

timing_summary = pd.DataFrame(timing_rows)
timing_summary.to_csv(stats_dir / "table5_timing_stats.csv", index=False)

latex_lines = [
    "\\begin{table}[H]",
    "\\centering",
    "\\caption{ \\\\ \\underline{Summary statistics for timing of peak outcome variables}}",
    "\\label{tab:timing_stats}",
    "\\scriptsize",
    "\\begin{tabular}{l ccc ccc}",
    "\\toprule",
    "& \\multicolumn{3}{c}{\\textit{y-timing}} & \\multicolumn{3}{c}{\\textit{$\\pi$-timing}} \\\\",
    "\\textit{Policy rules $\\to$} & \\textit{Taylor} & \\textit{Inertial} & \\textit{Growth} & \\textit{Taylor} & \\textit{Inertial} & \\textit{Growth} \\\\",
    "\\midrule",
]

for group_index, (group_name, group_df) in enumerate(table_groups):
    if group_index > 0:
        latex_lines.append("\\midrule")
    latex_lines.append(f"\\multicolumn{{7}}{{l}}{{\\textbf{{{group_name}}}}} \\\\")
    group_summary = timing_summary.loc[timing_summary["group"] == group_name]
    for row_label, stat_name in table_stats:
        cells = []
        for var, _ in timing_table_variables:
            for rule_name, _ in elasticity_rules:
                value = group_summary.loc[
                    (group_summary["variable"] == var) & (group_summary["rule"] == rule_name),
                    stat_name,
                ].iloc[0]
                if stat_name == "n":
                    cells.append(str(int(value)))
                else:
                    cells.append(latex_number(float(value)))
        latex_lines.append(f"{row_label.replace('Std deviation', 'Std deviation')} & " + " & ".join(cells) + " \\\\")

latex_lines.extend(
    [
        "\\bottomrule",
        "\\multicolumn{7}{p{13cm}}{\\footnotesize Notes: See Table~\\ref{tab:outcome_vars} for definitions of variables. Source: authors' calculations based on simulations of MMB models.}",
        "\\end{tabular}",
        "\\end{table}",
    ]
)

table5_latex = "\n".join(latex_lines) + "\n"
(stats_dir / "table5_timing_stats.tex").write_text(table5_latex, encoding="utf-8")

outcomevars = [
    "IScurve20",
    "infl_per_rr20",
    "sacratio20",
    "Billsacrat20",
    "IScurve40",
    "infl_per_rr40",
    "sacratio40",
    "Billsacrat40",
    "IScurve60",
    "infl_per_rr60",
    "sacratio60",
    "Billsacrat60",
]

timingvars = [
    "piq_timing_max",
    "y_timing_max",
    "rrate_timing_min",
    "irate_timing_min",
]

summary_source = table_df

rule_groups = [
    ("all", pd.Series(True, index=summary_source.index)),
    ("Taylor", summary_source["rule"] == "Taylor"),
    ("Inertial_Taylor", summary_source["rule"] == "Inertial_Taylor"),
    ("Growth", summary_source["rule"] == "Growth"),
]

summary_rows = []
for var in outcomevars:
    if var not in summary_source.columns:
        continue
    for group_name, keep in rule_groups:
        x = pd.to_numeric(summary_source.loc[keep, var], errors="coerce").dropna()
        summary_rows.append(
            {
                "variable": var,
                "group": group_name,
                "mean": x.mean(),
                "median": x.median(),
                "sd": x.std(),
                "skew": population_skew(x),
                "n": int(x.shape[0]),
            }
        )

summary = pd.DataFrame(summary_rows)
summary.to_csv(stats_dir / "outcome_summary_stats_by_rule.csv", index=False)

with open(stats_dir / "texresults_outcomevars_stats_output.txt", "w", encoding="utf-8") as f:
    f.write(table3_latex)

manifest_rows = [
    {
        "file": "summarystats/table3_summary_stats.tex",
        "kind": "table",
        "description": "LaTeX Table 3 summary statistics for the constructed data.",
    },
    {
        "file": "summarystats/table3_summary_stats.csv",
        "kind": "table",
        "description": "Long-form source values for the LaTeX Table 3 summary statistics.",
    },
    {
        "file": "summarystats/outcome_summary_stats_by_rule.csv",
        "kind": "table",
        "description": "Additional main-sample summary statistics for outcome variables by policy rule.",
    },
    {
        "file": "summarystats/table4_elasticity_stats.tex",
        "kind": "table",
        "description": "LaTeX Table 4 summary statistics for macroeconomic elasticity variables.",
    },
    {
        "file": "summarystats/table4_elasticity_stats.csv",
        "kind": "table",
        "description": "Long-form source values for the LaTeX Table 4 elasticity statistics.",
    },
    {
        "file": "summarystats/table5_timing_stats.tex",
        "kind": "table",
        "description": "LaTeX Table 5 summary statistics for timing of peak outcome variables.",
    },
    {
        "file": "summarystats/table5_timing_stats.csv",
        "kind": "table",
        "description": "Long-form source values for the LaTeX Table 5 timing statistics.",
    },
    {
        "file": "summarystats/texresults_outcomevars_stats_output.txt",
        "kind": "table",
        "description": "Backward-compatible copy of the LaTeX Table 3 summary statistics.",
    },
]

for var in timingvars:
    if var not in df.columns:
        continue
    plot_df = df.loc[valid_summary_sample].copy()

    fig, ax = plt.subplots(figsize=(9, 5))
    for rule_name, color in [
        ("Inertial_Taylor", "#1f4e79"),
        ("Taylor", "#8c2d04"),
        ("Growth", "#2f6f3e"),
    ]:
        vals = pd.to_numeric(plot_df.loc[plot_df["rule"] == rule_name, var], errors="coerce").dropna()
        ax.hist(vals, bins=range(0, summary_time_limit + 2), alpha=0.55, label=rule_name.replace("_", " "), color=color)
    ax.set_title(f"{var} by policy rule")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Frequency")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = stats_dir / f"{var}_rules_timing_hist.pdf"
    fig.savefig(path)
    plt.close(fig)
    with open(stats_dir / f"{var}_rules_timing_hist_description.txt", "w", encoding="utf-8") as f:
        f.write(f"Figure: {path.name}\n")
        f.write(f"Shows the distribution of {var} by policy rule for the main summary-statistics sample, excluding observations with y_timing_max or piq_timing_max at or above {summary_time_limit} quarters.\n")
        f.write("Horizontal axis: quarter of timing event. Vertical axis: frequency.\n")
        f.write("Data source: ../input/MMB_reg_format.dta.\n")
    manifest_rows.append({"file": f"summarystats/{path.name}", "kind": "figure", "description": f"{var} by rule histogram."})

    fig, ax = plt.subplots(figsize=(9, 5))
    for col, label, color in [
        ("calibrated", "Calibrated", "#1f4e79"),
        ("estimated", "Estimated", "#2f6f3e"),
    ]:
        vals = pd.to_numeric(plot_df.loc[plot_df[col] == 1, var], errors="coerce").dropna()
        ax.hist(vals, bins=range(0, summary_time_limit + 2), alpha=0.55, label=label, color=color)
    ax.set_title(f"{var} by estimation type")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Frequency")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = stats_dir / f"{var}_types_timing_hist.pdf"
    fig.savefig(path)
    plt.close(fig)
    with open(stats_dir / f"{var}_types_timing_hist_description.txt", "w", encoding="utf-8") as f:
        f.write(f"Figure: {path.name}\n")
        f.write(f"Shows the distribution of {var} by calibrated versus estimated models for the main summary-statistics sample, excluding observations with y_timing_max or piq_timing_max at or above {summary_time_limit} quarters.\n")
        f.write("Horizontal axis: quarter of timing event. Vertical axis: frequency.\n")
        f.write("Data source: ../input/MMB_reg_format.dta.\n")
    manifest_rows.append({"file": f"summarystats/{path.name}", "kind": "figure", "description": f"{var} by estimation-type histogram."})

pd.DataFrame(manifest_rows).to_csv(output_dir / "manifest.csv", index=False)
print(f"Wrote summary statistics to {stats_dir}.")
