# -*- coding: utf-8 -*-
"""
RizomUV 2027 简体中文汉化工具
================================================================
一个文件，三种用法：
  1) 直接运行（双击 exe / python patch_tool.py）→ 图形界面，两个大按钮
  2) python patch_tool.py --install → 命令行一键汉化（供“一键汉化.bat”调用）
  3) python patch_tool.py --restore → 命令行一键还原

本工具不含、也不分发 RizomUV 程序本体；只对使用者自己持有的正版原版打补丁。
汉化逻辑完整复用 src/ 下经过实测的 13 个脚本，本文件只负责：
版本校验 → 备份 → 调用脚本 → 安装 → 建快捷方式 → 日志反馈。
"""
import contextlib
import hashlib
import io
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import runpy
from pathlib import Path

# 补丁脚本通过 runpy 动态加载，PyInstaller 静态分析看不到它们内部的 import。
# 这里显式声明，强制把 json/re 打进 exe，否则运行到 build.py 会报 No module named 'json'。
import json as _json_for_packer
import re as _re_for_packer
_DYNAMIC_DEPS = (_json_for_packer, _re_for_packer)

# ---------------------------------------------------------------- 常量
EXPECTED_MD5 = '2ddf8d6da2000ae3eac66d7eea59a311'      # 原版 2027.0.598.g864535413
EXPECTED_OUTPUT_MD5 = '1a2c16e67fb3a1b595c0fa0622f1940a'  # 汉化版自检值
APP_TITLE = 'RizomUV 2027 简体中文汉化工具'

PF = os.environ.get('ProgramFiles') or r'C:\Program Files'
PF86 = os.environ.get('ProgramFiles(x86)') or r'C:\Program Files (x86)'
INSTALL_DIRS = [
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF86) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027',
]
EXE_NAME = 'rizomuv.exe'
BAK_NAME = 'rizomuv_en_backup.exe'

# 构建步骤：(脚本名, 传给 sys.argv 的参数列表) —— 与 build_all.py 完全同序
STEPS = [
    ('build.py',        ['dicts/tr_core.json,dicts/tr_phrase.json', 'build/rizomuv_ui_only.exe',
                         '--block', 'dicts/blocklist_ui_only.txt']),
    ('patch_menu.py',   ['build/rizomuv_menu_final.exe', 'dicts/menu_all.json']),
    ('patch_tooltip.py', []),
    ('patch_all.py',    ['build/rizomuv_panel_final.exe', 'dicts/batch_all.json']),
    ('patch_udim.py',   []),
    ('patch_redbox.py', []),
    ('patch_similar.py', []),
    ('patch_margin.py', []),
    ('patch_pack.py',   []),
    ('patch_unwrap.py', []),
    ('patch_tabs2.py',  []),
    ('patch_menu2.py',  []),
    ('patch_prefs.py',  []),
]
RES_FILES = ['force_patch.txt', 'prefs_backup.txt', 'shortbuf.txt']


