# Interactions With Rules

## Purpose

Estimate how selected model attributes interact with policy rules in robust outcome regressions.

## Inputs

- `input/MMB_reg_format.dta`: symlink to `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`

## Outputs

- `output/interactions_with_rules/*.csv`
- `output/interactions_with_rules/*.pdf`
- `output/interactions_with_rules/*_description.txt`
- `output/manifest.csv`

## Run

From `tasks/mechanisms/interactions_with_rules/code/`:

```bash
make
```
