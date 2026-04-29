# Build MMB Analysis Dataset

## Purpose

Construct the production analysis datasets from MMB response exports and hand-coded model attributes.

This task replaces the legacy Stata data-construction core with one flat Python script. The script keeps the same economic steps visible: import IRFs, build model attributes, compute outcome variables, compute sacrifice ratios, and merge the regression panel.

## Inputs

Inputs are symlinks created by this task's Makefile:

- `input/responses/`: response CSVs from `tasks/import_mmb_legacy_data/output/responses/`
- `input/sacratios_csv/`: sacrifice-ratio response CSVs from `tasks/import_mmb_legacy_data/output/sacratios_csv/`
- `input/model_characteristics.xlsx`, linked from the corrected legacy model-characteristics workbook.
- `input/bob_var_irfs.csv`
- `config/params.yaml`

## Outputs

- `output/MMB_IRF_format.dta`
- `output/MMB_IRF_format.csv`
- `output/MMB_IRF_format_codebook.txt`
- `output/MMB_IRF_format_full.dta`
- `output/MMB_IRF_format_full_codebook.txt`
- `output/MMB_reg_format.dta`
- `output/MMB_reg_format.xlsx`
- `output/MMB_reg_format_codebook.txt`
- `output/parity_report.txt`

## Run

From `tasks/build_mmb_analysis_dataset/code/`:

```bash
make
```

## Method Notes

- Model-rule IRFs are sign-flipped so the maintained shock is an expansionary monetary policy shock, following the legacy pipeline.
- The real rate is constructed as the nominal interest-rate response minus next-quarter quarterly inflation.
- The output response follows the legacy data construction exactly: `Output Gap` is used for `y`, while the separate `Output` rows are ignored.
- Sacrifice-ratio values are calculated in Python, then replaced with the legacy Stata `sacratios_*.dta` values when those golden files are present. This preserves the historical sacrifice-ratio inputs while keeping the Python calculation inspectable.
- Because the main model-characteristics input is now `Model_Characteristics_corrections.xlsx`, the parity report is expected to differ from the old legacy derived datasets in model-attribute columns touched by those corrections.
- Stable parameters and sample restrictions come from `config/params.yaml`.
