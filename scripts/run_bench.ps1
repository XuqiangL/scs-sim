$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
$prefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
    $prefix = @("-3")
}

Write-Host "[scs-sim] 10k Walker + Kepler-J2 bench (ISL subsample 64)..."
& $py @prefix -m scs_sim.bench --config configs/walker_10k.yaml --full --steps 4 --isl-max-sats 64 @args
exit $LASTEXITCODE
