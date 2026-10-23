# PowerShell Lockstep Co-Simulation Runner
param(
    [ValidateSet("verilator", "cocotb", "both")]
    [string]$Sim = "verilator",
    [string]$Test = "",
    [switch]$All,
    [switch]$Trace,
    [Nullable[int]]$InjectFault = $null
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PyScript = Join-Path $ScriptDir "run_cosim.py"

$ArgsList = @("--sim", $Sim)
if ($Test) {
    $ArgsList += @("--test", $Test)
}
if ($All) {
    $ArgsList += @("--all")
}
if ($Trace) {
    $ArgsList += @("--trace")
}
if ($null -ne $InjectFault) {
    $ArgsList += @("--inject-fault", $InjectFault)
}

python $PyScript @ArgsList
exit $LASTEXITCODE
