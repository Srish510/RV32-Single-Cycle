<#
.SYNOPSIS
Runs the official RISC-V RV32I Architectural Compliance Test Suite.

.DESCRIPTION
Compiles each compliance test in riscv-arch-test/riscv-test-suite/rv32i_m/I/src/
using the installed RISC-V GCC toolchain, executes them on the simulated RV32I core,
and verifies correct architectural execution via the tohost test interface.
Note: fence, ecall, and ebreak are intentionally excluded per architecture specification.

.EXAMPLE
.\tb\run_compliance.ps1
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjRoot = Split-Path -Parent $ScriptDir

Push-Location $ProjRoot
try {
    python tb\run_compliance.py
} finally {
    Pop-Location
}
