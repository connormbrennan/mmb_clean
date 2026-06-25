# Lasso Feature Screen

## Purpose

Screen model and non-model attributes for the MMB outcomes using LASSO-style selection with paper controls always included.
Elasticity outcomes use a Belloni-Chernozhukov-style feasible square-loss LASSO with iterated heteroskedastic penalty loadings after residualizing policy-rule and estimated-model controls.
Timing outcomes use a Poisson L1 screen with policy-rule and estimated-model controls included but unpenalized.
The current screening multiplier is `0.5`; the canonical `1.0` multiplier selected an empty model for all outcomes in this application.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/lasso/lasso_coefficients_long.csv`
- `output/lasso/lasso_coefficients_long_citation_weighted.csv`
- `output/lasso/lasso_zeroed_summary.csv`
- `output/lasso/lasso_zeroed_summary_citation_weighted.csv`
- `output/lasso/lasso_zeroed_features.csv`
- `output/lasso/lasso_zeroed_features_citation_weighted.csv`
- `output/lasso/lasso_nonzero_features.csv`
- `output/lasso/lasso_nonzero_features_citation_weighted.csv`
- `output/lasso/lasso_sparse_dropped_features.csv`
- `output/lasso/lasso_sparse_dropped_features_by_outcome.csv`
- `output/lasso/lasso_sparse_dropped_features_by_outcome_citation_weighted.csv`
- `output/lasso/lasso_zeroed_report.txt`
- `output/lasso/lasso_zeroed_report_citation_weighted.txt`
- `output/lasso/lasso_post_selection_table.tex`
- `output/lasso/lasso_post_selection_table.csv`
- `output/lasso/lasso_post_selection_table_citation_weighted.tex`
- `output/lasso/lasso_post_selection_table_citation_weighted.csv`
- `output/lasso/post_refit_diagnostics.csv`
- `output/lasso/post_refit_diagnostics_citation_weighted.csv`
- `output/lasso/lasso_metadata.json`

The post-selection tables refit selected variables with policy-rule and estimated-model controls and report standard errors clustered by model.
Elasticity outcomes use robust linear post-selection refits. Timing outcomes use Poisson GLM post-selection refits, with a negative-binomial GLM used when an auxiliary overdispersion test rejects equidispersion.
The global sparse-feature file records binary features dropped before outcome-specific screens. The by-outcome sparse-feature files record binary features dropped after each outcome sample is formed, including the lower-observation sacrifice-ratio sample.
The post-refit diagnostics files record selected terms dropped from post-selection refits because of zero variance or exact collinearity.
The citation-weighted outputs rerun the same outcome-specific screens with normalized citation weights and use the same weights in the post-selection refits.

## Run

From `tasks/measurement/lasso/code/`:

```bash
make
```
