# AGENTS.md

Repository-specific instructions for AI coding agents.

## Objective

Help with economics and finance research while preserving a workflow that is:
- simple
- inspectable
- reproducible
- easy for a researcher, not a software engineer, to debug

## Non-negotiable coding rules

- Initiate new tasks using `bash scripts/new_task.sh <category> <task> python`
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

## Makefile dependency discipline

Every production task must have this structure:

- `tasks/<category>/<task>/Makefile`
- `tasks/<category>/<task>/code/Makefile`
- `tasks/<category>/<task>/input/.gitkeep`
- `tasks/<category>/<task>/output/.gitkeep`

The root `Makefile` is only a wrapper:

```make
SHELL := /bin/bash

.PHONY: all clean

all:
	$(MAKE) -C code all

clean:
	$(MAKE) -C code clean
```

The `code/Makefile` does the real work. It must recurse into every direct upstream task so that staleness propagates transitively through the DAG, but it must use ordinary file-mtime dependencies for the local Python step so that step only runs when its inputs are genuinely newer than its outputs:

```make
SHELL := /bin/bash

.PHONY: all clean FORCE
.NOTPARALLEL:

all: ../output/downstream_file.parquet

clean:
	rm -f ../output/downstream_file.parquet
	rm -f ../input/upstream_file.parquet

FORCE:

# Why FORCE here:
#   Make cannot tell whether upstream is stale without recursing — the
#   upstream output file's mtime alone does not reflect changes to
#   upstream's *source code* or upstream's *own* upstream tasks. So we
#   always recurse into the direct upstream(s). This is cheap: when
#   upstream is up to date the recursive call is just a few stat()s and
#   prints "Nothing to be done", and crucially it does NOT touch the
#   upstream output file's mtime. Only if upstream actually rebuilds
#   does the file get a new mtime, which then propagates downstream
#   through the ordinary prerequisite below.
#
# --no-print-directory keeps the recursion quiet when nothing happens.
../../upstream_task/output/upstream_file.parquet: FORCE
	$(MAKE) --no-print-directory -C ../../upstream_task
	test -f $@

../input/upstream_file.parquet: ../../upstream_task/output/upstream_file.parquet | ../input
	ln -sfn ../../upstream_task/output/upstream_file.parquet $@

# This recipe runs ONLY when main.py or the (symlinked) input file is
# actually newer than the output. The FORCE above triggers recursion,
# not rebuilds — recursion that finds nothing to do leaves mtimes alone,
# so this rule stays a no-op until something genuinely changes.
../output/downstream_file.parquet: main.py ../input/upstream_file.parquet | ../output
	python3 main.py
	test -f $@

../input ../output:
	mkdir -p $@
```

If a task has multiple direct upstreams, give each one its own `FORCE`-gated rule and its own symlink. Do not coalesce them into one rule; you want Make to recurse into each upstream independently so a change in any branch of the DAG propagates correctly.

Adjust relative paths as needed. The important requirements are:

- A downstream `input/` file must be a symbolic link to an upstream `output/` file.
- The Makefile must have a rule for each upstream output file with `FORCE` as a prerequisite, whose recipe calls `$(MAKE) --no-print-directory -C <upstream_task>`. This is the mechanism for transitive staleness: each level of the DAG recurses into its parents, and the recursion is a cheap no-op when nothing is stale.
- The `test -f $@` line in that rule is a guardrail — it makes the build fail loudly if the upstream Makefile claims success but did not actually produce the expected file.
- The downstream output must depend on the symlinked `../input/...` file **and** on `main.py` (plus any other local source files). This is the rule whose mtime check decides whether `python3 main.py` actually runs.
- Directory targets such as `../input` and `../output` must be order-only prerequisites after `|`, so the directory's mtime does not invalidate downstream targets.

Multiple outputs from a single script:

If a script produces multiple outputs, do not put all jointly produced files on the left side of one ordinary rule. Use one primary output, or a stamp file, and make the companion outputs depend on it:

```make
PRIMARY_OUTPUT := ../output/main_dataset.parquet

SECONDARY_OUTPUTS := \
	../output/main_dataset_codebook.txt \
	../output/main_dataset_manifest.json

OUTPUTS := $(PRIMARY_OUTPUT) $(SECONDARY_OUTPUTS)

all: $(OUTPUTS)

$(PRIMARY_OUTPUT): main.py ../input/source.parquet | ../output
	python3 main.py
	test -f $(PRIMARY_OUTPUT)
	test -f ../output/main_dataset_codebook.txt
	test -f ../output/main_dataset_manifest.json

# Companions are produced by the same script; they just need to exist.
$(SECONDARY_OUTPUTS): $(PRIMARY_OUTPUT)
	test -f $@
```

Validation:

Before finishing any task-structure or Makefile change, agents must validate with:

```
make -n -C tasks/<category>/<task> all
```

Run it twice in succession with no source changes in between. The first call may show the recursive `$(MAKE)` invocations into upstream tasks — that is expected and correct. **What must not appear on the second call is the local `python3 main.py` line, or any upstream task's `python3` line.** If a Python invocation shows up when nothing has changed on disk, some rule has a phony or always-stale ordinary prerequisite (for example, `FORCE` accidentally listed on the Python rule itself, or a directory used as an ordinary prerequisite instead of order-only) and must be fixed.

For changes affecting upstream/downstream relationships, also run `make -n` on at least one downstream task that consumes the changed output. Do not run expensive data pulls or WRDS jobs unless explicitly asked; use `make -n` for dependency validation when execution would be costly.