"""
Purpose:
    Copy exact legacy generated outputs into the task structure.

Inputs:
    ../../../legacy/mmb_upgraded/output/
    ../../../legacy/mmb_upgraded/bob/
    ../../../legacy/mmb_upgraded/cloud_graphs/
    ../../../legacy/mmb_upgraded/outlier_charts/

Outputs:
    ../output/legacy_exact/
    ../output/legacy_exact_manifest.txt
    Companion *_description.txt files for copied binary artifacts.

Run:
    make from tasks/reproduce_legacy_outputs/code/
"""

from pathlib import Path
import hashlib
import shutil

import pandas as pd


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
repo_dir = task_dir.parents[1]
legacy_dir = repo_dir / "legacy" / "mmb_upgraded"
output_dir = task_dir / "output"
exact_dir = output_dir / "legacy_exact"

source_dirs = [
    legacy_dir / "output",
    legacy_dir / "bob",
    legacy_dir / "cloud_graphs",
    legacy_dir / "outlier_charts",
]

binary_suffixes = {".pdf", ".png", ".zip", ".dta", ".xlsx", ".docx", ".irf", ".mat"}
legacy_code_suffixes = {".do", ".m", ".ado", ".py", ".r", ".jl"}

if exact_dir.exists():
    shutil.rmtree(exact_dir)
exact_dir.mkdir(parents=True, exist_ok=True)

rows = []
for source_root in source_dirs:
    if not source_root.exists():
        continue
    for source_path in sorted(source_root.rglob("*")):
        if ".git" in source_path.parts or not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        if source_path.suffix.lower() in legacy_code_suffixes:
            continue

        relative_source = source_path.relative_to(legacy_dir)
        destination = exact_dir / relative_source
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
                "size_bytes": destination.stat().st_size,
                "sha256": destination_hash,
            }
        )

        if destination.suffix.lower() in binary_suffixes:
            description = destination.with_name(destination.stem + "_description.txt")
            with open(description, "w", encoding="utf-8") as f:
                f.write(f"Artifact: {destination.name}\n")
                f.write(f"Copied from: {source_path.relative_to(repo_dir)}\n")
                f.write("Purpose: exact legacy generated output preserved under the current task structure.\n")
                f.write("Transformation: none; SHA-256 hash matches the legacy source file.\n")
                f.write(f"SHA-256: {destination_hash}\n")

manifest = pd.DataFrame(rows)
manifest.to_csv(output_dir / "legacy_exact_manifest.txt", index=False)
print(f"Copied {len(manifest)} legacy generated artifacts.")
