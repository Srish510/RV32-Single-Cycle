#!/bin/bash
# Assembles a RISC-V program and runs it on the full rv32i_core simulation.

if [ -z "$1" ]; then
    echo "Usage: ./simulate.sh <program_name>"
    echo "Example: ./simulate.sh fibonacci"
    exit 1
fi

# Detect python command (use python3 if available, otherwise python)
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Strip .s extension if the user provided it accidentally
PROG_NAME="${1%.s}"

# Navigate to project root safely so relative paths work
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJ_ROOT" || exit 1

ASM_FILE="tb/asm/${PROG_NAME}.s"
HEX_FILE="tb/hex/${PROG_NAME}.hex"

if [ ! -f "$ASM_FILE" ]; then
    echo -e "\033[0;31mERROR: Could not find $ASM_FILE\033[0m"
    exit 1
fi

echo -e "\n\033[0;36m[1/2] Assembling ${PROG_NAME}.s -> ${PROG_NAME}.hex ...\033[0m"
if ! $PYTHON_CMD scripts/rvasm.py "$ASM_FILE" -o "$HEX_FILE" -a; then
    echo -e "\033[0;31mERROR: Assembly failed.\033[0m"
    exit 1
fi

echo -e "\n\033[0;32m[2/2] Running Top-Level Simulation on CPU Core ...\033[0m"
# Resolve absolute path for Cocotb using python (safe across OS/environments)
ABS_HEX_PATH=$($PYTHON_CMD -c "import os; print(os.path.abspath('$HEX_FILE'))")

export PROG_HEX="$ABS_HEX_PATH"
$PYTHON_CMD tb/top/run_top.py
