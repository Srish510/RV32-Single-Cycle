#!/usr/bin/env bash
# Bash Wrapper for RV32I Formal Verification Suite (SymbiYosys + RVFI)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/run_formal.py" "$@"
