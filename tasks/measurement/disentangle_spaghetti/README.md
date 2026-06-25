# Disentangle Spaghetti

## Purpose

Measure how much MMB policy-transmission heterogeneity is explained by rules, model identity, model attributes, IRF shape archetypes, nonlinear predictors, and outlier sensitivity.

IRF archetypes are formed from output, inflation, and nominal-rate paths only (`y`, `piq`, and `irate`). The real rate (`rrate`) is excluded because it is a lagged linear combination of nominal rates and inflation. The task reports a baseline summary-feature k-means archetype analysis plus functional-PCA, Ward hierarchical-clustering, and diagonal-covariance Gaussian-mixture alternatives.

Driver regressions use model-clustered inference in the panel specification. Timing driver regressions follow the paper-table rule: Poisson GLM first, with a negative-binomial GLM used only when an auxiliary overdispersion test rejects equidispersion. Significant panel terms with fewer than five supporting models are excluded from the headline significant-driver table and written separately.

Prediction diagnostics use cross-validation folds grouped by model, so all rule observations for a model are assigned to the same train or test fold.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`
- `input/MMB_IRF_format_full.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta`

## Outputs

- `output/disentangle_spaghetti/*.csv`
- `output/disentangle_spaghetti/findings_report.md`
- `output/disentangle_spaghetti/ward_archetype_summary.png`
- `output/disentangle_spaghetti/ward_archetype_summary_description.txt`
- `output/manifest.csv`

## Run

From `tasks/measurement/disentangle_spaghetti/code/`:

```bash
make
```
