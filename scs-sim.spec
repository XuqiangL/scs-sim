# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['scs_sim/desktop/exe_entry.py'],
    pathex=[],
    binaries=[],
    datas=[('scs_sim/viz', 'scs_sim/viz'), ('configs', 'configs')],
    hiddenimports=['uvicorn.logging', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'webview', 'webview.platforms.edgechromium'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchaudio', 'torchvision', 'tensorflow', 'jax', 'cupy', 'matplotlib', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'gi', 'android'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='scs-sim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='scs-sim',
)
