# -*- mode: python ; coding: utf-8 -*-
# 新版本一键汉化 exe 打包配置。在 v648 目录内运行：
#   python -m PyInstaller --noconfirm --distpath dist --workpath build_pyi 打包.spec
import os

_HERE = os.path.dirname(os.path.abspath(SPEC))

# build.py 由 patch_tool.py 通过 importlib 动态加载，静态分析看不到，
# 因此显式作为数据文件打包到根目录；资源路径由 patch_tool.resource_dir() 指向 _MEIPASS。
datas = [
    (os.path.join(_HERE, 'build.py'), '.'),
    (os.path.join(_HERE, 'verified_dict.json'), '.'),
    (os.path.join(_HERE, 'dicts'), 'dicts'),
]

a = Analysis(
    ['_launcher.py'],
    pathex=[_HERE],
    binaries=[],
    datas=datas,
    hiddenimports=['patch_tool', 'json', 're'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],  # 控制台版入口不需要 GUI；打包环境也可能缺 tcl/tk
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
