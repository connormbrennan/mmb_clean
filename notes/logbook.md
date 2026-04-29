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
