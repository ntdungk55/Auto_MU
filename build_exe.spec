# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Test Auto application."""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules
hiddenimports = [
    'PyQt6',
    'PyQt6.QtWidgets',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'win32gui',
    'win32ui',
    'win32con',
    'win32api',
    'ctypes',
    'pytesseract',
    'openai',
    'requests',
]

# Add src submodules
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('src.logic')
hiddenimports += collect_submodules('src.ui')
hiddenimports += collect_submodules('src.application')
hiddenimports += collect_submodules('src.domain')
hiddenimports += collect_submodules('src.infrastructure')

# Build datas list - only include folders that exist
datas = []
if os.path.exists('tools'):
    datas.append(('tools', 'tools'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='TestAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)
