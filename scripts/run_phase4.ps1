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
Write-Host "[scs-sim] running Phase 4 compute demo..."
& $py @prefix -m scs_sim.demo --config configs/phase4_compute.yaml @args
exit $LASTEXITCODE
