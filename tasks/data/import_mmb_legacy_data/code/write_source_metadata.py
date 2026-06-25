"""
Purpose:
    Write plain-text metadata for immutable legacy MMB inputs.

Inputs:
    ../output/model_characteristics.xlsx
    ../output/responses/*.csv
    ../output/sacratios_csv/*.csv
    ../output/sacratios_json/*.json
    ../output/bob_var_irfs.csv
    ../output/stationary_var_data.csv
    ../output/classifications.csv

Outputs:
    ../output/model_characteristics_codebook.txt
    ../output/source_inventory.txt

Run:
    make from tasks/data/import_mmb_legacy_data/code/
"""

from pathlib import Path
import json

import pandas as pd


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
output_dir = task_dir / "output"


# Summarize the binary model-characteristics workbook so it can be reviewed in text.
model_characteristics = pd.read_excel(output_dir / "model_characteristics.xlsx")
with open(output_dir / "model_characteristics_codebook.txt", "w", encoding="utf-8") as f:
    f.write("Model characteristics source workbook\n")
    f.write("====================================\n\n")
    f.write("Source: legacy/mmb_upgraded/data/raw/Model_Characteristics_corrections.xlsx\n")
    f.write(f"Rows: {model_characteristics.shape[0]}\n")
    f.write(f"Columns: {model_characteristics.shape[1]}\n\n")
    f.write("Columns and dtypes\n")
    f.write("------------------\n")
    for name, dtype in model_characteristics.dtypes.items():
        f.write(f"{name}: {dtype}\n")
    f.write("\nFirst 5 rows\n")
    f.write("------------\n")
    f.write(model_characteristics.head(5).to_string(index=False))
    f.write("\n\nFilters applied: none. This task only links the immutable source workbook.\n")


# Count linked source files and record a small amount of CSV/JSON provenance.
inventory_rows = []
source_groups = {
    "responses_csv": output_dir / "responses",
    "sacratios_csv": output_dir / "sacratios_csv",
    "sacratios_json": output_dir / "sacratios_json",
}

for group_name, folder in source_groups.items():
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        row = {
            "group": group_name,
            "file": path.name,
            "size_bytes": path.stat().st_size,
        }
        if path.suffix.lower() == ".csv":
            sample = pd.read_csv(path, nrows=5)
            row["rows_sampled"] = len(sample)
            row["columns"] = len(sample.columns)
            row["column_names"] = ", ".join(sample.columns.astype(str).tolist())
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            row["top_level_records"] = len(data) if isinstance(data, list) else "not_list"
            row["columns"] = ""
            row["column_names"] = ""
        inventory_rows.append(row)

single_files = [
    ("bob_var_irfs", output_dir / "bob_var_irfs.csv"),
    ("stationary_var_data", output_dir / "stationary_var_data.csv"),
    ("classifications", output_dir / "classifications.csv"),
]
for group_name, path in single_files:
    sample = pd.read_csv(path, nrows=5)
    inventory_rows.append(
        {
            "group": group_name,
            "file": path.name,
            "size_bytes": path.stat().st_size,
            "rows_sampled": len(sample),
            "columns": len(sample.columns),
            "column_names": ", ".join(sample.columns.astype(str).tolist()),
        }
    )

inventory = pd.DataFrame(inventory_rows)
with open(output_dir / "source_inventory.txt", "w", encoding="utf-8") as f:
    f.write("Imported legacy source inventory\n")
    f.write("================================\n\n")
    f.write("All file paths are task output links back to legacy/mmb_upgraded sources.\n")
    f.write("No source files were copied or transformed by this task.\n\n")
    f.write(inventory.to_string(index=False))
    f.write("\n")
