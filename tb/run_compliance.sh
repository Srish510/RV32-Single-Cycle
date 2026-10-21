#!/usr/bin/env bash
# Runs the official RISC-V RV32I Architectural Compliance Test Suite.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJ_ROOT"
python tb/run_compliance.py
