#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/new_workstream.sh evidence
#
# Creates:
#   tasks/evidence/

WORKSTREAM="${1:-}"

if [[ -z "$WORKSTREAM" ]]; then
  echo "Usage: bash scripts/new_workstream.sh <workstream_name>"
  exit 1
fi

TARGET="tasks/$WORKSTREAM"

if [[ -e "$TARGET" ]]; then
  echo "Error: '$TARGET' already exists."
  exit 1
fi

mkdir -p "$TARGET"

cat > "$TARGET/README.md" <<WORKSTREAMREADME
# $WORKSTREAM

Describe what belongs in this workstream.

Examples:
- reusable construction tasks
- mechanism-testing tasks
- model solution tasks
- paper-facing output tasks
WORKSTREAMREADME

echo "Created $TARGET"
