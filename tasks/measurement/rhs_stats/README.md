# RHS Stats

## Purpose

Create a manuscript-style table of model and non-model RHS attribute averages using one row per MMB model.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`
- `config/params.yaml`: shared variable labels

## Outputs

- `output/table_rhs_stats.tex`
- `output/table_rhs_stats.csv`
- `output/manifest.csv`

## Notes

The table reports model-level averages for the final analysis model universe, not the broader pre-curation RHS file and not model-rule observation averages.
The any-channel row is recomputed as the union of the four current channel indicators: constrained household demand, firm balance sheet, bank intermediation, and labor-market friction.
The estimation-sample rows use estimated models only.
