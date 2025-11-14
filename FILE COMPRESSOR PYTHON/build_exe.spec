# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter   # <-- makes the path detection work even in frozen builds

# ------------------------------------------------------------------
# 1. Find the customtkinter package automatically
# ------------------------------------------------------------------
ctk_path = os.path.dirname(customtkinter.__file__)

# ------------------------------------------------------------------
# 2. PyInstaller analysis
# ------------------------------------------------------------------
a = Analysis(
    ['youtube.py'],                     # <-- your main script
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, 'customtkinter'),   # bundle customtkinter assets
    ],
    hiddenimports=[
        'yt_dlp',
        'yt_dlp.version',
        'customtkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

# ------------------------------------------------------------------
# 3. Build the .exe
# ------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YouTubeDownloader',          # <-- name of the final .exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                          # compress with UPX (optional)
    console=False,                     # <-- **windowed** (no console)
    # icon='icon.ico',                # <-- **REMOVED** – no icon
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)