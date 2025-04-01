# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Add all files in assets folder
assets_path = os.path.abspath('assets')
assets_files = []
for root, dirs, files in os.walk(assets_path):
    for file in files:
        file_path = os.path.join(root, file)
        rel_path = os.path.relpath(file_path, os.path.dirname(assets_path))
        assets_files.append((file_path, os.path.join('assets', os.path.relpath(file_path, assets_path))))

# Add localization files
localization_path = os.path.abspath('localization')
localization_files = []
for root, dirs, files in os.walk(localization_path):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, os.path.dirname(localization_path))
            localization_files.append((file_path, os.path.join('localization', os.path.relpath(file_path, localization_path))))

# Combine all data files
all_data_files = assets_files + localization_files
# Add config.template.json
all_data_files.append(('config.template.json', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=all_data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='social_download_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/Logo_new_32x32.png',
) 