<#
.SYNOPSIS
Runs the complete RV32I Coverage & Verification Closure Suite.

.DESCRIPTION
Executes all 37 RISC-V Architectural Compliance tests and the directed coverage
closure test with both Functional (ISA) and Structural (Verilator line/toggle/branch) coverage collection.
Generates an interactive HTML dashboard and updates docs/coverage.md.

.EXAMPLE
.\tb\run_coverage.ps1
.\tb\run_coverage.ps1 --sim verilator
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjRoot = Split-Path -Parent $ScriptDir

Push-Location $ProjRoot
try {
    python tb\run_coverage.py @RemainingArgs
} finally {
    Pop-Location
}
