# 新版本 RizomUV 2027.0.648 Win 简体中文补丁

把**新版本 RizomUV 2027.0.648 Win** 的界面变成简体中文。**只改界面文字，不动任何功能**——加载、展开、排布、旋转、脚本桥接与英文原版完全一致。

> 如果你装的是老版本 2027.0.598 Win，请回到仓库根目录，用 [`../v598/`](../v598/) 里的工具。两套工具不能混用。

## 一键汉化（不懂代码也能用）

**双击 `dist\RizomUV汉化工具_648.exe`**，打开图形窗口，按提示操作即可。它会自动查找英文原版、校验版本、构建、备份、安装并创建桌面快捷方式。无需安装 Python。

界面采用简洁大气的浅色中性风格：品牌标题、环境检测状态、操作日志、主操作按钮分区清晰；支持窗口自由缩放（内容自适应），按钮有悬停/焦点/禁用反馈，并有 `Ctrl+H` 汉化、`Ctrl+R` 还原快捷键。

- 运行前请**完全关闭 RizomUV**。
- 需要你本机已安装**正版英文原版 2027.0.648 Win**（工具只读取它，不分发软件本体）。
- 若自动找不到原版，点窗口里的 **「选择原版文件」** 手动指定；安装目录不对则点 **「更换安装目录」**。
- 想改回英文：点窗口里的 **「一键还原」**（或双击 `一键还原.bat`），原版已自动备份在安装目录，名为 `rizomuv_en_backup.exe`。

工具会校验英文原版 MD5 必须为 `abbc69339a373f08cbc3507111d97fbf`（对应 2027.0.648）。版本不对、找不到原版、RizomUV 没关、没有管理员权限时，工具会用中文说明原因并停止，不会乱改文件。

## 三种用法

| 方式 | 适合谁 | 需要 Python 吗 | 操作 |
|------|--------|----------------|------|
| **A. 独立工具**（推荐） | 普通用户 | ❌ 不需要 | 双击 `dist\RizomUV汉化工具_648.exe` |
| **B. 一键 bat** | 想要源码可控 | ✅ 需要 Python 3 | 双击 `一键汉化.bat`（自动建虚拟环境、安装、构建） |
| **C. 手动构建** | 开发者 | ✅ 需要 Python 3 | `python build.py <英文原版.exe> <输出.exe>` |

三种方式产出的汉化版**逐字节一致**（MD5 均为 `8101756ad004fc63b5b5ba206d9d7d87`）。

## 汉化内容与安全原则

在 exe 的 **UI 字符串区**（文件偏移 `0x6d00000`–`0x6e20000`）把英文文案替换为中文 UTF-8 字节，用 `\x00` 填充到原字符串槽末尾：

- 主迁移 621 词 + 顶部工具栏 7 个分组标题 + Transform 面板 8 个标签 + 菜单 6 个标签 + 视口 Grid 面板 4 个显示标签（`显示网格` / `划分数` / `吸附细分` / `像素网格`）+ 视口显示标签 4 个（`光照` / `像素` / `细分` / `浏览...`）+ 控件悬停说明 841 条（含 1 条此前漏提取的补译）+ 残留 UI 显示标签 41 条（面板/对话框里的短语标签，如 `数据访问`、`包围盒信息`、`投影方向` 等，来自剩余英文复查清单里「可安全补」的部分。其中 `UV in 3D path` / `3D path` 两个极短槽放不下完整译法，采用精简译法 `3D中UV路径` / `路径`）。
- **只改 UI 区**，SDK/代码/数据区一律不动；文件大小不变。
- 黑名单、指针密集区、键名保护、零填充预算检查全部保留；危险词与命令名/枚举值一律不翻（`Protect`、`Strategy`、`Tags`、`Transform`、`Shape`、`Move`、`Rotate`、`Off/Planar/Curved` 等）。
- Grid 面板的分组标题 `Grid` **刻意保留英文**：它与 `Factory / Selection / Pixel / Tile / Group / BBox` 同属内部注册名，且在黑名单中，翻它会触发内部寻址错误。面板内 4 个显示标签后面都跟着独立的 `Prefs./Vars.` 键与 `ZOMID_*_UI` 控件 ID，程序不靠标签文本寻址，因此这 4 个可以安全汉化。

这套规则来自实测：早期曾因误译内部键导致模型空白、旋转失效，现已全部规避。

## 目录说明

