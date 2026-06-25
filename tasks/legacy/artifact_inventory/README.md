# Artifact Inventory

## Purpose

Inventory legacy files that are useful for provenance but are not part of the current reproducible production workflow.

This task does not promote old drafts, exploratory notebooks, generated PDFs, old Stata logs, or scratch model-alteration scripts into production. It records where they are and how they should be treated.

## Inputs

- `legacy/mmb_upgraded/`

## Outputs

- `output/artifact_inventory.txt`

## Run

From `tasks/legacy/artifact_inventory/code/`:

```bash
make
```

## Disposition

- Core raw inputs are promoted through `tasks/data/import_mmb_legacy_data`.
- Core analysis datasets are rebuilt through `tasks/data/build_mmb_analysis_dataset`.
- Cloud figures are rebuilt through `tasks/graphs/generate_mmb_cloud_graphs`.
- Legacy drafts, generated regression PDFs, old notebooks, and one-off scripts remain in `legacy/` until a specific downstream task needs them.
