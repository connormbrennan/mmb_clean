"""
Purpose:
    Inventory legacy artifacts that are not promoted into the production task graph.

Inputs:
    ../../../legacy/mmb_upgraded/

Outputs:
    ../output/legacy_artifact_inventory.txt

Run:
    make from tasks/archive_legacy_artifacts/code/
"""

from pathlib import Path
from collections import Counter

import pandas as pd


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
repo_dir = task_dir.parents[1]
legacy_dir = repo_dir / "legacy" / "mmb_upgraded"
output_dir = task_dir / "output"
output_dir.mkdir(parents=True, exist_ok=True)

rows = []
extension_counts = Counter()
extension_sizes = Counter()

for path in sorted(legacy_dir.rglob("*")):
    if ".git" in path.parts or not path.is_file():
        continue
    relative = path.relative_to(repo_dir)
    extension = path.suffix.lower() if path.suffix else "[no extension]"
    size_bytes = path.stat().st_size
    extension_counts[extension] += 1
    extension_sizes[extension] += size_bytes

    first_part = path.relative_to(legacy_dir).parts[0]
    if path.name == "Model_Characteristics_corrections.xlsx":
        disposition = "promoted as main model-characteristics input through tasks/import_mmb_legacy_data"
    elif path.name.startswith("Model_Characteristics"):
        disposition = "legacy model-characteristics reference; not the main feed-in input"
    elif str(relative).startswith("legacy/mmb_upgraded/data/raw"):
        disposition = "promoted as source input through tasks/import_mmb_legacy_data"
    elif str(relative).startswith("legacy/mmb_upgraded/data/derived"):
        disposition = "superseded by tasks/build_mmb_analysis_dataset outputs"
    elif str(relative).startswith("legacy/mmb_upgraded/output/cloud_graphs"):
        disposition = "superseded by tasks/generate_mmb_cloud_graphs outputs"
    elif first_part in ["documentation", "drafts", "outlier_emails"]:
        disposition = "reference archive; keep in legacy until cited by a specific task"
    elif first_part in ["code", "work_code_legacy", "misc", "calc-sacrifice-ratio"]:
        disposition = "legacy code archive; promote only when needed by a named task"
    elif first_part in ["output", "bob", "cloud_graphs", "outlier_charts"]:
        disposition = "legacy generated output; preserved exactly by tasks/reproduce_legacy_outputs"
    else:
        disposition = "legacy archive; inspect before promoting"

    rows.append(
        {
            "path": str(relative),
            "extension": extension,
            "size_bytes": size_bytes,
            "disposition": disposition,
        }
    )

inventory = pd.DataFrame(rows)
summary_rows = []
for extension, count in extension_counts.most_common():
    summary_rows.append(
        {
            "extension": extension,
            "files": count,
            "megabytes": round(extension_sizes[extension] / 1024 / 1024, 2),
        }
    )
summary = pd.DataFrame(summary_rows)

with open(output_dir / "legacy_artifact_inventory.txt", "w", encoding="utf-8") as f:
    f.write("Legacy artifact inventory\n")
    f.write("=========================\n\n")
    f.write(f"Legacy root: {legacy_dir.relative_to(repo_dir)}\n")
    f.write(f"Files inventoried outside nested .git folders: {len(inventory)}\n\n")
    f.write("Summary by extension\n")
    f.write("--------------------\n")
    f.write(summary.to_string(index=False))
    f.write("\n\n")
    f.write("Disposition rules\n")
    f.write("-----------------\n")
    f.write("Core raw data enter through the source-data import task.\n")
    f.write("Derived datasets and cloud graphs are rebuilt in production tasks.\n")
    f.write("Exact generated legacy artifacts are preserved by tasks/reproduce_legacy_outputs for parity checks and reference.\n")
    f.write("Old drafts, exploratory notebooks, and one-off code remain archived until a named task needs them.\n\n")
    f.write("Full inventory\n")
    f.write("--------------\n")
    f.write(inventory.to_string(index=False))
    f.write("\n")

print(f"Wrote legacy inventory for {len(inventory)} files.")
