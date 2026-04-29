# Import MMB Legacy Data

## Purpose

Bring immutable inputs from `legacy/mmb_upgraded/` into the production workflow without copying large files or treating `legacy/` as a direct downstream dependency.

## Inputs

- `legacy/mmb_upgraded/data/raw/responses/*.csv`: model impulse-response CSVs from the MMB app.
- `legacy/mmb_upgraded/data/raw/sacratios/csv/*.csv`: inflation-target shock response CSVs used for sacrifice ratios.
- `legacy/mmb_upgraded/data/raw/sacratios/json/*.json`: original MMB app JSON exports for the sacrifice-ratio experiment.
- `legacy/mmb_upgraded/data/raw/Model_Characteristics_corrections.xlsx`: corrected hand-coded model attributes used as the main feed-in model-characteristics input.
- `legacy/mmb_upgraded/data/raw/Bob_IRFS_63Q1_07Q4.csv`: VAR benchmark IRFs used in cloud graphs.
- `legacy/mmb_upgraded/data/raw/stationaryvardata.csv`: raw VAR input data retained for provenance.
- `legacy/mmb_upgraded/data/classifications.csv`: legacy model classification file retained for provenance.
- `legacy/mmb_upgraded/models/`, `models-of-interest/`, and `user_defined_rules/`: MMB model files and policy-rule parameter files retained for provenance.

## Outputs

The task writes relative symbolic links under `output/` plus source metadata:

- `output/responses/`
- `output/sacratios_csv/`
- `output/sacratios_json/`
- `output/model_characteristics.xlsx`
- `output/model_characteristics_codebook.txt`
- `output/bob_var_irfs.csv`
- `output/stationary_var_data.csv`
- `output/classifications.csv`
- `output/models`
- `output/models_of_interest`
- `output/user_defined_rules`
- `output/source_inventory.txt`

## Run

From `tasks/import_mmb_legacy_data/code/`:

```bash
make
```

## Notes

This task does not alter the legacy archive. Downstream tasks should depend on these `output/` links through their own `input/` symlinks.
