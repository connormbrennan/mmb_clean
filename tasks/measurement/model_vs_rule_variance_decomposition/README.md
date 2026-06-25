# model_vs_rule_variance_decomposition

## Purpose
Show whether cross-model heterogeneity explains more variation in monetary-transmission outcomes than policy-rule heterogeneity.

## Inputs
- `input/MMB_reg_format.dta`, symlinked from `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`
- `config/params.yaml`, used for the shared paper timing cutoff

## Outputs
- `output/model_vs_rule_variance_decomposition.csv`
- `output/model_vs_rule_variance_decomposition.tex`
- `output/model_vs_rule_variance_decomposition.pdf`
- `output/model_vs_rule_variance_decomposition.png`
- `output/model_vs_rule_variance_decomposition_description.txt`
- `output/findings_note.md`
- `output/manifest.csv`

## Notes
The script filters to the paper regression sample by dropping rows with the shared timing cutoff in either timing outcome and rows missing `model` or `rule`. For each outcome, it fits rule-only, model-only, and rule-plus-model fixed-effect regressions using the canonical MMB regression dataset.
