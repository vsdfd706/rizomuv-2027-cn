# -*- mode: python ; coding: utf-8 -*-
# 新版本一键汉化 exe 打包配置（GUI 版）。
# 需要带完整 tkinter 的 Python；在 v648 目录内运行：
#   python -m PyInstaller --noconfirm --distpath dist --workpath build_pyi 打包.spec
import os
from PyInstaller.utils.hooks import collect_all

_HERE = os.path.dirname(os.path.abspath(SPEC))

# build.py 由 patch_tool.py 通过 importlib 动态加载，静态分析看不到，
# 因此显式作为数据文件打包到根目录；资源路径由 patch_tool.resource_dir() 指向 _MEIPASS。
datas = [
    (os.path.join(_HERE, 'build.py'), '.'),
    (os.path.join(_HERE, 'verified_dict.json'), '.'),
    (os.path.join(_HERE, 'dicts'), 'dicts'),
]
binaries = []
hiddenimports = ['patch_tool', 'ui_theme', 'json', 're', 'tkinter']
# 完整打入 tcl/tk 数据（init.tcl 等），否则运行时报 Can't find init.tcl
_tk = collect_all('tkinter')
datas += _tk[0]
binaries += _tk[1]
hiddenimports += _tk[2]

a = Analysis(
    ['_gui_launcher.py'],
    pathex=[_HERE],
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
    name='RizomUV汉化工具_648',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI 窗口，无控制台黑框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
