# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

import os
_HERE = os.path.dirname(os.path.abspath(SPEC))
datas = [(os.path.join(_HERE, 'src'), 'src'), (os.path.join(_HERE, 'dicts'), 'dicts'), (os.path.join(_HERE, 'force_patch.txt'), '.'), (os.path.join(_HERE, 'prefs_backup.txt'), '.'), (os.path.join(_HERE, 'shortbuf.txt'), '.')]
binaries = []
hiddenimports = ['tkinter']
tmp_ret = collect_all('tkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['patch_tool.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RizomUV汉化工具',
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
)