```
v648/
├── dist/RizomUV汉化工具_648.exe   # 独立工具（推荐入口，双击即开 GUI 窗口）
├── 一键汉化.bat / 一键还原.bat    # 源码方式一键脚本
├── patch_tool.py                  # 工具核心：GUI + CLI + 校验 / 备份 / 安装 / 还原
├── ui_theme.py                    # 界面样式：配色 / 字体 / 间距 / 组件状态（单一事实来源）
├── build.py                       # 构建引擎：从英文原版一键重建（8 批合一）
├── verified_dict.json             # 723 条已验证安全词条（v10 术语已统一）
├── dicts/blocklist_ui_only.txt    # 危险词黑名单
├── dicts/labels_zh.json           # 41 条残留 UI 显示标签补译（按偏移定位，当前生效）
├── dicts/tooltips_zh.json         # 841 条悬停说明译文（长段落带断行空格；实际写入 825 条，16 条指针密集区跳过）
├── dicts/tooltips_zh_full.json    # 840 条无空格完整译文备份（v7 版）
├── dicts/tooltips_zh_v8_short.json  # 464 条短句版备份（v8 版，可回退）
├── 打包.spec / _gui_launcher.py   # exe 打包配置与启动入口
└── history/                       # 原 4 批分批脚本与旧安装脚本（可复现记录，仅供参考）
```

`build.py` 是 `history/` 下 4 个分批脚本的合一重写版（再追加第 5、6、7、8 批补译），逐级 MD5 校验完全一致。
**v10 术语统一**：旧词表里 `tile` 曾同时译「平铺 / 瓦片」、`pack` 曾译「平铺 / 打包」而界面标签 `Packing` 译「排布」。本版按审查报告的统一标准（`tile→瓦片`、`pack/Packing→排布`）修订 `verified_dict.json` 8 条，最终成品中「平铺 / 打包」已归零。
因为改动落在第 1 批词表，整条链已从英文原版逐级重算并重新验证（每级均满足 UI 区外零改动、文件大小不变）。

**v10.1 回退 17 条风险词**：首版把 58 条全部补译后，RizomUV 报 `The variable is not found: '已选择'` —— `Selected` 这类**纯单词**不只作显示标签，还被当作内部变量名查找。因此回退 15 条纯标识符风格的词（`Selected` / `Edge` / `Vertex` / `Polygon` / `Labels` / `Normals` / `Viewport` / `Amount` / `Steps` / `Boxes` / `Rename` / `Ungroup` / `Outlines` / `Examples` / `Algorithms`），以及 2 条命中黑名单的短语（`Island Properties` / `Islands and groups`），最终保留 41 条含空格或连字符的短语——这类字符串不可能是 Lua 标识符。第 8 批现已与第 1 批一样加载 `blocklist_ui_only.txt`，并在运行时拒绝纯标识符，形成双重防护。
`abbc6933`(英文) → `d1f2e200` → `dbfacc0b` → `fa143b51` → `5474f1a6` → `c81d9c3e` → `f38b0a5d` → `93acbc66`(悬停说明) → `8101756a`(最终，含 41 条残留 UI 显示标签)。

第 7 批的悬停说明按**文件偏移**定位（不按字符串查找），逐槽检查 UI 区边界、独立 NUL 槽、纯 ASCII 原文、零填充预算与指针密度。说明框靠空格换行，中文整串无空格会单行溢出遮挡文字：因此显示宽度 >80 的长段落在中文标点后插入 ASCII 空格作断行点（163 条），每段 ≤80；678 条短句保持原样。另补上一条此前漏提取的说明（`0x6dca920`）。无空格版与短句版分别备份在 `tooltips_zh_full.json`、`tooltips_zh_v8_short.json`。

## 重新打包独立工具（开发者）

**必须用带完整 tkinter 的 Python 打包**。用精简版 Python（例如 WorkBuddy 内置的 `binaries\python`，不含 tkinter）打出的 exe 只有约 7.7 MB，双击会直接报 `ModuleNotFoundError: No module named 'tkinter'`。本机可用的完整版本（用户级安装，含 tkinter 8.6）：

```bash
cd v648
"C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe" -m PyInstaller --noconfirm --distpath dist --workpath build_pyi 打包.spec
```

打包后**先看体积再交付**：正常约 **10.3 MB**；若只有 7.7 MB 左右，就是 tkinter 没打进去，必须换 Python 重打。界面视觉值集中在 `ui_theme.py`，改配色/字号/间距只需改这一处。

自检（GUI 版末尾会等按回车，自动化调用不要直接跑）：

```
dist\RizomUV汉化工具_648.exe --check --exe "英文原版路径"
```

> `build.py` 由 `patch_tool.py` 通过 `importlib` 动态加载，PyInstaller 静态分析看不到，因此打包配置里已把它和词表、黑名单作为数据文件显式打入。修改打包方式时不要漏掉这一步。
