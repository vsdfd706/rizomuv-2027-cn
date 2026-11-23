# RizomUV 2027 简体中文补丁

把 **RizomUV 2027.0.598** 的界面变成简体中文。**只改界面文字，不动任何功能**——加载、展开、排布、旋转、脚本桥接与英文原版完全一致。

---

## 三步搞定（推荐）

> 前提：你已安装 **英文原版 RizomUV 2027.0.598**，并拥有正版授权。本工具不含也不分发 RizomUV 程序本体。

**第 1 步**：关闭 RizomUV。

**第 2 步**：双击 `dist\RizomUV汉化工具.exe`（无需装 Python）。

**第 3 步**：点窗口里的 **「一键汉化」** 按钮，等十几秒，看到"全部完成"即可。

完成。桌面上会自动多出一个 **「RizomUV 2027 (中文)」** 快捷方式，以后从它启动就是中文界面。

> 想改回英文？双击工具里的 **「一键还原」**（或 `一键还原.bat`），随时恢复，原版已自动备份。

---

## 三种用法，按需选择

| 方式 | 适合谁 | 需要 Python 吗 | 操作 |
|------|--------|----------------|------|
| **A. 独立工具**（推荐） | 普通用户 | ❌ 不需要 | 双击 `dist\RizomUV汉化工具.exe` → 一键汉化 |
| **B. 一键 bat** | 想要源码可控 | ✅ 需要 Python 3 | 双击 `一键汉化.bat`（自动建虚拟环境、装依赖、构建） |
| **C. 手动构建** | 开发者 | ✅ 需要 Python 3 | 见下方"开发者"一节 |

三种方式产出的汉化版**逐字节一致**（MD5 均为 `1a2c16e67fb3a1b595c0fa0622f1940a`）。

---

## 版本校验与故障提示

工具会自动校验原版文件的 MD5（`2ddf8d6da2000ae3eac66d7eea59a311`，对应 2027.0.598）。如果版本不对、找不到原版、RizomUV 没关、或没有管理员权限，工具会**用中文明确告诉你原因并停止**，不会甩给你一堆 Python 报错。

常见问题：

- **"版本不匹配"**：你的 RizomUV 不是 2027.0.598（g864535413），补丁只针对这个版本。
- **"需要管理员权限"**：右键工具 → 以管理员身份运行。
- **"RizomUV 仍在运行"**：先彻底退出 RizomUV 再试。

---

## 法律与合规声明

- 本仓库**只包含补丁源码与工具**，**不包含也不分发 RizomUV 程序本体**。
- 构建时需要你**自己持有正版授权**的英文原版 `rizomuv.exe`。
- 请勿把任何 exe 原版文件、构建产物上传到 GitHub（既违反软件许可，也会超过单文件 100 MB 上限）。`.gitignore` 已排除这些路径。
- 本项目仅供个人学习与交流，使用者需自行遵守 Rizom Lab 的软件许可协议。

---

## 开发者

### 一键构建源码

```bash
# 1) 把正版英文原版复制到仓库根目录，改名为 rizomuv.exe.bak
# 2) 运行（Windows，Python 3，仅标准库）
python build_all.py
# 产出：out/rizomuv_cn.exe
```

用正确原版构建时，产出 MD5 应为 `1a2c16e67fb3a1b595c0fa0622f1940a`。

### 重新打包独立工具

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "RizomUV汉化工具" ^
  --hidden-import tkinter --collect-all tkinter ^
  --add-data "src;src" --add-data "dicts;dicts" ^
  --add-data "force_patch.txt;." --add-data "prefs_backup.txt;." --add-data "shortbuf.txt;." ^
  patch_tool.py
# 产出：dist/RizomUV汉化工具.exe
# 自检：dist\RizomUV汉化工具.exe --selftest --exe 你的原版.exe
```

> **打包环境要求**：用于打包的 Python 必须是**完整安装**（自带 `tkinter` 且 `<Python目录>\tcl\tcl8.6\init.tcl` 存在），精简版/沙箱版 Python 缺 Tcl 数据，打出的 exe 会在启动时报 `ModuleNotFoundError: tkinter` 或 `Can't find init.tcl`。`--collect-all tkinter` 不能省。
>
> 另：补丁脚本由 `runpy` 动态加载，PyInstaller 静态分析看不到它们内部的 `import json/re`，所以 `patch_tool.py` 顶部已显式导入这两个模块强制打包，不要删。

### 工作原理

补丁直接在 exe 的 **UI 字符串区**（文件偏移约 `0x6d00000`–`0x6e00000`）把英文文案替换为中文 UTF-8 字节，用 `\x00` 填充到原字符串槽末尾。关键安全规则（都在 `src/build.py`）：

- **只改 UI 区**：SDK 字符串区、代码区、数据区一律不动。
- **指针密集区跳过**：被内部指针表引用的字符串（命令字段、配置键、面板注册表）是运行时标识符，翻译会导致坏命令 / 加载失败，自动跳过。
- **键名保护**：紧跟 `ZOMID_` / `Vars.` / `Prefs.` 的是变量名，跳过。
- **黑名单**：`dicts/blocklist_ui_only.txt` 列出已知危险键，一律不动。
- **槽位预算**：中文字节数加终止符必须放得进原槽，放不下自动跳过，避免溢出破坏相邻数据。

这套规则来自实测：早期版本曾因误译内部键导致模型空白、旋转失效，现已全部规避。`patch_tool.py` 只是把这些脚本按原顺序串起来执行（版本校验 → 备份 → 构建 → 安装 → 快捷方式），**不重写任何补丁逻辑**。

### 文件结构

```
rizomuv-2027-cn/
├── dist/RizomUV汉化工具.exe      # 独立工具（推荐入口）
├── patch_tool.py                # 工具核心：GUI + CLI + 构建引擎
├── 一键汉化.bat / 一键还原.bat   # 源码方式一键脚本
├── build_all.py                 # 手动一键构建
├── requirements.txt             # 依赖清单（仅标准库，实际为空）
├── force_patch.txt              # 强制放行的 UI 标签白名单
├── prefs_backup.txt             # 配置键参考（用于跳过危险键）
├── shortbuf.txt                 # 固定小缓冲区标签清单
├── dicts/                       # 词典与黑名单
└── src/                         # 13 个补丁脚本
```

---

## 已汉化范围与已知说明

- 顶部菜单、各标签页与面板标题、展开/排布/相似/UDIM/Margin 等面板字段与提示、首选项常用项、悬浮说明，共 500 余处。
- **刻意保留英文**的项：`Scene`、`Tags`、`Viewport 3D/UV`、`Exporter`、`Log`、`Strategy`、`Mutations`、`Threshold` 等（同时被当作内部键或枚举值，翻译会破坏功能）。
- 3ds Max → RizomUV 桥接脚本可能报 `The variable is not found: 'Prefs.UI.Display.UnfoldOptimize'`。这是桥接脚本调用了 2027 已移除的旧变量，**英文原版同样会报**，与汉化无关。
- 导入含退化面的模型时日志可能出现 `Bad corner ID in CBox2D::GetGeometryPoint`，英文原版同样存在，与汉化无关。
