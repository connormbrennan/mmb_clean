# Model Classification Audit with Gemini Context Caching

This task audits `Model_Characteristics_corrections.xlsx` against Gemini 3.1 Pro's reading of the native model PDFs. The default API model ID is `gemini-3.1-pro-preview`.

The workflow is:

1. Upload each model PDF to Gemini Files API.
2. Create one explicit Context Cache per model/PDF.
3. Ask the 17 parent audit questions sequentially with ordinary `generate_content` calls, each referencing the relevant cache.
4. Ask sticky-price, sticky-wage, indexation, and estimation-date follow-ups only when the parent answer is `True`.
5. Log discrepancies to `output/model_audit.csv` and all parsed answers to `output/gemini_all_answers.csv`.

The task intentionally does not use Gemini Batch API because Batch API and Context Caching cannot be combined for this workflow.

Run from `tasks/data/classifying_api/code/`:

```sh
make status
make run
```

`make run` resumes from `output/progress.log`, so interrupted runs do not repeat completed model-question pairs.
Use `make reset` or `make clean-output` before rerunning after prompt or comparison-rule changes.

## Inputs

- `input/Model_Characteristics_corrections.xlsx`: baseline model-characteristics workbook.
- `input/mmb_model_paper_map.md`: model-to-paper source map.
- `input/model_paper_files.csv`: explicit model-to-PDF manifest.
- `input/papers`: symlinked by the Makefile to `SamplePapers/`.
- `../../../../config/params.yaml`: Gemini model, temperature, cache TTL, output-token limit, file-processing timeout, and related run parameters.

The script fails before calling Gemini if a workbook model is missing from the manifest, a manifest model is absent from the workbook, a model appears twice, a referenced PDF is missing, or a referenced PDF exceeds 50MB.

## Required Environment

Set one of:

```sh
export GEMINI_API_KEY="..."
```

or:

```sh
export GOOGLE_API_KEY="..."
```

The Python environment must have Google's SDK:

```sh
python3 -m pip install -r ../requirements.txt
```

The task does not require pandas or openpyxl; the script reads the workbook directly from the `.xlsx` XML to keep the dependency surface narrow.

Google Search grounding is enabled for external-metadata questions: `CB_Authors`, `Date_Pub`, `Working_Paper`, and `Published`.

## Outputs

- `output/model_audit.csv`: discrepancy rows only, with columns `model`, `variable`, `right_coding`, `explanation`.
- `output/gemini_all_answers.csv`: every parsed Gemini answer and comparison status.
- `output/gemini_raw_responses.jsonl`: raw response text and usage metadata.
- `output/cache_manifest.csv`: uploaded file names and cache names by model.
- `output/progress.log`: append-only resume/progress trace.
- `output/classifying_api_run_summary.txt`: latest status or run summary.
- `output/Model_Characteristics_corrections_llm.xlsx`: the first-sheet model-characteristics workbook with Gemini discrepancy corrections applied in-place, plus an `LLM_Corrections_Log` sheet.
- `output/Model_Characteristics_corrections_llm_summary.txt`: metadata for the corrected workbook output.

After `model_audit.csv` exists, build the corrected workbook with:

```sh
make corrections-workbook
```

## Current Manifest Status

The substantive paper mappings for `G7_TAY93`, `NK_GK09lin`, `NK_JO15_ht`, `US_FRB03`, `US_MI07AL`, and `US_YR13AL` were confirmed by the user on 2026-05-28.

The manifest currently covers all 92 workbook models with zero missing local PDF references.

Also decide whether the first paid API run should include all 92 workbook models or a pilot subset. Use `max_models_per_run` in `config/params.yaml` for a pilot.
