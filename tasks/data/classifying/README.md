# Model Classification Inputs

This task holds the hand-maintained model-characteristics workbook and paper-map inputs used by `tasks/data/classifying_v2/`.

The files are manual source inputs. The Makefile exposes them through `output/` symlinks so downstream tasks can depend on a standard task output location.

## Inputs

- `input/Model_Characteristics_corrections.xlsx`
- `input/mmb_model_paper_map.md`
- `input/model_audit_manual.csv`
- `input/progress.log`

## Outputs

- `output/Model_Characteristics_corrections.xlsx`
- `output/mmb_model_paper_map.md`
- `output/model_audit_manual.csv`
- `output/progress.log`

## Run

From `tasks/data/classifying/code/`:

```sh
make
```
