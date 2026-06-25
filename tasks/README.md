# Tasks

`tasks/` contains production work.

Top-level folders are workstreams, not rigid stages.
Add new workstreams if the project needs them.

Each task should be an economically meaningful unit, not a junk drawer.

## Workstreams

- `data/`: source imports, model classification inputs/audits, and constructed analysis datasets.
- `graphs/`: graph outputs generated from task inputs.
- `measurement/`: regression, selection, summary-statistics, and measurement-output artifacts.
- `mechanisms/`: mechanism and interaction outputs.
- `model/`: model-solving and model-comparison tasks.
- `legacy/`: provenance inventories and generated archives that do not fit a narrower workstream.

## Current Tasks

Data:

- `data/import_mmb_legacy_data/`: links immutable MMB source inputs from the legacy archive into task outputs.
- `data/classifying/`: hand-maintained model-classification source files used by the audit task.
- `data/classifying_v2/`: audits model-characteristic codings with Gemini and writes the corrected workbook.
- `data/build_mmb_analysis_dataset/`: rebuilds the IRF panel and regression-format dataset in Python.

Graphs:

- `graphs/generate_mmb_cloud_graphs/`: regenerates cloud graphs from the rebuilt IRF panel in Python.
- `graphs/output_cloud_graphs/`: generates the bundled cloud-graph output set from the rebuilt IRF panel.

Measurement:

- `measurement/outcome_coef_plots/`: estimates robust bivariate outcome regressions and plots coefficients.
- `measurement/timing_coef_plots/`: estimates timing regressions and plots coefficients.
- `measurement/disentangle_spaghetti/`: computes decomposition, archetype, and variance outputs.
- `measurement/lasso/`: runs penalized feature-selection screens.
- `measurement/stepwise_regressions/`: runs bidirectional stepwise regressions.
- `measurement/policy_rules_estimation/`: estimates policy-rule and estimated-model outcome tables.
- `measurement/nominal_rigidities/`: estimates nominal-rigidity outcome tables.
- `measurement/real_rigidities/`: estimates real-rigidity and transmission-channel outcome tables.
- `measurement/nonmodel_attributes/`: estimates nonmodel-attribute outcome tables.
- `measurement/broad_model_variables/`: estimates combined broad-variable outcome tables.
- `measurement/rhs_stats/`: summarizes model-level RHS attribute averages for manuscript tables.
- `measurement/summary_stats/`: generates Table 3-style summary-statistics outputs and timing histograms.

Mechanisms:

- `mechanisms/interactions_with_rules/`: estimates and plots attribute-by-rule interaction effects.

Legacy:

- `legacy/generated_output_archives/`: preserves remaining generated archive families such as `bob/`, old cloud-graph archives, and outlier charts.
- `legacy/artifact_inventory/`: inventories remaining legacy files and records their disposition.
