# Generate MMB Cloud Graphs

## Purpose

Generate IRF cloud graphs from the constructed MMB IRF panel.

Each graph shows model-rule IRFs after a 100 basis point monetary policy shock, with the cross-model median and the Smets-Wouters 2007 model highlighted.

## Inputs

- `input/MMB_IRF_format_full.dta` from `tasks/data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta`

## Outputs

- PDF cloud graphs in `output/`
- One `<figure>_description.txt` metadata file per PDF
- `output/cloud_graphs_manifest.txt`

## Run

From `tasks/graphs/generate_mmb_cloud_graphs/code/`:

```bash
make
```
