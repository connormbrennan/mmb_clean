# AGENTS.md

Repository-specific instructions for AI coding agents.

## Objective

Help with economics and finance research while preserving a workflow that is:
- simple
- inspectable
- reproducible
- easy for a researcher, not a software engineer, to debug

## Non-negotiable coding rules

- Prefer plain scripts over architecture
- Do not introduce classes unless explicitly requested
- Do not create helper modules unless reused across multiple tasks
- Do not create nested orchestration systems
- Do not create controller scripts that just call other scripts unless explicitly asked
- Do not over-engineer
- Prefer one economically meaningful task per script
- Use relative paths only
- Do not hardcode important parameters inside scripts
- Put reusable parameters in `config/params.yaml`
- Keep code easy to read and modify manually
- Add comments to code and functions with steps to explain intuition. Not long docstrings but state what and why. 
- Write procedural scripts that read top-to-bottom, with intermediate values visible at each step. Extract a function only when the same logic is called from two or more places — never for organization, readability, or single-use wrappers.



## Python-specific rules

- Do not add `if __name__ == "__main__":` unless explicitly requested
- Do not wrap straightforward research code in unnecessary functions
- Prefer pandas / numpy / statsmodels directly
- Avoid framework-style abstractions
- Make every script anchor paths off of __file__ so as to make both make and the Python debugger work fine

## Julia-specific rules

- Keep scripts flat and readable
- Avoid turning everything into a package unless explicitly requested
- Keep model-solving code transparent and easy to edit

## Task structure

Production work lives in `tasks/`.

Each production task should contain:
- `input/`
- `code/`
- `output/`
- `README.md`
- `code/Makefile`

Agents should assume the task is run from `tasks/<task_name>/code/`.

Exploratory work lives in `scratch/` and should not be treated as stable production code.

## Task philosophy

A task should do one economically meaningful thing.

Good examples:
- build firm-patent panel
- estimate event study
- construct novelty measure
- solve baseline model
- produce calibration targets
- generate figure 2

Bad examples:
- analysis1
- regressions
- misc
- final_stuff

## Output discipline

- Every stable artifact used downstream should be a file produced by some task in `output/`.
- This includes datasets, tables, figures, calibration targets, regression outputs, and any numbers that will later be cited in notes or papers.
- Do not hardcode stable results in manuscripts or notes when they can be produced by code.

## Data handling

- Do not use a global `data/raw/` folder as the default source of production dependencies in task code.
- Immutable source data should enter the workflow through a dedicated source-data task (for example `tasks/download_data/` or `tasks/import_<source>/`) or another explicitly designated source location.
- Tasks that build datasets write to their own `output/`.
- If a derived dataset is used by multiple downstream tasks, give it its own build task.
- Downstream tasks should consume upstream artifacts via symbolic links placed in `input/` that point to another task’s `output/`; do not copy files between tasks.
- Do not scatter stable production data files outside of `tasks/*/output/` or explicitly designated source-data locations.
- Document data sources and access instructions in the producing task `README.md` and, if helpful, in `data/README.md`.

## Script header convention

- Script headers are descriptive only; the Makefile is the source of truth for exact file-level dependencies.

At the top of each script, include:
- purpose
- inputs
- outputs
- run instructions

## Makefile conventions

- The Makefile for a task lives at `tasks/<task>/code/Makefile`.
- Makefiles should stay short and readable.
- The first target should usually be `all`.
- Declare concrete output files explicitly.
- On the left of `:` put the file to be built; on the right put the exact scripts and upstream files it depends on.
- Use order-only prerequisites (`|`) for directories such as `../input` and `../output`.
- Create `input/` and `output/` if needed.
- Use symbolic-link rules (`ln -s`) to connect downstream `input/` files to upstream `output/` files.
- Prefer one economically meaningful output per rule when practical.
- Recipes must begin with a tab.
- Use Make for stable production dependencies, not exploratory one-offs.

## File movement and restructuring

- Do not rename or move large parts of the repo unless explicitly instructed
- Do not change directory structure gratuitously
- Do not delete files unless explicitly instructed or clearly temporary

## Change discipline

- Prefer the smallest correct edit
- Preserve existing workflow unless told to redesign it
- When adding a stable new result or object, put it in a task
- Log to `notes/logbook.md` when: creating a new task, changing `config/params.yaml`, making a methodological choice that affects results, or dropping/transforming data in a non-obvious way. One or two sentences is enough.

## Things agents must not do

- Do not install packages without asking first
- If a new dependency is required, add it to the repository’s environment-management task or files first (for example `tasks/setup_environment/`, `requirements.txt`, `Project.toml`, or `Manifest.toml`) and ask before actually running package-manager commands.
- Do not refactor working code while fixing a bug
- Do not add logging, error handling, or CLI argument parsing unless requested
- Do not create wrapper scripts that add indirection without value
- Do not split a working script into multiple files for "cleanliness"
- Do not rewrite code to be "more Pythonic" or "more idiomatic" when it already works
- Do not add type hints, docstrings, or tests unless explicitly asked
- Do not invent metrics or proxy variables unless explicitly asked

## Version control

- Do not run any git commands unless explicitly asked
- Do not create branches, commit, or push
- Do not modify `.gitignore` without asking
- Assume the researcher manages version control manually

## Reproducibility for models and simulations

- Store random seeds in `config/params.yaml`; do not use global random state
- Document the solution algorithm (e.g., VFI, shooting) in the task README
- Log simulation parameters and versions to `notes/logbook.md`
- Do not overwrite a working simulation script without creating a new task or documenting the change
- Prefer deterministic tie-breaking when sorting or selecting from simulated outcomes
- Calibration targets should come from a dedicated build task or be computed as part of the task with a clear procedure

## Output metadata

Binary outputs are not directly readable by text-based review tools.
Every binary file in `output/` should have a companion plain-text metadata file.

- Datasets (`.parquet`, `.dta`, `.pkl`, etc.): write `<filename>_codebook.txt` containing row/column counts, column names and dtypes, a sample of the first 5–10 rows, any filters applied, and time coverage.
- Figures (`.png`, `.pdf`, `.svg`): write `<filename>_description.txt` containing what the figure shows, axis labels/units, data source, and key takeaways.
- Estimation results saved as binary: write a plain-text summary with the specification, key coefficients, sample size, and fixed effects.
- Metadata files should be produced by the same script that produces the binary output and listed as Makefile targets.
- Do not require metadata for scratch/exploratory outputs.
