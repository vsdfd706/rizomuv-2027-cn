# RizomUV 2027 简体中文补丁（仅界面 UI）

针对 **RizomUV 2027.0.598（g864535413）** 的简体中文界面补丁。

> **本项目只修改界面显示文字，不改动任何内部运行逻辑。** 加载、展开、排布、旋转、脚本桥接等功能与英文原版完全一致。

---

## ⚠️ 法律与合规声明

- 本仓库**只包含补丁源码**（翻译词典、黑名单、构建脚本），**不包含也不分发 RizomUV 程序本体**。
- 构建时需要你**自己持有正版授权**的英文原版 `rizomuv.exe`。请把该文件自行复制到仓库根目录并改名为 `rizomuv.exe.bak`。
- 请勿把 `rizomuv.exe.bak`、`build/`、`out/` 或任何 exe 文件上传到 GitHub —— 这既违反软件许可协议，也会因文件超过 GitHub 单文件 100 MB 上限而失败。以上路径均已写入 `.gitignore`。
- 本项目仅供个人学习与交流使用。使用者需自行遵守 Rizom Lab 的软件许可协议，作者不承担因使用本补丁产生的任何责任。

---

## 工作原理

补丁直接在 exe 的 **UI 字符串区**（文件偏移约 `0x6d00000`–`0x6e00000`）内，把英文界面文案的原字节替换为中文 UTF-8 字节，并用 `\x00` 填充到原字符串槽末尾。

有几条关键的安全规则（都写在 `src/build.py` 里）：

- **只改 UI 区**：SDK 字符串区、代码区、数据区一律不动。
- **指针密集区跳过**：被内部指针表引用的字符串（命令字段、配置键、面板注册表）是运行时标识符，翻译会导致坏命令 / 坏配置 / 加载失败，自动跳过。
- **键名保护**：后面紧跟 `ZOMID_` / `Vars.` / `Prefs.` 的字符串是变量名，跳过。
- **黑名单**：`dicts/blocklist_ui_only.txt` 列出已知的危险键（如 `Scene`、`Density`、`Tags`、`Strategy`、`Mutations`、`Viewport 3D/UV` 等），翻译它们会造成模型空白、旋转失效等故障，一律不动。
- **槽位预算**：中文字节数加终止符必须能放进原字符串槽，放不下的自动跳过，避免溢出破坏相邻数据。

这套规则是反复实测总结出来的：早期版本曾因误译内部键导致模型加载空白、旋转失效，现已全部规避。

---

## 使用方法

### 环境

- Windows + Python 3（只需标准库，无需 pip 安装依赖）

### 步骤

1. 克隆本仓库：

   ```bash
   git clone <你的仓库地址>.git
   cd rizomuv-2027-cn
   ```

2. 把你的**正版英文原版** `rizomuv.exe` 复制到仓库根目录，改名为 `rizomuv.exe.bak`。

3. 一键构建：

   ```bash
   python build_all.py
   ```

   脚本会校验原版 MD5（应为 `2ddf8d6da2000ae3eac66d7eea59a311`，对应 2027.0.598），然后依次应用全部词典与补丁，最终生成：

   ```
   out/rizomuv_cn.exe
   ```

4. 关闭 RizomUV，双击 `install.bat`（自动请求管理员权限）安装；`restore.bat` 可还原英文原版。

### 验证

用原版 MD5 构建时，产出的 `out/rizomuv_cn.exe` MD5 应为：

```
1a2c16e67fb3a1b595c0fa0622f1940a
```

若一致，说明源码完整、构建成功。

---

## 已汉化的界面范围

- 顶部菜单栏（文件 / 编辑 / 窗口 / 脚本 / 帮助等）
- 各标签页与面板标题（UV 集 / 相似 / 投影 / 展开 / 排布 / 相似等）
- 展开（Unwrap）、排布（Pack）、相似（Similar）、UDIM、Margin、变换等面板的字段、下拉项与提示说明
- 首选项（Preferences）左侧分类及 Viewports 页的常用选项
- 各类悬浮提示（tooltip）与长段说明文字

已翻译 500 余处界面字符串。**出于稳定性刻意保留英文**的项：`Scene`、`Tags`、`Viewport 3D/UV`、`Exporter`、`Log`、`Strategy`、`Mutations`、`Threshold` 等（它们同时被当作内部键或枚举值，翻译会破坏功能）。

---

## 文件结构

```
rizomuv-2027-cn/
├── build_all.py              # 一键构建入口
├── install.bat               # 安装汉化版（需管理员）
├── restore.bat               # 还原英文原版（需管理员）
├── force_patch.txt           # 强制放行的 UI 标签白名单
├── prefs_backup.txt          # 配置键参考（用于跳过危险键）
├── shortbuf.txt              # 固定小缓冲区标签清单
├── dicts/
│   ├── tr_core.json          # 核心界面词典
│   ├── tr_phrase.json        # 短语 / 说明词典
│   ├── menu_all.json         # 菜单项
│   ├── batch_all.json        # 面板批量词条
│   └── blocklist_ui_only.txt # 危险键黑名单
└── src/
    ├── build.py              # 基础词典构建器
    ├── patch_menu.py         # 菜单
    ├── patch_tooltip.py      # 悬浮说明
    ├── patch_all.py          # 面板批量词
    ├── patch_udim.py         # UDIM 面板
    ├── patch_redbox.py       # 红框区域字段
    ├── patch_similar.py      # 相似面板
    ├── patch_margin.py       # Margin 说明
    ├── patch_pack.py         # 排布面板
    ├── patch_unwrap.py       # 展开面板
    ├── patch_tabs2.py        # 标签页按钮
    ├── patch_menu2.py        # 窗口菜单续翻
    └── patch_prefs.py        # 首选项页
```

---

## 已知说明

- 3ds Max → RizomUV 桥接脚本可能报 `The variable is not found: 'Prefs.UI.Display.UnfoldOptimize'`。这是桥接脚本调用了 2027 已移除的旧变量，**英文原版同样会报**，与汉化无关，仅导致自动全选边未执行，可忽略。
- 导入含退化面的模型时日志可能出现 `Bad corner ID in CBox2D::GetGeometryPoint`，这是几何拓扑告警，英文原版同样存在，与汉化无关。
