"""
Purpose:
    Generate the output cloud graph bundle from the constructed IRF panel.

Inputs:
    ../input/MMB_IRF_format_full.dta

Outputs:
    ../output/cloud_graphs/*.pdf
    ../output/cloud_graphs/*_description.txt
    ../output/manifest.csv

Run:
    make from tasks/graphs/output_cloud_graphs/code/
"""

from pathlib import Path
import os
import shutil

import pandas as pd


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
input_dir = task_dir / "input"
output_dir = task_dir / "output"
graph_dir = output_dir / "cloud_graphs"
if graph_dir.exists():
    shutil.rmtree(graph_dir)
graph_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".matplotlib"))

import matplotlib.pyplot as plt

df = pd.read_stata(input_dir / "MMB_IRF_format_full.dta", convert_categoricals=False)
df = df.sort_values(["model", "rule", "period"]).copy()

graph_options = {
    "median": "--r",
    "smets_wouters": "--b",
    "calibrated": "tab:orange",
    "estimated": "g",
    "other": "0.55",
    "thin_alpha": 0.29,
    "highlight_width": 4.5,
    "thin_width": 1.2,
}

variables = {
    "piq": ("Quarterly Inflation", (1.0, -0.25)),
    "y": ("Output", (1.75, -0.25)),
    "irate": ("Nominal Interest Rate", (1.0, -1.1)),
    "rrate": ("Real Interest Rate", (0.5, -1.5)),
}

rules = {
    "inertial_taylor": ("Inertial_Taylor", "Inertial Taylor Rule"),
    "taylor": ("Taylor", "Taylor Rule"),
    "growth": ("Growth", "Growth Rule"),
}

model_types = {
    "estimated": ("estimated", "Estimated Models"),
    "calibrated": ("calibrated", "Calibrated Models"),
}

plot_specs = []
for var_name in variables:
    plot_specs.append((f"{var_name}_all", var_name, "", "", ""))
    for rule_slug, (rule_value, rule_title) in rules.items():
        plot_specs.append((f"{var_name}_{rule_slug}", var_name, rule_value, "", rule_title))
    for type_slug, (type_column, type_title) in model_types.items():
        plot_specs.append((f"{var_name}_{type_slug}", var_name, "", type_column, type_title))
    for type_slug, (type_column, type_title) in model_types.items():
        for rule_slug, (rule_value, rule_title) in rules.items():
            plot_specs.append(
                (
                    f"{var_name}_{type_slug}_{rule_slug}",
                    var_name,
                    rule_value,
                    type_column,
                    f"{type_title} under {rule_title}",
                )
            )

manifest_rows = []
for file_base, var_name, rule_value, type_column, subtitle in plot_specs:
    title, bound = variables[var_name]

    keep = pd.Series(True, index=df.index)
    if rule_value:
        keep = keep & (df["rule"] == rule_value)
    if type_column:
        keep = keep & (df[type_column] == 1)

    # Keep a familiar reference line in every subset for visual comparison.
    sw_reference = (df["model"] == "US_SW07") & (df["rule"] == "Inertial_Taylor")
    plot_df = df.loc[keep | sw_reference].copy()

    median_source = df.loc[keep & (df["model"] != "VAR, 1963:Q1-2007:Q4")].copy()
    med = median_source.groupby("period")[var_name].median().rename("median")
    plot_df = plot_df.merge(med, on="period", how="left")

    fig, ax = plt.subplots(figsize=(14, 8.5))
    groups = list(plot_df.groupby(["model", "rule"], sort=True))
    median_drawn = False

    for _, group in groups:
        group = group.sort_values("period")
        if not median_drawn and group["median"].notna().any():
            ax.plot(
                group["period"],
                group["median"],
                graph_options["median"],
                linewidth=graph_options["highlight_width"],
                label="Median",
                zorder=len(groups) + 1,
            )
            median_drawn = True

        is_sw = (group["model"].iloc[0] == "US_SW07") and (group["rule"].iloc[0] == "Inertial_Taylor")
        if is_sw:
            ax.plot(
                group["period"],
                group[var_name],
                graph_options["smets_wouters"],
                linewidth=graph_options["highlight_width"],
                label="Smets & Wouters (2007)\nunder Inertial Taylor Rule",
                zorder=len(groups),
            )
        elif group["model"].iloc[0] == "VAR, 1963:Q1-2007:Q4":
            continue
        elif group["calibrated"].iloc[0] == 1:
            ax.plot(
                group["period"],
                group[var_name],
                color=graph_options["calibrated"],
                linewidth=graph_options["thin_width"],
                alpha=graph_options["thin_alpha"],
            )
        elif group["estimated"].iloc[0] == 1:
            ax.plot(
                group["period"],
                group[var_name],
                color=graph_options["estimated"],
                linewidth=graph_options["thin_width"],
                alpha=graph_options["thin_alpha"],
            )
        else:
            ax.plot(
                group["period"],
                group[var_name],
                color=graph_options["other"],
                linewidth=graph_options["thin_width"],
                alpha=graph_options["thin_alpha"],
            )

    subtitle_text = f"\n{subtitle}" if subtitle else ""
    ax.set_title(f"{title} after a 100bps Monetary Policy Shock{subtitle_text}", fontsize=22)
    ax.set_xlabel("Quarters", fontsize=16)
    ax.set_ylim(bound[1], bound[0])
    ax.margins(x=0)
    ax.grid(color="grey", linestyle="--", linewidth=0.5)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), frameon=False, ncol=2, fontsize=13)
    fig.tight_layout()

    figure_path = graph_dir / f"{file_base}.pdf"
    fig.savefig(figure_path, bbox_inches="tight")
    plt.close(fig)

    description_path = graph_dir / f"{file_base}_description.txt"
    with open(description_path, "w", encoding="utf-8") as f:
        f.write(f"Figure: {figure_path.name}\n")
        f.write(f"Shows: {title} impulse responses across MMB model-rule pairs.\n")
        f.write("Horizontal axis: quarters after a 100 basis point monetary policy shock.\n")
        f.write(f"Vertical axis: response of {var_name} in model units used by the MMB exports.\n")
        f.write("Data source: tasks/data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta.\n")
        if subtitle:
            f.write(f"Subset: {subtitle}.\n")
        else:
            f.write("Subset: all model-rule pairs.\n")
        f.write("Key takeaways: thin orange lines are calibrated models, thin green lines are estimated models, the red dashed line is the cross-model median, and the blue dashed line highlights Smets-Wouters (2007) under the inertial Taylor rule.\n")

    manifest_rows.append(
        {
            "figure": figure_path.name,
            "description": description_path.name,
            "variable": var_name,
            "rule_filter": rule_value or "all",
            "type_filter": type_column or "all",
            "n_model_rule_pairs": plot_df[["model", "rule"]].drop_duplicates().shape[0],
        }
    )

manifest = pd.DataFrame(manifest_rows)
manifest.to_csv(output_dir / "manifest.csv", index=False)
print(f"Wrote {len(manifest)} cloud graphs to {graph_dir}.")
