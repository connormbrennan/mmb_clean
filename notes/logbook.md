# Logbook

Use this as a running research log.

A good entry records:
- what you did
- why you did it
- what changed
- what the result means
- what the next step is

---

## YYYY-MM-DD

### Task
-

### What I did
-

### Result
-

### Interpretation
-

### Next step
-

## 2026-06-04

### Task
- Reorganized `tasks/` into workstream folders and split the old exact-output copy task by artifact family.

### What I did
- Moved data construction/classification tasks under `tasks/data/`, cloud graph tasks under `tasks/graphs/`, regression, selection, and summary-statistics artifacts under `tasks/measurement/`, rule-interaction artifacts under `tasks/mechanisms/`, manuscript tables under `tasks/paper/`, and residual archive/provenance tasks under `tasks/legacy/`.
- Replaced the monolithic `reproduce_legacy_outputs` task with topic-specific exact-copy tasks: `output_cloud_graphs`, `outcome_coef_plots`, `timing_coef_plots`, `disentangle_spaghetti`, `interactions_with_rules`, `lasso`, `stepwise_regressions`, `summary_stats`, `table11`, and `paper_tables`.
- Updated Makefile paths and task documentation to match the nested workstream layout.
- Standardized `tasks/data/classifying/` as a source-data task and moved the exploratory `ce_test.ipynb` notebook to `scratch/notebooks/`.

### Result
- Exact generated artifacts remain reproducible from `legacy/mmb_upgraded/`, but they now sit in task folders named by economic or paper purpose rather than in a single catch-all output task.

### Interpretation
- This makes downstream references more inspectable: measurement regressions live with measurement, mechanism interactions live with mechanisms, and paper-facing tables live with paper outputs.

### Next step
- Use the workstream paths in `tasks/README.md` as the navigation map for future tasks.

## 2026-04-28

### Task
- Reorganized the legacy MMB workflow into production tasks while preserving the original generated outputs exactly.

### What I did
- Created `tasks/import_mmb_legacy_data`, `tasks/build_mmb_analysis_dataset`, `tasks/generate_mmb_cloud_graphs`, `tasks/reproduce_legacy_outputs`, and `tasks/archive_legacy_artifacts`.
- Moved reusable MMB parameters into `config/params.yaml`: horizons, dropped model-rule ids, output response labels, graph extent, and seed.
- Rewrote the stable data build and cloud graph generation in Python with task-local `input`, `code`, and `output` folders and short Makefiles.
- Preserved exact legacy figures, tables, regressions, and other generated artifacts under `tasks/reproduce_legacy_outputs/output/legacy_exact` with SHA-256 checks in the manifest.
- Excluded legacy source scripts from the exact-output copy task so the reorganized production code remains Python-only.

### Result
- The rebuilt Python datasets match the legacy Stata-derived outputs exactly for `MMB_IRF_format.dta`, `MMB_IRF_format_full.dta`, and `MMB_reg_format.dta`.
- The legacy generated artifacts were copied bit-for-bit into the organized task output, and the archive task inventoried the remaining legacy tree.
- The Python cloud graph task generates 48 inspectable PDF figures with plain-text description files; these are Python redraws, while exact legacy figure files remain preserved separately.

### Interpretation
- In the initial exact-parity build, the import task used `Model_Characteristics_safecopy.xlsx` as the model-characteristics source because the current `Model_Characteristics.xlsx` was missing author entries that appeared in the legacy derived outputs.
- The legacy real-rate construction sets the final period in each model-rule group to zero after a lead-inflation calculation and Stata collapse; this was reproduced for parity, but it may affect peak/timing/sign-change variables.
- Sacrifice-ratio files are carried through from the legacy derived outputs after a visible Python reconstruction step because recomputing them from the raw CSV exports differed only at Stata/Python floating-point precision, which was enough to break exact equality.
- The legacy code contains a mix of generated artifacts and source code in the same folders; the new structure separates exact archived artifacts from newly generated Python outputs.

### Next step
- Use `make -C tasks/build_mmb_analysis_dataset/code` for rebuilt datasets, `make -C tasks/generate_mmb_cloud_graphs/code` for Python redraws, and `make -C tasks/reproduce_legacy_outputs/code` when exact legacy artifact copies are needed downstream.

