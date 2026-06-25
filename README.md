# Consensus and Dissension on the Power of Monetary Policy

This repository contains the production workflow for the paper *Consensus and
Dissension on the Power of Monetary Policy: What 75 Macroeconomic Models Have
to Say* by William B. English, Robert J. Tetlow, and Connor M. Brennan.

The project rebuilds a Macroeconomic Model Data Base (MMB) analysis dataset,
codes model characteristics, and generates the summary statistics, regression
tables, figures, and paper-supporting diagnostics used in the manuscript.

## Research Question

The paper asks how large monetary-policy effects are across macroeconomic
models, how quickly those effects arrive, and which model or non-model
attributes help explain disagreement across models.

Rather than relying on one structural model, the analysis compares standardized
monetary-policy experiments across 75 MMB models under three policy rules:
Taylor, inertial Taylor, and growth rules.

## Production Pipeline

The stable workflow lives in `tasks/`. The main production sequence is:

1. `tasks/data/import_mmb_legacy_data/` links immutable legacy MMB inputs.
2. `tasks/data/classifying_api/` preserves the Gemini API-based audit workflow
   for model-characteristic codings and writes the corrected workbook.
3. `tasks/data/build_mmb_analysis_dataset/` rebuilds the IRF panel and
   regression-format analysis dataset.
4. `tasks/graphs/` regenerates cloud-graph outputs from the rebuilt IRF panel.
5. `tasks/measurement/` generates summary statistics, coefficient plots,
   model-attribute tables, LASSO checks, and regression tables.
6. `tasks/mechanisms/interactions_with_rules/` estimates and plots
   attribute-by-rule interaction checks.
7. `tasks/paper/` builds paper-facing table bundles.

The expensive Gemini audit target is `make run` inside
`tasks/data/classifying_api/code/`. Ordinary project rebuilds should use the
already-generated audit results through `make corrections-workbook`, which does
not send new API requests.

## Main Outputs

The analysis dataset task produces:

- `MMB_IRF_format.dta` and `MMB_IRF_format_full.dta`: IRF panels.
- `MMB_reg_format.dta`: model-rule regression panel.
- `rhs.dta`, `lhs_20.dta`, `lhs_40.dta`, `lhs_60.dta`, and sacrifice-ratio
  datasets used by downstream tasks.

The measurement tasks produce:

- Table 2-style RHS/model-attribute summaries.
- Table 3-style summary statistics and timing histograms.
- Table 6 policy-rule and estimated-model regressions.
- Table 7 nominal-rigidity regressions.
- Table 8 real-rigidity regressions.
- Table 9 nonmodel-attribute regressions.
- Table 10 broad model-variable regressions.
- LASSO and stepwise variable-selection checks.
- Cross-rule rank-stability diagnostics.
- Model-vs-rule variance-decomposition diagnostics.

## Outcome Measures

Downstream tasks focus on five monetary-transmission outcomes:

- `IScurve20`: output response per real-rate response.
- `infl_per_rr20`: inflation response per real-rate response.
- `sacratio20`: sacrifice ratio from the disinflation experiment.
- `y_timing_max`: quarter of peak output response.
- `piq_timing_max`: quarter of peak inflation response.

The main regression sample excludes timing sentinel observations at or above the
shared timing cutoff in `config/params.yaml`.

## Model Attributes

The current model-characteristic schema includes:

- Policy-rule indicators.
- Estimated-model status.
- Nominal rigidities: sticky wages, wage indexation, and price indexation.
- Real channels: constrained household demand, firm balance sheets, bank
  intermediation, labor-market frictions, and open economy.
- Non-model attributes: central-bank authorship, model size, vintage, and
  estimation-sample timing where relevant.

## Estimation Conventions

The regression-table tasks use:

- Robust linear regressions with model-clustered inference for slope and
  sacrifice-ratio outcomes.
- Poisson GLMs for timing outcomes, with a negative-binomial GLM used when an
  auxiliary overdispersion test rejects equidispersion.
- Citation-weighted companion specifications where configured.

Sparse-cell diagnostics are included for saturated real-channel and broad-model
specifications, and weakly supported cells are suppressed from paper-facing
tables where appropriate.

## Rebuilding

There is no root `make all` target. Rebuild individual production tasks from
their task root or `code/` directory, for example:

```bash
make -C tasks/data/build_mmb_analysis_dataset
make -C tasks/measurement/summary_stats
make -C tasks/measurement/policy_rules_estimation
make -C tasks/paper/paper_tables/code
```

To refresh the corrected classification workbook without sending new Gemini API
requests:

```bash
make -C tasks/data/classifying_api/code corrections-workbook
```

Avoid `make -C tasks/data/classifying_api/code run` unless you explicitly want
to send Gemini API requests.

## Repository Layout

- `config/`: shared parameters, labels, and model-specification settings.
- `legacy/`: immutable legacy MMB source archive and generated-output archive
  material.
- `notes/`: logbook and project notes.
- `paper/`: manuscript-facing files.
- `scratch/`: exploratory notebooks and one-off analysis.
- `scripts/`: repository helper scripts.
- `tasks/`: production data, graph, measurement, mechanism, and paper tasks.

## Workflow Rules

- Stable work belongs in `tasks/`, not `scratch/`.
- Each production task owns its `input/`, `code/`, `output/`, `README.md`, and
  Makefile.
- Downstream tasks consume upstream outputs through symlinks in `input/`.
- Use `config/params.yaml` for reusable parameters.
- Record substantive methodological changes in `notes/logbook.md`.

## Disclaimer

The views expressed are those of the authors and do not necessarily reflect the
views of the Board of Governors of the Federal Reserve System, the Federal Open
Market Committee, or members of their staffs.
