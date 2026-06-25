# Stepwise Regressions

## Purpose

Run bidirectional stepwise Python regressions for MMB outcome and timing variables using nominal-rigidity, real-rigidity, non-model, and combined candidate sets.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/stepwise_regressions/*.txt`
- `output/manifest.csv`

## Run

From `tasks/measurement/stepwise_regressions/code/`:

```bash
make
```