## 2026-04-28

### Task
- Switched the main model-characteristics feed-in from the safecopy workbook to the corrected workbook.

### What I did
- Updated `tasks/import_mmb_legacy_data` so `output/model_characteristics.xlsx` links to `legacy/mmb_upgraded/data/raw/Model_Characteristics_corrections.xlsx`.
- Regenerated the import metadata and rebuilt `tasks/build_mmb_analysis_dataset` from the corrected workbook.
- Confirmed that both workbooks have the same 92 production model rows before the `DROP BELOW` section, so the existing production-row cutoff still selects the intended model block.

### Result
- `MMB_IRF_format.dta` still matches the legacy derived output exactly because it does not depend on model-characteristics attributes.
- `MMB_IRF_format_full.dta` and `MMB_reg_format.dta` now intentionally fail parity against the old legacy derived outputs in corrected model-attribute columns: `wlth`, `bnkcrdit`, `gov_spend`, `tax`, `gov_debt`, and `fiscal`.

### Interpretation
- The parity break is expected and comes from using corrected economic codings rather than the safecopy values used by the old legacy outputs.
- The exact legacy generated artifacts remain preserved under `tasks/reproduce_legacy_outputs` for reference, but the main analysis-data build now reflects the corrected model characteristics.

### Next step
- Treat the updated parity report as a diagnostic against the old legacy outputs rather than as a required exact-match target for corrected model-characteristics columns.

## 2026-05-28

### Task
- Created `tasks/classifying_v2` to audit model-characteristic codings with Gemini 3.1 Pro.

### What I did
- Added a production task that uploads native PDFs from `SamplePapers`, creates one Gemini Context Cache per model/PDF, and asks the audit questions with ordinary cached `generate_content` calls.
- Added reusable Gemini parameters to `config/params.yaml`, including model name, cache TTL, output-token limit, request pause, and pilot-run model cap.
- Added explicit Gemini thinking configuration and renamed the Google Search toggle to cover external metadata questions beyond central-bank authors.

### Result
- The task writes discrepancy-only rows to `model_audit.csv`, all parsed answers to `gemini_all_answers.csv`, and cache/raw-response metadata to inspectable CSV/JSONL files.

### Interpretation
- Batch API was removed because this workflow needs Context Caching. The model-to-PDF manifest now covers all 92 workbook models and the confirmed renamed PDFs in `SamplePapers`.

### Next step
- Install `google-genai`, set `GEMINI_API_KEY` or `GOOGLE_API_KEY`, optionally set `max_models_per_run` for a pilot, then run `make -C tasks/classifying_v2/code run`.

### Update
- Added retry parameters for transient Gemini `generate_content` failures after a 503 API outage interrupted a cached run. The run remains resumable from `progress.log`.

### Update
- Raised the classifying_v2 Gemini output-token cap and added a rerun pass for prior `UNCLEAR` rows after discovering truncated JSON prefixes with clear answers. The rerun pass removes old unclear rows and dependent child answers before resuming so corrected answers replace parser artifacts rather than duplicating them.

## 2026-06-04

### Task
- Added an LLM-corrected model-characteristics workbook for downstream analysis.

### What I did
- Added `tasks/classifying_v2/code/apply_llm_corrections_to_workbook.py` to apply `model_audit.csv` discrepancies to the first 92 rows of `Model_Characteristics_corrections.xlsx`.
- Normalized corrected values for downstream parsing: central-bank author percentages are stored as decimal shares, booleans as Excel booleans, estimate quarters as `YYYYQ#`, and known category spellings as labels used by the analysis dataset build.
- Wired `tasks/build_mmb_analysis_dataset` to consume `Model_Characteristics_corrections_llm.xlsx`.

### Result
- The original first-sheet layout is preserved, corrected cells carry comments with the raw LLM explanation, and an `LLM_Corrections_Log` sheet records each applied change.

### Update
- Replaced the copy-only measurement and paper tasks with Python production builders that read the MMB analysis dataset from task `input/` symlinks and generate their own outputs.
- Added companion notebooks beside the Python scripts for `lasso`, `disentangle_spaghetti`, `outcome_coef_plots`, `timing_coef_plots`, `stepwise_regressions`, `paper_tables`, and `table11`.
- Removed the stale exact-output manifests and legacy-output copy dependencies from those task Makefiles.

