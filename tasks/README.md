# Tasks

`tasks/` contains production work.

Top-level folders are workstreams, not rigid stages.
Add new workstreams if the project needs them.

Each task should be an economically meaningful unit, not a junk drawer.

## Current Tasks

- `import_mmb_legacy_data/`: links immutable MMB source inputs from the legacy archive into task outputs.
- `build_mmb_analysis_dataset/`: rebuilds the IRF panel and regression-format dataset in Python and reports parity against the legacy derived datasets.
- `generate_mmb_cloud_graphs/`: regenerates cloud graphs from the rebuilt IRF panel in Python.
- `reproduce_legacy_outputs/`: preserves exact legacy figures, tables, regression outputs, and robustness artifacts under the task structure.
- `archive_legacy_artifacts/`: inventories remaining legacy files and records their disposition.
