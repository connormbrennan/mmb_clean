# Build MMB Analysis Dataset

## Purpose

Construct the production analysis datasets from MMB response exports and hand-coded model attributes.

This task replaces the legacy Stata data-construction core with one flat Python script. The script keeps the same economic steps visible: import IRFs, build model attributes, compute outcome variables, compute sacrifice ratios, and merge the regression panel.

## Inputs

Inputs are symlinks created by this task's Makefile:

- `input/responses/`: response CSVs from `tasks/data/import_mmb_legacy_data/output/responses/`
- `input/sacratios_csv/`: sacrifice-ratio response CSVs from `tasks/data/import_mmb_legacy_data/output/sacratios_csv/`
- `input/Model_Characteristics_corrections_llm.xlsx`, linked from `tasks/data/classifying_api/output/`.
- `input/bob_var_irfs.csv`
- `config/params.yaml`

## Outputs

- `output/MMB_IRF_format.dta`
- `output/MMB_IRF_format.csv`
- `output/MMB_IRF_format_codebook.txt`
- `output/MMB_IRF_format_full.dta`
- `output/MMB_IRF_format_full_codebook.txt`
- `output/lhs_20.dta`
- `output/lhs_40.dta`
- `output/lhs_60.dta`
- `output/MMB_reg_format.dta`
- `output/MMB_reg_format.xlsx`
- `output/MMB_reg_format_codebook.txt`
- `output/rhs.dta`
- `output/sacratios_20.dta`
- `output/sacratios_40.dta`
- `output/sacratios_60.dta`
- `output/parity_report.txt`

## Run

From `tasks/data/build_mmb_analysis_dataset/code/`:

```bash
make
```

## Method Notes

- Model-rule IRFs are sign-flipped so the maintained shock is an expansionary monetary policy shock, following the legacy pipeline.
- The real rate is constructed as the nominal interest-rate response minus next-quarter quarterly inflation.
- The output response follows the legacy data construction exactly: `Output Gap` is used for `y`, while the separate `Output` rows are ignored.
- Sacrifice-ratio values are calculated in Python from the raw sacrifice-ratio CSVs linked into `input/sacratios_csv/`. The task does not read derived legacy `sacratios_*.dta` files.
- Terminal real-rate observations that lack next-quarter inflation are left missing. Cumulative real-rate outcomes also become missing when the horizon window contains a missing real rate.
- Citation weights in the regression panel use `cites` and `pub_date`: years since publication are measured as of `citation_weight_as_of` in `config/params.yaml`, citations per year are `(1 + cites) / (1 + years since publication)`, and `citation_weight` is `log(1 + cites_per_year)` normalized to mean one.
- Because the main model-characteristics input is now `Model_Characteristics_corrections_llm.xlsx` and sacrifice ratios are rebuilt from raw CSVs, the parity report is expected to show structured differences from old legacy derived datasets in model-attribute and sacrifice-ratio columns.
- Stable parameters and sample restrictions come from `config/params.yaml`.