### Update
- Restructured generated notebooks into multiple setup/helper/output cells instead of single large code cells.
- Removed generated `main()` wrappers and Python type annotations from the measurement and paper builders.
- Replaced the remaining non-legacy copy-only tasks for output cloud graphs, interactions with rules, and summary stats with Python builders that generate outputs from task inputs.

## 2026-06-12

### Update
- Updated `tasks/data/classifying_v2/input/model_paper_files.csv` to point several models to newly supplied paper PDFs where filenames indicated corrected source versions: ACEL, CGG02, GM07, JO15_ht, MPT10, RE09, and YR13 variants.

## 2026-06-17

### Update
- Replaced the old three-channel analysis variables (`ntwrth`, `wlth`, `bnkcrdit`) with the classifying_v2 channel schema: `firm_bs`, `bank`, `hh_demand`, and `labor_frict`.
- Removed the legacy parity report from `build_mmb_analysis_dataset` because the analysis dataset now intentionally diverges from the legacy column schema.

### Update
- Removed manuscript-table production from the `tasks/paper/` workstream and split it into measurement tasks by empirical exercise: policy rules and estimation, nominal rigidities, real rigidities, nonmodel attributes, broad model variables, and Table 11 specifications.
- Moved the table outcome lists, sample restriction, labels, and variable specifications into `config/params.yaml` so the new tasks do not hardcode the main empirical table choices.

### Update
- Moved the summary-statistics task from `tasks/quantitative/summary_stats` to `tasks/measurement/summary_stats` because the Table 3-style summary statistics are a measurement artifact from the constructed analysis data.
- Updated the moved task's Makefile to recurse into `build_mmb_analysis_dataset`, symlink the constructed regression dataset through `input/`, and enumerate the table and histogram outputs explicitly.

### Update
- Changed `tasks/measurement/summary_stats` so its main stable table output is `table3_summary_stats.tex`, a manuscript-formatted LaTeX table for the constructed data.
- The Table 3 summary table uses observations with output and inflation timing below 60 quarters, then reports full-sample, calibrated-model, and estimated-model panels for the h=20 outcome variables and timing measures.

### Update
- Added `table4_elasticity_stats.tex` and `table4_elasticity_stats.csv` to `tasks/measurement/summary_stats` for the macroeconomic elasticity summary table by policy rule.
- Switched manuscript summary-table skewness calculations to population skewness, matching the existing full-sample Table 3 and Table 4 values.

### Update
- Confirmed `estimated` and `calibrated` are exact complements for nonmissing MMB analysis observations, so they are collinear with an intercept.
- Removed `calibrated` from the LASSO fixed-effect residualization controls and rebuilt the LASSO outputs/notebook with `rule_itr`, `rule_g`, and `estimated` as the fixed-effect columns.

### Update
- Added a model-name replacement for the `US_FMS134` typo so MMB analysis outputs use the corrected model code `US_FMS13`.
- Rebuilt the analysis dataset and downstream generated outputs that consume `MMB_reg_format.dta` or `MMB_IRF_format_full.dta`.

### Update
- Added `table5_timing_stats.tex` and `table5_timing_stats.csv` to `tasks/measurement/summary_stats` for the timing-of-peak-outcomes summary table by policy rule.
- The table uses the same timing-restricted sample and population skewness convention as the manuscript-formatted Tables 3 and 4 outputs.

### Update
- Added manuscript-formatted Table 6 outputs to `tasks/measurement/policy_rules_estimation` for both the full sample and the estimated-model subsample.
- The Table 6 diagnostics report ordinary R-squared statistics for elasticity columns, GLM residual pseudo-R-squared statistics for timing columns, robust weighted R-squared for elasticity columns, and residual standard errors from the production fits.

### Update
- Added `citation_weight_as_of: "2026-02"` to `config/params.yaml` and promoted citation-weight variables into `tasks/data/build_mmb_analysis_dataset/output/MMB_reg_format.dta`.
- Added citation-weighted Table 6 outputs to `tasks/measurement/policy_rules_estimation`; weights are age-adjusted citations per year, log-transformed, and renormalized to mean one within each regression sample.

