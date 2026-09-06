# Optional one-folder PyInstaller build. Not required — venv + scs-sim.cmd is
# the supported Windows path. PyInstaller pulls a large tree (numpy); skip if
# the download is too heavy.
#
#   powershell -ExecutionPolicy Bypass -File scripts\build_pyinstaller.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$py = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $py = ".\.venv\Scripts\python.exe"
}

Write-Host "[scs-sim] pip install pyinstaller (optional)..."
& $py -m pip install "pyinstaller>=6.0"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force -Path dist | Out-Null
Write-Host "[scs-sim] building one-folder scs-demo (this can take several minutes)..."
& $py -m PyInstaller --noconfirm --clean --onedir --name scs-demo --console scs_sim/__main__.py
Write-Host "[scs-sim] output under dist\scs-demo\  — prefer scs-sim.cmd for daily use."
Write-Host "Signed MSI is out of scope for Phase 7."
