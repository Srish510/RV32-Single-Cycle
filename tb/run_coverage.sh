#!/usr/bin/env bash
# Runs the complete RV32I Coverage & Verification Closure Suite.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJ_ROOT"
python tb/run_coverage.py "$@"