### Update
- Added manuscript-formatted Table 7 outputs to `tasks/measurement/nominal_rigidities` for both the full sample and the estimated-model subsample.
- Added citation-weighted Table 7 counterparts using the same age-adjusted, log-transformed citation weights, renormalized to mean one within each regression sample.

### Update
- Updated the real-rigidity regression spec to use constrained household demand, firm balance sheet, bank lending, labor friction, open economy, and all pairwise interaction candidates among those variables.
- Added manuscript-formatted and citation-weighted Table 8 outputs to `tasks/measurement/real_rigidities`; interaction rows are rendered only when identified in at least one outcome for the relevant sample.

### Update
- Changed the Table 6, Table 7, and Table 8 regression tasks so reported standard errors are clustered by MMB model for both unweighted and citation-weighted regressions.
- Added `cluster_var: "model"` to `config/params.yaml`; robust least-squares elasticity columns use model-clustered score covariance from the converged RLM weights, and timing GLMs use model-clustered covariance directly.

### Update
- Added manuscript-formatted and citation-weighted Table 9 outputs to `tasks/measurement/nonmodel_attributes` for both the full sample and the estimated-model subsample.
- Updated the nonmodel-attribute specification to use central-bank authorship, log number of equations, middle/late vintage indicators, and the central-bank-authors by late-vintage interaction, avoiding raw estimation-window variables that restrict the full sample to estimated models.

### Update
- Added manuscript-formatted and citation-weighted Table 10 outputs to `tasks/measurement/broad_model_variables` for both the full sample and the estimated-model subsample.
- Updated the broad model-variable specification to use the current channel variables: constrained household demand, firm balance sheet, bank lending, labor friction, open economy, their pairwise interactions, nominal rigidity variables, and the nonmodel attributes used in Table 9.

### Update
- Extended `tasks/measurement/lasso` to write printable post-selection regression tables for unweighted and citation-weighted LASSO screens.
- The post-selection refits include policy-rule and estimated-model controls and report standard errors clustered by model; the citation-weighted screen and refits use normalized citation weights within each outcome sample.

### Update
- Changed the LASSO screen in `tasks/measurement/lasso` from CV-minimum penalized prediction models to a Belloni-Chernozhukov-style feasible LASSO with iterated heteroskedastic penalty loadings.
- The LASSO task still reports post-selection refits with model-clustered standard errors and now records the theory penalty level and sklearn-equivalent penalty in the zeroed-summary outputs.

### Update
- Set the feasible-LASSO screening multiplier in `tasks/measurement/lasso` to 0.5 after the canonical multiplier selected the empty model for all outcomes.
- The multiplier is recorded in `lasso_metadata.json` and in the LaTeX table notes so alternative penalty conservativeness can be tested explicitly.

### Update
- Updated `tasks/data/build_mmb_analysis_dataset` so sacrifice ratios are rebuilt only from raw sacrifice-ratio CSVs and no longer fall back to legacy derived `.dta` files.
- Real-rate endpoints without next-quarter inflation are now left missing, and cumulative real-rate outcomes are missing when a horizon includes such missing terminal values.

### Update
- Updated `tasks/measurement/disentangle_spaghetti` IRF archetype clustering to exclude `rrate`, since real rates are a lagged linear combination of nominal rates and inflation.
- Added functional-PCA, Ward hierarchical-clustering, and Gaussian-mixture archetype checks, then regenerated the disentangling report with markdown tables and section-level interpretation notes for the June 18 MMB analysis dataset.

### Update
- Added `ward_archetype_summary.png` and a companion description file to `tasks/measurement/disentangle_spaghetti`.
- The figure visualizes Ward archetype geometry, cluster outcome means, and mean `y`, `piq`, and `irate` paths for the rrate-free archetype analysis.

### Update
- Removed the obsolete `tasks/measurement/table11_specifications` task because the current attached manuscript has no Table 11 and the task only reproduced stale alternate broad-specification outputs.
- Removed the unused `table11_specs` block from `config/params.yaml`; the active broad model-variable outputs remain in `tasks/measurement/broad_model_variables`.

