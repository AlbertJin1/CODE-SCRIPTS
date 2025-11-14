# pyinstaller.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('backend/static', 'static'),        # React build
        ('backend/api.py', '.'),             # <-- ADD THIS LINE
        ('backend/core', 'core'),            # your compressor modules
        ('backend/utils', 'utils'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'api',                               # <-- ADD THIS
        'PIL',
        'PyPDF2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CompressMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,              # <-- CHANGE TO True FOR DEBUGGING
    icon=None,
)