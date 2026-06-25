# cross_rule_rank_stability

## Purpose
Show whether models preserve their relative rankings across monetary policy rules.

## Inputs
- `input/MMB_reg_format.dta`, symlinked from `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`
- `config/params.yaml`, used for the shared paper timing cutoff

## Outputs
- `output/cross_rule_rank_stability.csv`
- `output/cross_rule_rank_stability.tex`
- `output/cross_rule_rank_stability_heatmap.pdf`
- `output/cross_rule_rank_stability_heatmap.png`
- `output/cross_rule_rank_stability_heatmap_description.txt`
- `output/findings_note.md`
- `output/manifest.csv`

## Notes
The script filters to the paper regression sample and pivots each outcome to a model-by-rule matrix. It computes Spearman and Pearson correlations for each requested policy-rule pair, with the paper figure focused on Spearman rank stability.
