# 新版 RizomUV 2027 exe 汉化补丁链

本目录保存针对**新版 RizomUV 2027 exe**（英文原版 MD5 `abbc69339a373f08cbc3507111d97fbf`）的界面汉化补丁与安装脚本，与仓库根目录针对旧版 exe 的工具相互独立。

## 一键安装

只有一个入口：**`一键安装完整汉化.bat`**。双击后按提示同意 UAC 提权即可，它会自动按顺序完成全部 4 批汉化；每批都做 MD5 校验、自动备份、替换、复核，任一环节不符立即停止并写入 `install_result.txt`。

- 运行前请**完全关闭 RizomUV**。
- 若当前已是最终汉化版（`ef85533b…`），脚本会写 `RESULT=ALREADY_INSTALLED`，不重复安装。
- 4 个分阶段 exe 优先从本脚本所在目录读取；找不到时回退到构建目录 `E:\A_1\ai\wd\rizom_cn`。换机使用时把 `rizomuv_new_cn*.exe` 放到本目录即可。
- 结果见同目录 `install_result.txt`。

## 补丁链构成（内部顺序）

这 4 批是**逐批叠加**的，后一批的 exe 包含前一批的全部改动。统一安装脚本内部仍按此顺序应用并逐级校验，不能跳批、不能混用旧版工具：

| 顺序 | 内容 | 构建脚本 | 安装后 MD5 |
|---|---|---|---|
| 0 | 英文原版（使用者自备正版） | — | `abbc69339a373f08cbc3507111d97fbf` |
| 1 | 主汉化迁移（621 词） | `build_new_version.py` | `cf53e1496873dffba10983d180a0cdcf` |
| 2 | 顶部工具栏 7 个分组标题 | `patch_toolbar_titles.py` | `8018ad29b03772d8b51f8c676220e334` |
| 3 | Transform 面板 8 个界面标签 | `patch_transform_panel.py` | `651a25b166ab27091f6dcc0695756529` |
| 4 | 菜单 6 个界面标签 | `patch_menu_safe6.py` | `ef85533b797c7fc841e9c26bd676efae` |

## 安全原则

- 只改 UI 字符串区 `0x6d00000–0x6e20000`，区外零改动，文件大小不变。
- UTF-8 中文写入原有零填充槽，绝不越界、绝不加长文件。
- 危险词与命令名/枚举值一律不翻：`Protect`、`Strategy`、`Tags`、`Transform`、`Shape`、`Move`、`Rotate`、`Off/Planar/Curved` 等。
- 每批都从已装版本派生，只动当批的少数几个独立槽位。

## 说明

- `verified_dict.json` 是从旧版"最终完整版"与英文原版差分提取的 723 条已验证安全词条，主迁移据此写入 621 条。
- `extract_verified_dict.py` 用于从旧版差分重新生成词表；`build_new_version.py` 与 3 个 `patch_*.py` 是本目录 4 个分阶段 exe 的可复现构建脚本。
- 这些脚本不修改任何程序逻辑、配置键或内部命令名，仅替换界面显示的文字。
