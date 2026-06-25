# Paper Tables

## Purpose

Build manuscript regression tables directly from the MMB analysis dataset using Python robust outcome regressions and count timing regressions.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/paper_tables/*_full_sample.txt`
- `output/paper_tables/*_estimated_models.txt`
- `output/paper_tables/all_regression_tables.txt`
- `output/paper_tables/manifest.csv`

## Run

From `tasks/paper/paper_tables/code/`:

```bash
make
```
