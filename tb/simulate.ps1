<#
.SYNOPSIS
Assembles a RISC-V program and runs it on the full rv32i_core simulation.

.DESCRIPTION
Takes the base name of a program in tb\asm\, assembles it to tb\hex\, and 
launches the cocotb top-level simulation.

.EXAMPLE
.\simulate.ps1 fibonacci
#>
param (
    [Parameter(Mandatory=$true, Position=0, HelpMessage="Name of the assembly file (without .s extension)")]
    [string]$ProgName
)

# Get the directory of this script (tb/) and the project root
$TbDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjRoot = Split-Path -Parent $TbDir

# Navigate to project root to ensure relative paths in python scripts work perfectly
Push-Location $ProjRoot

# Handle case where user accidentally types "fibonacci.s" instead of "fibonacci"
$ProgName = $ProgName -replace '\.s$', ''

$AsmFile = "tb\asm\$ProgName.s"
$HexFile = "tb\hex\$ProgName.hex"

if (-Not (Test-Path $AsmFile)) {
    Write-Host "ERROR: Could not find $AsmFile" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "`n[1/2] Assembling $ProgName.s -> $ProgName.hex ..." -ForegroundColor Cyan
python scripts\rvasm.py $AsmFile -o $HexFile -a

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Assembly failed." -ForegroundColor Red
    Pop-Location
    exit $LASTEXITCODE
}

Write-Host "`n[2/2] Running Top-Level Simulation on CPU Core ..." -ForegroundColor Green
# Resolve absolute path for Cocotb to find the hex file
$env:PROG_HEX = (Resolve-Path $HexFile).Path

python tb\top\run_top.py

# Cleanup environment variable and restore working directory
Remove-Item Env:\PROG_HEX -ErrorAction SilentlyContinue
Pop-Location
