# -*- coding: utf-8 -*-
"""GUI 版启动入口（供 PyInstaller 打包成 onefile exe，双击打开窗口）。

保留命令行模式：--install / --restore / --selftest / --check 仍走 cli，
无参数时打开图形界面。
"""
import sys

import patch_tool


def main():
    args = sys.argv[1:]
    if '--check' in args:
        # 自检：只校验 + 构建到临时目录，不安装
        import tempfile
        from pathlib import Path
        orig = patch_tool.find_original()
        if '--exe' in args:
            orig = Path(args[args.index('--exe') + 1])
        print('资源目录：%s' % patch_tool.resource_dir())
        print('英文原版：%s' % orig)
        if orig:
            ok, msg = patch_tool.check_version(orig)
            print(msg)
            if ok:
                try:
                    out = patch_tool.build(orig, Path(tempfile.mkdtemp()), emit=print)
                    print('构建自检：%s' % ('通过 ✓' if patch_tool.md5(out) == patch_tool.EXPECTED_OUTPUT_MD5 else '失败 ✗'))
                except Exception as e:
                    print('构建自检失败：%s' % e)
        input('按回车键退出...')
        return 0
    if args and (args[0] in ('--install', '--restore') or '--selftest' in args):
        return patch_tool.cli()
    patch_tool.gui()
    return 0


if __name__ == '__main__':
    sys.exit(main())
