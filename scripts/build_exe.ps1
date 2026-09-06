# Build scs-sim.exe (one-folder) — WebView2 only, lean deps.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$py = "py"; $prefix = @("-3")
if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe"; $prefix = @() }
Write-Host "[scs-sim] ensuring lean desktop deps..."
& $py @prefix -m pip install "pyinstaller>=6.0" "fastapi>=0.110" "uvicorn>=0.27" "httpx>=0.27" "numpy>=1.26" "pyyaml>=6.0" "sgp4>=2.23" "pywebview>=5.0"
& $py @prefix -m pip install --no-deps -e .
New-Item -ItemType Directory -Force -Path dist | Out-Null
Write-Host "[scs-sim] building lean WebView2 EXE..."
& $py @prefix -m PyInstaller --noconfirm --clean --onedir --name scs-sim --console `
  --add-data "scs_sim/viz;scs_sim/viz" `
  --add-data "configs;configs" `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.protocols.http.auto `
  --hidden-import uvicorn.protocols.websockets.auto `
  --hidden-import uvicorn.lifespan.on `
  --hidden-import webview `
  --hidden-import webview.platforms.edgechromium `
  --exclude-module torch `
  --exclude-module torchaudio `
  --exclude-module torchvision `
  --exclude-module tensorflow `
  --exclude-module jax `
  --exclude-module cupy `
  --exclude-module matplotlib `
  --exclude-module PyQt5 `
  --exclude-module PyQt6 `
  --exclude-module PySide2 `
  --exclude-module PySide6 `
  --exclude-module gi `
  --exclude-module android `
  scs_sim/desktop/exe_entry.py
Copy-Item -Recurse -Force configs dist\scs-sim\configs -ErrorAction SilentlyContinue
$exe = "dist\scs-sim\scs-sim.exe"
if (Test-Path $exe) {
  $len = (Get-Item $exe).Length
  $dir = (Get-ChildItem dist\scs-sim -Recurse | Measure-Object -Property Length -Sum).Sum
  Write-Host "[scs-sim] EXE ready: $exe ($([math]::Round($len/1MB,1)) MB file, $([math]::Round($dir/1MB,1)) MB folder)"
} else { Write-Host "[scs-sim] BUILD FAILED"; exit 1 }
