# Outcome Coefficient Plots

## Purpose

Estimate bivariate robust outcome regressions and plot attribute and rule coefficients for the MMB outcome measures.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/coef_plots_outcomes/*.pdf`
- `output/coef_plots_outcomes/*_description.txt`
- `output/coef_plots_outcomes.zip`
- `output/coef_plots_outcomes_description.txt`
- `output/manifest.csv`

## Run

From `tasks/measurement/outcome_coef_plots/code/`:

```bash
make
```
