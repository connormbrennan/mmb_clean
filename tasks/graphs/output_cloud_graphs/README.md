# Output Cloud Graphs

## Purpose

Generate a bundled set of MMB IRF cloud graphs from the constructed IRF panel.

## Inputs

- `input/MMB_IRF_format_full.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta`

## Outputs

- `output/cloud_graphs/*.pdf`
- `output/cloud_graphs/*_description.txt`
- `output/manifest.csv`

## Run

From `tasks/graphs/output_cloud_graphs/code/`:

```bash
make
```
