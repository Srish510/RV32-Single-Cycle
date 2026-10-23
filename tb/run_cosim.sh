#!/usr/bin/env bash
# Shell script to execute RV32I Lockstep Co-Simulation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="${PYTHON:-python3}"

exec "$PYTHON_EXEC" "$SCRIPT_DIR/run_cosim.py" "$@"
