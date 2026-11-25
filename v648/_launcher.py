# -*- coding: utf-8 -*-
"""控制台版一键汉化入口（供 PyInstaller 打包成 exe，双击即用）。

无需 Python、无需命令行：双击后自动查找并校验英文原版、构建汉化版、
备份原版、安装并创建桌面快捷方式；全程中文提示，出错给出原因。
"""
import sys

import patch_tool


def main():
    print('=' * 56)
    print('  RizomUV 2027.0.648 Win  简体中文一键汉化')
    print('  只改界面文字，不动任何功能')
    print('=' * 56)
    print()
    print('运行前请先完全关闭 RizomUV。')
    print()

    # --check：只校验环境，不安装（用于验证 exe 打包是否完整）
    if '--check' in sys.argv:
        import tempfile
        from pathlib import Path
        orig = patch_tool.find_original()
        if '--exe' in sys.argv:
            orig = Path(sys.argv[sys.argv.index('--exe') + 1])
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

    try:
        patch_tool.do_install(emit=print)
    except Exception as e:
        print()
        print('[失败] %s' % e)
        print('未做任何更改。请按提示处理后重试。')
    else:
        print()
        print('全部完成，现在可以启动 RizomUV，界面已是简体中文。')
    finally:
        print()
        input('按回车键退出...')
    return 0


if __name__ == '__main__':
    sys.exit(main())
