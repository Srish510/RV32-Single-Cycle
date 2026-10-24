# PowerShell Wrapper for RV32I Formal Verification Suite (SymbiYosys + RVFI)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Push-Location $ProjectRoot
try {
    python "$ScriptDir\run_formal.py" @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
