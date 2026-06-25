# Summary Stats

## Purpose

Generate Tables 3-5 summary statistics and timing histograms from the MMB analysis dataset.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/summarystats/table3_summary_stats.tex`
- `output/summarystats/table3_summary_stats.csv`
- `output/summarystats/table4_elasticity_stats.tex`
- `output/summarystats/table4_elasticity_stats.csv`
- `output/summarystats/table5_timing_stats.tex`
- `output/summarystats/table5_timing_stats.csv`
- `output/summarystats/outcome_summary_stats_by_rule.csv`
- `output/summarystats/texresults_outcomevars_stats_output.txt`
- `output/summarystats/*_timing_hist.pdf`
- `output/summarystats/*_description.txt`
- `output/manifest.csv`

## Sample rule

The input dataset has 222 model-rule observations. Tables 3-5 use the main
summary-statistics sample, which excludes observations with `y_timing_max >= 99`
or `piq_timing_max >= 99`. This removes five timing-outlier observations coded
at 99 quarters, leaving 217 observations for the main y-slope, pi-slope,
y-timing, and pi-timing summaries. Sacrifice-ratio counts are lower where the
disinflation experiment is infeasible.

## Run

From `tasks/measurement/summary_stats/code/`:

```bash
make
```
