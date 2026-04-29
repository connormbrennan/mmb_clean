#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/new_task.sh <workstream> <task_name> [python|julia]
#
# Examples:
#   bash scripts/new_task.sh measurement construct_novelty_index
#   bash scripts/new_task.sh model solve_baseline julia
#
# This creates:
#   tasks/<workstream>/<task_name>/
#     input/
#     code/
#     output/
#     README.md
#     Makefile
#
# Philosophy:
# - one economically meaningful task
# - not a junk drawer
# - not an overbuilt mini-software-package

PROJECT_DEFAULT_LANG="python"

WORKSTREAM="${1:-}"
TASK_NAME="${2:-}"
TASK_LANG="${3:-$PROJECT_DEFAULT_LANG}"

if [[ -z "$WORKSTREAM" || -z "$TASK_NAME" ]]; then
  echo "Usage: bash scripts/new_task.sh <workstream> <task_name> [python|julia]"
  exit 1
fi

if [[ "$TASK_LANG" != "python" && "$TASK_LANG" != "julia" ]]; then
  echo "Error: task language must be 'python' or 'julia'."
  exit 1
fi

if [[ ! -d "tasks/$WORKSTREAM" ]]; then
  echo "Error: workstream 'tasks/$WORKSTREAM' does not exist."
  echo "Create it first with:"
  echo "  bash scripts/new_workstream.sh $WORKSTREAM"
  exit 1
fi

TASK_DIR="tasks/$WORKSTREAM/$TASK_NAME"

if [[ -e "$TASK_DIR" ]]; then
  echo "Error: '$TASK_DIR' already exists."
  exit 1
fi

mkdir -p "$TASK_DIR/input" "$TASK_DIR/code" "$TASK_DIR/output"
touch "$TASK_DIR/input/.gitkeep" "$TASK_DIR/output/.gitkeep"

cat > "$TASK_DIR/README.md" <<TASKREADME
# $TASK_NAME

## Purpose
State clearly what this task does.

## Inputs
List the economic or data objects used here.

## Outputs
List the files this task creates.

## Notes
Anything important for future-you.
TASKREADME

cat > "$TASK_DIR/Makefile" <<'TASKMAKE'
SHELL := /bin/bash
.RECIPEPREFIX := >

.PHONY: all clean

# Example pattern:
#
# all: ../output/example.csv
#
# ../output/example.csv: code/main.py ../input/raw_data.csv | ../output
# > python3 code/main.py
#
# Or for Julia:
#
# ../output/example.csv: code/main.jl ../input/raw_data.csv | ../output
# > julia code/main.jl

all:
> @echo "Define explicit outputs and recipes for this task."

../output:
> mkdir -p ../output

clean:
> rm -f ../output/*
> touch ../output/.gitkeep
TASKMAKE

if [[ "$TASK_LANG" == "python" ]]; then
  cat > "$TASK_DIR/code/main.py" <<'PYEOF'
"""
Purpose:
Inputs:
Outputs:
Run:
  python3 code/main.py
"""

from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = TASK_ROOT / "input"
OUTPUT_DIR = TASK_ROOT / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

print("Replace this starter script with task-specific code.")
PYEOF
fi

if [[ "$TASK_LANG" == "julia" ]]; then
  cat > "$TASK_DIR/code/main.jl" <<'JLEOF'
# Purpose:
# Inputs:
# Outputs:
# Run:
#   julia code/main.jl

println("Replace this starter script with task-specific code.")
JLEOF
fi

echo "Created $TASK_DIR"
