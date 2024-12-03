# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
import os

from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.osx import BUNDLE

import solara
# see https://github.com/spacetelescope/jdaviz/blob/main/.github/workflows/standalone.yml
# for an example of how to sign the app for macOS
codesign_identity = os.environ.get("DEVELOPER_ID_APPLICATION")

# this copies over the nbextensions enabling json and the js assets
# for all the widgets
datas = [
    (Path(sys.prefix) / "share" / "jupyter", "./share/jupyter"),
    (Path(sys.prefix) / "etc" / "jupyter", "./etc/jupyter"),
]

block_cipher = None


a = Analysis(
    ["solara-app-entrypoint.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["rich.logging"],
    hookspath=["hooks"],
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
    [],
    exclude_binaries=True,
    name="solara",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=codesign_identity,
    entitlements_file="../entitlements.plist",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    # directory name: dist/solara
    name="solara",
)
app = BUNDLE(
    exe,
    coll,
    name="solara.app",
    icon="../solara.icns",
    entitlements_file="entitlements.plist",
    bundle_identifier="com.widgetti.solara",
    version=solara.__version__,
)