### Update
- Updated `tasks/measurement/summary_stats` so the tables, by-rule CSV, and timing histograms all use the same main summary-statistics sample excluding observations with `y_timing_max >= 60` or `piq_timing_max >= 60`.
- Switched the summary-stats Makefile to a phony all-or-nothing build because the script recreates the whole `summarystats/` directory and partial output deletion should trigger regeneration rather than a failed existence check.

### Update
- Updated `config/params.yaml` so the shared MMB timing cutoff is 99 quarters, and changed regression-table loading and summary statistics to use that single cutoff.
- Updated `tasks/measurement/policy_rules_estimation` to rebuild all outputs together, clear stale output artifacts before regeneration, and describe timing regressions as Poisson with a negative-binomial fallback when overdispersion is detected.

### Update
- Updated `tasks/measurement/nominal_rigidities` so its Makefile rebuilds all jointly produced outputs together, its clean target works from a partially deleted task directory, and `main.py` clears stale output artifacts before regeneration.
- Updated the nominal-rigidities Table 7 notes to describe timing regressions as Poisson with a negative-binomial fallback and to state the estimated-model control only for the full-sample table.

### Update
- Updated `tasks/measurement/real_rigidities` so the estimated-model appendix uses a main-effects-only real-rigidity specification while the full-sample table keeps the all-pairwise specification.
- Added real-rigidity support and dropped-term diagnostics, blanked displayed coefficients with fewer than three supporting models, and updated Table 8 notes to describe Poisson timing regressions with a negative-binomial fallback.

### Update
- Updated `tasks/measurement/rhs_stats` to compute model-attribute averages from the final `MMB_reg_format.dta` model universe rather than the broader pre-curation `rhs.dta` file.
- The RHS-stats task now rebuilds its jointly produced outputs together, clears stale output artifacts before regeneration, and validates that model-level attributes are constant across policy-rule rows before collapsing to one row per model.

### Update
- Updated `tasks/measurement/nonmodel_attributes` so its jointly produced Table 9 outputs rebuild together, stale output artifacts are cleared before regeneration, and the manifest lists itself.
- Clarified that Table 9 covers central-bank authorship, model size, and model vintage, not estimation-sample indicators, and corrected the timing-regression and estimated-model-control notes.

### Update
- Updated `tasks/measurement/broad_model_variables` so the full-sample Table 10 keeps all pairwise real-channel interactions, while the estimated-model appendix uses a simpler main-effects broad specification to avoid sparse-cell interaction estimates.
- Added Table 10 support and dropped-column diagnostics, suppressed displayed coefficients with fewer than three supporting models, and corrected timing-regression and estimated-model-control notes.

### Update
- Updated `tasks/measurement/lasso` so elasticity outcomes use the residualized feasible square-loss LASSO screen while timing outcomes use a Poisson L1 screen with paper controls unpenalized.
- Added outcome-specific sparse-feature drops, post-selection refit collinearity diagnostics, and Poisson/negative-binomial timing refits using the same overdispersion logic as the main regression tables.

### Update
- Added `tasks/measurement/model_vs_rule_variance_decomposition` and `tasks/measurement/cross_rule_rank_stability` as independent production measurement tasks using the canonical `MMB_reg_format.dta` paper regression sample.
- The new tasks recompute model-versus-rule fixed-effect variation and cross-rule model-rank stability directly from the canonical data, with manifests, paper-language findings notes, and figure metadata.

## 2026-06-25

### Update
- Added `tasks/measurement/rhs_stats` to produce a model-level RHS attribute table from `rhs.dta`, including the current four channel indicators and estimated-model-only estimation-sample rows.

### Update
- Updated `tasks/measurement/disentangle_spaghetti` driver regressions to use model-clustered inference for elasticities, Poisson/negative-binomial timing GLMs with the paper overdispersion rule, and a five-model support screen for headline significant panel drivers.
- Switched diagnostic cross-validation to model-grouped folds, renamed timing-based archetype stability labels, moved GMM checks to diagonal covariance, and added manifest, sparse-significance, and dropped-collinearity diagnostics.

### Update
- Updated `tasks/measurement/model_vs_rule_variance_decomposition` to validate one row per model-rule observation after filtering and to use the shared timing cutoff as an upper bound.
- Kept the model-to-rule incremental ratio in the CSV but removed it from the paper-facing LaTeX table to avoid distracting ratio values when the rule increment is mechanically near zero.
