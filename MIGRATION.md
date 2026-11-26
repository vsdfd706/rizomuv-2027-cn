# 换电脑迁移指南

本仓库的汉化工具**不绑定设备**，换电脑无需改代码、无需重新配置账号或环境变量。
下面按你的使用方式给出需要带走的东西和验证步骤。

## 一、只需要"在新电脑汉化 RizomUV"（绝大多数情况）

**带走一个文件就够**：`v648/dist/RizomUV汉化工具_648.exe`

它是自包含的——构建所需的词表（`verified_dict.json`）、黑名单（`dicts/blocklist_ui_only.txt`）、构建脚本（`build.py`）都已打进 exe 内部，运行时解压到临时目录，不读取仓库里的任何文件，也不依赖本机路径。

已备好一个便携包：`E:\A_1\ai\wd\RizomUV汉化工具_648_换机包.zip`（exe + 使用说明），拷到新电脑解压即用。

新机步骤：
1. 安装**正版 RizomUV 2027.0.648 Win 英文原版**（工具只读取、不分发本体）。
2. 完全关闭 RizomUV。
3. 双击 exe → 若"英文原版"是绿点，直接点「一键汉化」；若是红点，用「选择原版文件」手动指定，再点「一键汉化」。
4. 看到"全部完成"。还原用「一键还原」。

**无需在新电脑安装**：Python、pip、任何第三方库、Git（除非要继续开发）。

## 二、要在新电脑继续开发 / 重新打包 exe

带走**整个仓库**（`git clone` 或整个目录拷贝）。需要额外准备：

| 项 | 说明 | 换机是否要改 |
|---|---|---|
| Python 3 | 源码/bat 方式需要；仅标准库依赖 | 装上即可，`requirements.txt` 无需改 |
| 带完整 tkinter 的 Python + PyInstaller | **仅重新打包 GUI exe 时需要**；精简版缺 `init.tcl` 会在启动报错 | 新机装好完整 Python 即可；打包命令见 `v648/README.md` |
| 路径 | 代码里只有 `C:\Program Files` / `C:\Users\Public` 等 Windows 通用路径，且都先读环境变量、有兜底 | ❌ 不用改 |
| 环境变量 | `ProgramFiles`、`USERPROFILE`、`PUBLIC`（Windows 标准） | ❌ 自动适配 |
| 账号 / token / 授权 | 代码与配置中无任何 token、密码、API key | ❌ 无需配置 |
| 设备绑定 | 无机器码、无硬件绑定。MD5 是**文件版本校验**不是设备绑定 | ❌ 不用改 |

注意：工具只支持 **Windows**（依赖 `winreg` / `tasklist` / `Program Files` 语义），不能移植到 macOS / Linux。

## 三、隐私与历史路径

- `v648/`（在维护的版本）：无任何本机路径或个人标识，干净。
- `v598/prefs_backup.txt`：含旧电脑的历史文件路径（`C:\Users\ASUS\...`、企业微信缓存、3dsMax 目录等）。它只是 RizomUV 的**配置键参考**，只被正则提取键名，路径值不参与任何逻辑；且 v598 已不维护、不在换机包内。**换机包不包含它**，因此不会把旧路径带到新机。
- 本仓库无任何账号、token、授权信息。

## 四、换机后验证步骤

按你的使用方式二选一：

**仅使用 exe**：
1. 命令行运行 `RizomUV汉化工具_648.exe --check --exe "英文原版的完整路径"`，显示"构建自检：通过 ✓"且 MD5 为 `dbcc0c42…` 即正常。
2. 图形界面双击能正常开窗（验证 tkinter 打包完整，无黑框、无报错）。
3. 实际汉化一次，再点「一键还原」，确认恢复英文原版。

**继续开发 / 打包**：
1. `python -m py_compile patch_tool.py build.py ui_theme.py`（在 `v648/` 下）通过。
2. `python patch_tool.py --selftest --exe "英文原版路径"` 显示自检通过。
3. 重新打包：`python -m PyInstaller --noconfirm --distpath dist --workpath build_pyi 打包.spec`，产出的 exe `--check` 通过。
4. `git remote -v` 确认远程地址（克隆过来自动配置；换机后如需推送，凭据是你本机的 GitHub 登录，不在仓库内）。

## 五、已知的环境问题（与换机无关，供排障）

- 推送时若遇 `CONNECT tunnel failed 502` / `schannel` 错误，是本机代理问题，不是仓库问题；可临时绕过代理：`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY git -c http.proxy= push origin master`。
