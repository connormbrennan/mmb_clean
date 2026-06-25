"""
Purpose:
    Copy leftover exact legacy generated archives into this task.

Inputs:
    ../../../../legacy/mmb_upgraded/bob/
    ../../../../legacy/mmb_upgraded/cloud_graphs/
    ../../../../legacy/mmb_upgraded/outlier_charts/

Outputs:
    ../output/bob/
    ../output/cloud_graphs/
    ../output/outlier_charts/
    ../output/generated_output_archives_manifest.txt
    Companion *_description.txt files for copied binary artifacts.

Run:
    make from tasks/legacy/generated_output_archives/code/
"""

from pathlib import Path
import hashlib
import shutil

import pandas as pd


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
repo_dir = task_dir.parents[2]
legacy_dir = repo_dir / "legacy" / "mmb_upgraded"
output_dir = task_dir / "output"

source_specs = [
    ("bob", legacy_dir / "bob", output_dir / "bob"),
    ("cloud_graphs", legacy_dir / "cloud_graphs", output_dir / "cloud_graphs"),
    ("outlier_charts", legacy_dir / "outlier_charts", output_dir / "outlier_charts"),
]

binary_suffixes = {".pdf", ".png", ".zip", ".dta", ".xlsx", ".docx", ".irf", ".mat"}
code_suffixes = {".do", ".m", ".ado", ".py", ".r", ".jl"}

output_dir.mkdir(parents=True, exist_ok=True)

rows = []
for group_name, source_root, destination_root in source_specs:
    if not source_root.exists():
        continue
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    for source_path in sorted(source_root.rglob("*")):
        if ".git" in source_path.parts or not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        if source_path.suffix.lower() in code_suffixes:
            continue

        relative_source = source_path.relative_to(source_root)
        destination = destination_root / relative_source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        if source_hash != destination_hash:
            raise RuntimeError(f"Copy hash mismatch for {relative_source}")

        rows.append(
            {
                "source": str(source_path.relative_to(repo_dir)),
                "destination": str(destination.relative_to(repo_dir)),
                "group": group_name,
                "size_bytes": destination.stat().st_size,
                "sha256": destination_hash,
            }
        )

        if destination.suffix.lower() in binary_suffixes:
            description = destination.with_name(destination.stem + "_description.txt")
            with open(description, "w", encoding="utf-8") as f:
                f.write(f"Artifact: {destination.name}\n")
                f.write(f"Copied from: {source_path.relative_to(repo_dir)}\n")
                f.write("Purpose: exact legacy generated archive preserved under the current task structure.\n")
                f.write("Transformation: none; SHA-256 hash matches the legacy source file.\n")
                f.write(f"SHA-256: {destination_hash}\n")

manifest = pd.DataFrame(rows)
manifest.to_csv(output_dir / "generated_output_archives_manifest.txt", index=False)
print(f"Copied {len(manifest)} legacy generated archive artifacts.")
