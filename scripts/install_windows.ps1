# Create .venv and install SCS-Sim with dev + viz + api extras.
# Usage (from repo root, or any cwd — script cds to the repo):
#   powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
$prefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
    $prefix = @("-3")
}

Write-Host "[scs-sim] creating .venv ..."
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    & $py @prefix -m venv .venv
}

$venvPy = Join-Path $PWD ".venv\Scripts\python.exe"
Write-Host "[scs-sim] upgrading pip ..."
& $venvPy -m pip install -U pip
Write-Host "[scs-sim] pip install -e `".[dev,viz,api]`" ..."
& $venvPy -m pip install -e ".[dev,viz,api]"

Write-Host ""
Write-Host "[scs-sim] ready. Next:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  scs-sim.cmd demo"
Write-Host "  scs-sim.cmd viz"
Write-Host "  scs-sim.cmd api"
Write-Host "  .\.venv\Scripts\python.exe -m pytest"
Write-Host "See docs\WINDOWS.md (no signed MSI in this phase)."
