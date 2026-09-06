$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
$prefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
    $prefix = @("-3")
}

Write-Host "[scs-sim] installing editable package (core)..."
& $py @prefix -m pip install -e .
Write-Host "[scs-sim] optional matplotlib for PNG tracks (safe to skip)..."
try {
    & $py @prefix -m pip install -e ".[viz]"
} catch {
    Write-Host "[scs-sim] viz extra skipped — SVG fallback still works"
}
Write-Host "[scs-sim] running Phase 6 viz + KPI demo..."
& $py @prefix -m scs_sim.demo_viz --config configs/phase6_viz.yaml @args
exit $LASTEXITCODE
