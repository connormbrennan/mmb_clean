# Generated Output Archives

## Purpose

Preserve exact generated-output archive families that are useful for provenance but do not belong to the more specific graph, measurement, mechanisms, quantitative, or paper tasks.

This task does not reinterpret or redraw artifacts. It copies the original files bit-for-bit into this task's `output/` folder and writes a manifest so the copied files can be audited.

## Inputs

- `legacy/mmb_upgraded/bob/`
- `legacy/mmb_upgraded/cloud_graphs/`
- `legacy/mmb_upgraded/outlier_charts/`

## Outputs

- `output/bob/`
- `output/cloud_graphs/`
- `output/outlier_charts/`
- `output/generated_output_archives_manifest.txt`: source and destination inventory
- `<binary>_description.txt`: metadata companions for copied binary artifacts

## Run

From `tasks/legacy/generated_output_archives/code/`:

```bash
make
```

## Notes

Specific regression, mechanism, summary-statistic, and paper-table outputs are now filed in their own task folders.
