# Reproduce Legacy Outputs

## Purpose

Preserve exact legacy figures, tables, regression outputs, and robustness-output files under the current task structure.

This task is intentionally different from the rebuild tasks. It does not reinterpret or redraw legacy artifacts. It copies the original output artifacts bit-for-bit into this task's `output/` folder and writes a manifest so the copied files can be audited.

## Inputs

- `legacy/mmb_upgraded/output/`
- `legacy/mmb_upgraded/bob/`
- `legacy/mmb_upgraded/cloud_graphs/`
- `legacy/mmb_upgraded/outlier_charts/`

## Outputs

- `output/legacy_exact/...`: copied legacy artifacts
- `output/legacy_exact_manifest.txt`: source and destination inventory
- `<binary>_description.txt`: metadata companions for copied binary artifacts

## Run

From `tasks/reproduce_legacy_outputs/code/`:

```bash
make
```

## Notes

Use this task when exact legacy artifact parity matters. Use `tasks/build_mmb_analysis_dataset` and later Python analysis tasks when rebuilding results from source data matters.
