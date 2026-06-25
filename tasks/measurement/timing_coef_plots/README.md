# Timing Coefficient Plots

## Purpose

Estimate bivariate timing regressions and plot attribute and rule coefficients for output and inflation timing.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/coef_plots_timing/*.pdf`
- `output/coef_plots_timing/*_description.txt`
- `output/coef_plots_timing.zip`
- `output/coef_plots_timing_description.txt`
- `output/manifest.csv`

## Run

From `tasks/measurement/timing_coef_plots/code/`:

```bash
make
```
