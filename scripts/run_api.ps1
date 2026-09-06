$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
$prefix = @()
if (Test-Path ".\.venv\Scripts\python.exe") {
    $py = ".\.venv\Scripts\python.exe"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
    $prefix = @("-3")
}

Write-Host "[scs-sim] installing API extra..."
& $py @prefix -m pip install -e ".[api]"
Write-Host "[scs-sim] ops API on http://127.0.0.1:18765/docs"
& $py @prefix -m scs_sim.api --host 127.0.0.1 --port 18765 --config configs/phase6_viz.yaml @args
exit $LASTEXITCODE
