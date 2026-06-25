"""
Purpose:
    Copy exact disentangle-spaghetti artifacts into this task.

Inputs:
    ../../../../legacy/mmb_upgraded/output/disentangle_spaghetti/

Outputs:
    ../output/disentangle_spaghetti/
    ../output/exact_manifest.txt

Run:
    make from tasks/measurement/disentangle_spaghetti/code/
"""

from pathlib import Path
import csv
import hashlib
import shutil


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
repo_dir = task_dir.parents[2]
legacy_dir = repo_dir / "legacy" / "mmb_upgraded"
output_dir = task_dir / "output"

source_specs = [
    ("output/disentangle_spaghetti", "disentangle_spaghetti"),
]

binary_suffixes = {".pdf", ".png", ".zip", ".dta", ".xlsx", ".docx", ".irf", ".mat"}
code_suffixes = {".do", ".m", ".ado", ".py", ".r", ".jl"}

output_dir.mkdir(parents=True, exist_ok=True)

rows = []
for source_relative, destination_relative in source_specs:
    source_root = legacy_dir / source_relative
    destination_root = output_dir / destination_relative
    if not source_root.exists():
        raise SystemExit(f"Missing legacy source: {source_root.relative_to(repo_dir)}")

    if destination_root.exists():
        if destination_root.is_dir():
            shutil.rmtree(destination_root)
        else:
            destination_root.unlink()

    if source_root.is_dir():
        source_files = [p for p in sorted(source_root.rglob("*")) if p.is_file()]
    else:
        source_files = [source_root]

    for source_path in source_files:
        if ".git" in source_path.parts or source_path.name == ".DS_Store":
            continue
        if source_path.suffix.lower() in code_suffixes:
            continue

        if source_root.is_dir():
            destination = destination_root / source_path.relative_to(source_root)
        else:
            destination = destination_root
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        if source_hash != destination_hash:
            raise RuntimeError(f"Copy hash mismatch for {source_path.relative_to(repo_dir)}")

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
                f.write("Purpose: exact generated output preserved under the current task structure.\n")
                f.write("Transformation: none; SHA-256 hash matches the legacy source file.\n")
                f.write(f"SHA-256: {destination_hash}\n")

manifest_path = output_dir / "exact_manifest.txt"
with open(manifest_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "destination", "size_bytes", "sha256"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Copied {len(rows)} exact artifacts.")
