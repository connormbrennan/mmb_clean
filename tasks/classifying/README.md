# Consensus Economics Inflation Expectations

This task builds a vintage panel of Consensus Economics CPI inflation expectations from WRDS LSEG/Refinitiv Datastream.

The important distinction from `ce_test.ipynb` is that Consensus Economics forecasts are stored as annual target-year series with repeated `announceddate` vintages. The notebook searched for `CONPRC*` mnemonics and then kept the latest revision by `perioddate`, which pulls realized CPI-style series and discards the forecast vintage history.

Run from `tasks/classifying/code/`:

```sh
make all
```

Outputs are written to `output/`:

- `consensus_economics_inflation_expectations_panel.csv`: mean inflation expectations for next-/two-calendar-year targets, where available.
- `consensus_economics_inflation_expectations_panel.parquet`: same panel in parquet format.
- `consensus_economics_inflation_forecast_vintages.csv`: all CPI forecast summary-statistic vintages found from the explicit Consensus Economics source.
- `consensus_economics_series_metadata.csv`: Datastream metadata for selected series.
- `consensus_economics_inflation_expectations_panel_codebook.txt`: row counts, coverage, filters, dtypes, and sample rows.
- `consensus_economics_wrds_availability_audit.txt`: reproducible WRDS metadata audit documenting the checked schemas, tables, mnemonic patterns, and Consensus-like code-table labels.

Public LSEG documentation indicates that the broader fee-liable Consensus Economics product exists on Datastream with 1- and 2-year projections for many countries. The finding here is narrower: in this WRDS-hosted Datastream Economics SQL product, the explicit Consensus Economics CPI coverage exposed through `tr_ds_econ`/`trdstrm` is sparse. Albania has the mean CPI forecast series and the Netherlands has a standard-deviation series. The code records that coverage directly rather than falling back to realized CPI series.
