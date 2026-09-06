$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
$prefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
    $prefix = @("-3")
}

Write-Host "[scs-sim] installing editable package..."
& $py @prefix -m pip install -e .
Write-Host "[scs-sim] running Phase 5 ops demo..."
& $py @prefix -m scs_sim.demo_ops --config configs/phase5_ops.yaml @args
exit $LASTEXITCODE