# ---------------------------------------------------------------- 工具函数
def resource_dir() -> Path:
    """返回内嵌资源根目录（含 src/ dicts/ *.txt）。兼容 PyInstaller。"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def log(msg=''):
    print(msg, flush=True)


# 运行时可被用户/GUI 覆盖的安装目录
INSTALL_DIR_OVERRIDE: Path | None = None


def set_install_dir(path: Path | None):
    global INSTALL_DIR_OVERRIDE
    INSTALL_DIR_OVERRIDE = Path(path) if path else None


def _dirs_with_rizomuv() -> list:
    """多途径探测可能装着 RizomUV 的目录（按可信度排序，去重）。"""
    found = []

    def add(p):
        if p and p.exists() and (p / EXE_NAME).exists():
            k = str(p).lower()
            if k not in seen:
                seen.add(k)
                found.append(p)

    seen = set()

    # 1) 用户手动指定（最高优先级）
    if INSTALL_DIR_OVERRIDE:
        add(INSTALL_DIR_OVERRIDE)

    # 2) Windows 卸载注册表（最可靠，能找到自定义安装路径）
    try:
        import winreg
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]
        for hive, base in roots:
            try:
                key = winreg.OpenKey(hive, base)
            except OSError:
                continue
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                try:
                    sk = winreg.OpenKey(key, sub)
                    display, _ = winreg.QueryValueEx(sk, 'DisplayName')
                    if display and 'rizomuv' in str(display).lower():
                        for val in ('InstallLocation', 'DisplayIcon'):
                            try:
                                raw, _ = winreg.QueryValueEx(sk, val)
                                if raw:
                                    p = Path(str(raw).strip('"'))
                                    add(p if p.is_dir() else p.parent)
                            except OSError:
                                pass
                    winreg.CloseKey(sk)
                except OSError:
                    pass
            winreg.CloseKey(key)
    except Exception:
        pass

    # 3) 常见固定路径 + 各盘符下的常见位置
    candidates = list(INSTALL_DIRS)
    drives = []
    try:
        import string
        for letter in string.ascii_uppercase:
            d = Path(f'{letter}:\\')
            if d.exists():
                drives.append(d)
    except Exception:
        pass
    for dr in drives:
        candidates += [
            dr / 'Rizom Lab' / 'RizomUV 2027.0',
            dr / 'Program Files' / 'Rizom Lab' / 'RizomUV 2027.0',
            dr / 'Program Files (x86)' / 'Rizom Lab' / 'RizomUV 2027.0',
        ]
    for p in candidates:
        add(p)

    # 4) 用户目录、桌面、下载里的 rizomuv.exe（便携版 / 绿色版）
    for env in ('USERPROFILE', 'PUBLIC', 'OneDrive'):
        base = os.environ.get(env)
        if base:
            for sub in ('Desktop', 'Downloads', 'Documents', 'Rizom Lab', 'RizomUV 2027.0'):
                add(Path(base) / sub)

    # 本补丁仅适用 2027.0.598：把名字含 2027 的目录排到最前
    found.sort(key=lambda p: 0 if '2027' in str(p) else 1)
    return found


def install_dir() -> Path:
    dirs = _dirs_with_rizomuv()
    if dirs:
        return dirs[0]
    # 没探测到，返回默认路径（install() 会给出明确错误）
    return INSTALL_DIR_OVERRIDE or INSTALL_DIRS[0]


def original_candidates() -> list:
    """收集可能的英文原版 exe 路径（按优先级）。"""
    out = []
    # 覆盖所有探测到的安装目录，而不只是第一个
    for d in _dirs_with_rizomuv():
        out += [d / BAK_NAME, d / EXE_NAME]
    here = resource_dir()
    out += [here / 'rizomuv.exe.bak', here / EXE_NAME]
    for line in ['C:\\Users\\Public\\Downloads\\rizomuv.exe']:
        out.append(Path(line))
    # 去重、只保留存在的文件
    seen, uniq = set(), []
    for p in out:
        k = str(p).lower()
        if k not in seen and p.exists():
            seen.add(k)
            uniq.append(p)
    return uniq


def find_original() -> Path | None:
    """自动寻找 MD5 精确匹配的英文原版。"""
    for p in original_candidates():
        try:
            if md5(p) == EXPECTED_MD5:
                return p
        except OSError:
            pass
    return None


def check_version(exe: Path):
    """返回 (是否匹配, 说明文字)。绝不抛异常给上层。"""
    if not exe or not exe.exists():
        return False, '找不到文件：%s' % exe
    actual = md5(exe)
    if actual == EXPECTED_MD5:
        return True, '版本正确：RizomUV 2027.0.598（g864535413）'
    # 判断是否已经是汉化版
    tag = ''
    if actual == EXPECTED_OUTPUT_MD5:
        tag = '（这个文件看起来已经是汉化版了，不能用它再次构建）'
    return False, ('版本不匹配：需要 RizomUV 2027.0.598（g864535413）\n'
                   '  期望 MD5：%s\n'
                   '  你的文件：%s%s\n'
                   '  请改用正确的英文原版 rizomuv.exe。' % (EXPECTED_MD5, actual, tag))


# ---------------------------------------------------------------- 构建引擎
def build(original: Path, workdir: Path | None = None, emit=log) -> Path:
    """复用 src/ 脚本构建汉化版，返回 out/rizomuv_cn.exe 路径。"""
    res = resource_dir()
    workdir = Path(workdir or tempfile.mkdtemp(prefix='rizomcn_'))
    emit('工作目录：%s' % workdir)

    # 1) 搭建与 build_all.py 一致的目录结构
    (workdir / 'build').mkdir(parents=True, exist_ok=True)
    (workdir / 'out').mkdir(parents=True, exist_ok=True)
    for name in ['src', 'dicts']:
        src = res / name
        if not src.exists():
            raise RuntimeError('缺少资源目录：%s（exe 打包不完整？）' % src)
        shutil.copytree(src, workdir / name, dirs_exist_ok=True)
    for txt in RES_FILES:
        shutil.copyfile(res / txt, workdir / txt)
    shutil.copyfile(original, workdir / 'rizomuv.exe.bak')

    # 2) 按顺序执行 13 个原始脚本（进程内 runpy，避免 exe 递归启动）
    old_cwd, old_argv = os.getcwd(), sys.argv
    os.chdir(workdir)
    try:
        for i, (script, args) in enumerate(STEPS, 1):
            emit('[%02d/%02d] %s ...' % (i, len(STEPS), script))
            sys.argv = [script] + args
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                runpy.run_path(str(workdir / 'src' / script), run_name='__main__')
            detail = buf.getvalue().strip()
            if detail:
                emit('        ' + detail.splitlines()[0])
    except Exception as e:
        raise RuntimeError('构建失败于第 %d 步：%s\n%s' % (i, script, e)) from e
    finally:
        os.chdir(old_cwd)
        sys.argv = old_argv

    # 3) 收尾产出
    final = workdir / 'build' / 'rizomuv_prefs_final.exe'
    dest = workdir / 'out' / 'rizomuv_cn.exe'
    shutil.copyfile(final, dest)
    actual = md5(dest)
    emit('产出：%s' % dest)
    emit('MD5 ：%s' % actual)
    if actual == EXPECTED_OUTPUT_MD5:
        emit('自检通过 ✓ 与已验证的汉化版完全一致')
    else:
        emit('注意：MD5 与已知值不同，请留意功能验证。')
    return dest


def is_admin() -> bool:
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def rizomuv_running() -> bool:
    """检测 RizomUV 是否在运行。只认真正的进程表行，避免错误文本误判。"""
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rizomuv.exe', '/NH'],
                           capture_output=True, text=True)
        for line in (r.stdout or '').splitlines():
            # 真正的进程行以 "rizomuv.exe" 开头；INFO/ERROR 行不会这样
            if line.strip().lower().startswith('rizomuv.exe'):
                return True
    except Exception:
        pass
    return False


def need_admin(target: Path) -> bool:
    """目标不可写时需要管理员权限。"""
    try:
        with open(target / '__wtest__.tmp', 'wb'):
            pass
        (target / '__wtest__.tmp').unlink()
        return False
    except OSError:
        return True


def install(cn_exe: Path, target_dir: Path, emit=log) -> Path:
    """备份原版 + 安装汉化版。返回目标 exe 路径。"""
    dst = target_dir / EXE_NAME
    bak = target_dir / BAK_NAME
    if not dst.exists():
        raise RuntimeError('找不到 RizomUV 安装目录：%s' % dst)

    # 关闭正在运行的 RizomUV
    if rizomuv_running():
        raise RuntimeError('RizomUV 仍在运行，请先关闭它再安装。')

    if not bak.exists():
        shutil.copyfile(dst, bak)
        emit('已备份英文原版 → %s' % bak)
    else:
        emit('英文原版备份已存在，跳过备份。')
    shutil.copyfile(cn_exe, dst)
    emit('已安装汉化版 → %s' % dst)
    return dst


def create_shortcut(target: Path, emit=log):
    """在桌面创建“RizomUV 2027 (中文)”快捷方式。"""
    try:
        desktop = Path(os.environ['USERPROFILE']) / 'Desktop'
        if not desktop.exists():
            desktop = Path(os.environ.get('PUBLIC', r'C:\Users\Public')) / 'Desktop'
        lnk = desktop / 'RizomUV 2027 (中文).lnk'
        ps = ('$w=New-Object -ComObject WScript.Shell; '
              '$s=$w.CreateShortcut("%s"); '
              '$s.TargetPath="%s"; '
              '$s.WorkingDirectory="%s"; '
              '$s.Save()' % (lnk, target, target.parent))
        subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, timeout=30)
        emit('已创建桌面快捷方式：%s' % lnk)
    except Exception as e:
        emit('快捷方式创建失败（不影响汉化）：%s' % e)


def restore(target_dir: Path, emit=log):
    """用备份还原英文原版。"""
    dst, bak = target_dir / EXE_NAME, target_dir / BAK_NAME
    if not bak.exists():
        raise RuntimeError('找不到英文原版备份：%s\n无法还原。' % bak)
    if rizomuv_running():
        raise RuntimeError('RizomUV 仍在运行，请先关闭它再还原。')
    shutil.copyfile(bak, dst)
    emit('已还原为英文原版 → %s' % dst)


# ---------------------------------------------------------------- 流程封装
def do_install(manual_original: Path | None = None, emit=log):
    emit('=== 一键汉化开始 ===')
    original = manual_original or find_original()
    ok, msg = check_version(original)
    emit(msg)
    if not ok:
        raise RuntimeError('版本校验未通过，已停止。' + ('\n' + msg if '\n' not in msg else ''))
    dirs = _dirs_with_rizomuv()
    if len(dirs) > 1:
        emit('检测到多个 RizomUV 安装目录，使用：%s' % dirs[0])
        for d in dirs[1:]:
            emit('       （另有：%s）' % d)
    target = install_dir()
    emit('安装目录：%s' % target)
    if need_admin(target) and not is_admin():
        raise RuntimeError('安装目录需要管理员权限，请以管理员身份运行本工具。')
    cn = build(original, emit=emit)
    dst = install(cn, target, emit=emit)
    create_shortcut(dst, emit=emit)
    emit('=== 全部完成：现在可以启动 RizomUV，界面已是简体中文 ===')


def do_restore(emit=log):
    emit('=== 一键还原开始 ===')
    target = install_dir()
    emit('安装目录：%s' % target)
    if need_admin(target) and not is_admin():
        raise RuntimeError('安装目录需要管理员权限，请以管理员身份运行本工具。')
    restore(target, emit=emit)
    emit('=== 完成：已恢复英文原版 ===')


# ---------------------------------------------------------------- 命令行入口
def cli():
    mode = '--install' if '--install' in sys.argv else ('--restore' if '--restore' in sys.argv else None)
    manual = None
    if '--exe' in sys.argv:
        p = sys.argv[sys.argv.index('--exe') + 1]
        manual = Path(p)
    if '--dir' in sys.argv:
        p = sys.argv[sys.argv.index('--dir') + 1]
        set_install_dir(Path(p))
    if '--selftest' in sys.argv:
        try:
            orig = manual or find_original()
            log('资源目录：%s' % resource_dir())
            ok, msg = check_version(orig)
            log(msg)
            if not ok:
                return 2
            out = build(orig, emit=log)
            good = md5(out) == EXPECTED_OUTPUT_MD5
            log('自检结果：%s' % ('通过 ✓' if good else '失败 ✗'))
            return 0 if good else 3
        except Exception as e:
            log('[错误] %s' % e)
            return 2
    if not mode:
        log(__doc__)
        return 0
    try:
        if mode == '--install':
            do_install(manual)
        else:
            do_restore()
    except Exception as e:
        log('\n[错误] %s' % e)
        log('处理失败，未做任何更改。')
        return 2
    return 0


# ---------------------------------------------------------------- 图形界面
def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry('680x500')
    root.resizable(False, False)

    q = queue.Queue()
    running = {'v': False}

    frm = tk.Frame(root, padx=16, pady=12)
    frm.pack(fill='both', expand=True)

    tk.Label(frm, text=APP_TITLE, font=('Microsoft YaHei UI', 15, 'bold')).pack(anchor='w')
    tk.Label(frm, text='只汉化界面文字，不改动任何功能。请先关闭 RizomUV。',
             font=('Microsoft YaHei UI', 10), foreground='#555').pack(anchor='w', pady=(2, 10))

    info = tk.Label(frm, text='正在检测...', font=('Microsoft YaHei UI', 10),
                    justify='left', anchor='w')
    info.pack(fill='x')

    manual = {'p': None}

    def refresh_info():
        """统一刷新检测信息（原版 + 安装目录）。"""
        p = manual['p'] or find_original()
        lines = []
        if p:
            lines.append('✓ 英文原版：%s' % p)
        else:
            cands = original_candidates()
            lines.append('✗ 未自动找到英文原版（需要 2027.0.598），请点“选择原版文件”。')
            if cands:
                lines.append('  检测到这些文件但版本不符：' + '、'.join(str(c) for c in cands[:3]))

        dirs = _dirs_with_rizomuv()
        target = install_dir()
        if dirs:
            lines.append('✓ 安装目录：%s' % target)
            if len(dirs) > 1:
                lines.append('  （共发现 %d 处，可用“更换目录”切换）' % len(dirs))
        else:
            lines.append('✗ 未找到安装目录：%s' % target)
            lines.append('  如果 RizomUV 装在别处，请点“更换目录”。')
        color = '#0a7a2f' if (p and dirs) else '#c0392b'
        info.configure(text='\n'.join(lines), foreground=color)

    def detect():
        refresh_info()

    bar = tk.Frame(frm)
    bar.pack(fill='x', pady=10)

    def pick():
        f = filedialog.askopenfilename(title='选择英文原版 rizomuv.exe',
                                       filetypes=[('RizomUV 程序', '*.exe'), ('所有文件', '*.*')])
        if not f:
            return
        p = Path(f)
        ok, msg = check_version(p)
        if not ok:
            messagebox.showerror('版本不匹配', msg)
            return
        manual['p'] = p
        refresh_info()

    def pick_dir():
        d = filedialog.askdirectory(title='选择 RizomUV 的安装目录（里面有 rizomuv.exe）')
        if not d:
            return
        dp = Path(d)
        if not (dp / EXE_NAME).exists():
            messagebox.showerror('不是安装目录', '这个目录里没有 rizomuv.exe。\n请选择包含 rizomuv.exe 的文件夹，例如 D:\\RizomUV 2027.0')
            return
        set_install_dir(dp)
        refresh_info()

    btn_pick = tk.Button(bar, text='选择原版文件', font=('Microsoft YaHei UI', 10), command=pick)
    btn_pick.pack(side='left', padx=(0, 8))
    btn_dir = tk.Button(bar, text='更换安装目录', font=('Microsoft YaHei UI', 10), command=pick_dir)
    btn_dir.pack(side='left')

    logbox = tk.Text(frm, height=13, font=('Consolas', 9), wrap='none')
    logbox.pack(fill='both', expand=True, side='left')
    scroll = tk.Scrollbar(frm, command=logbox.yview)
    scroll.pack(fill='y', side='right')
    logbox.configure(yscrollcommand=scroll.set)

    def pump():
        try:
            while True:
                s = q.get_nowait()
                logbox.insert('end', s + '\n')
                logbox.see('end')
        except queue.Empty:
            pass
        if running['v']:
            root.after(120, pump)

    def runner(fn, *a):
        running['v'] = True
        btn_han.configure(state='disabled')
        btn_res.configure(state='disabled')
        btn_pick.configure(state='disabled')
        btn_dir.configure(state='disabled')
        root.after(100, pump)

        def work():
            try:
                fn(*a, emit=q.put)
                q.put('')
                q.put('✅ 操作成功完成。')
            except Exception as e:
                q.put('')
                q.put('❌ 失败：%s' % e)
                messagebox.showerror('操作失败', str(e))
            finally:
                running['v'] = False
                q.put('__DONE__')

        def finish():
            try:
                while True:
                    s = q.get_nowait()
                    if s == '__DONE__':
                        break
                    logbox.insert('end', s + '\n')
            except queue.Empty:
                pass
            logbox.see('end')
            btn_han.configure(state='normal')
            btn_res.configure(state='normal')
            btn_pick.configure(state='normal')
            btn_dir.configure(state='normal')

        def watch():
            if running['v']:
                root.after(120, watch)
            else:
                finish()
        root.after(120, watch)

    def on_han():
        p = manual['p'] or find_original()
        ok, msg = check_version(p)
        if not ok:
            messagebox.showerror('版本不匹配，已停止', msg)
            return
        target = install_dir()
        if not (target / EXE_NAME).exists():
            messagebox.showerror('找不到安装目录',
                                 '在 %s 没找到 rizomuv.exe。\n请点“更换安装目录”选择正确的文件夹。' % target)
            return
        if not messagebox.askyesno('确认', '即将把简体中文版安装到：\n%s\n\n确认无误且 RizomUV 已关闭？' % target):
            return
        runner(do_install, p)

    def on_res():
        if not messagebox.askyesno('确认', '即将把 RizomUV 恢复为英文原版。继续？'):
            return
        runner(do_restore)

    actions = tk.Frame(frm)
    actions.pack(fill='x', pady=(10, 0))
    btn_han = tk.Button(actions, text='一键汉化', font=('Microsoft YaHei UI', 11, 'bold'),
                        bg='#1f6feb', fg='white', width=14, command=on_han)
    btn_han.pack(side='left', padx=(0, 10))
    btn_res = tk.Button(actions, text='一键还原', font=('Microsoft YaHei UI', 11),
                        width=14, command=on_res)
    btn_res.pack(side='left')

    detect()
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and (sys.argv[1] in ('--install', '--restore') or '--selftest' in sys.argv):
        sys.exit(cli())
    gui()
