@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
REM ============================================================
REM  一键汉化.bat —— 自动选原版、建虚拟环境、装依赖、备份、构建、安装、建快捷方式
REM  版本不匹配会明确停止并说明原因，不会抛 Python 错误。
REM  运行前请先关闭 RizomUV。
REM ============================================================
title RizomUV 2027 一键汉化

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM ---- 1) 自动请求管理员权限（安装需要写 Program Files）----
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 请求管理员权限...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo ============================================================
echo   RizomUV 2027 简体中文一键汉化
echo ============================================================
echo.

REM ---- 2) 定位 Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
  echo [错误] 没有找到 Python 3。
  echo        请安装 Python 3（https://www.python.org/downloads/），安装时勾选 Add to PATH。
  echo        或者：直接使用 dist\RizomUV汉化工具.exe，无需 Python。
  pause
  exit /b 2
)

REM ---- 3) 建立虚拟环境（首次运行）----
if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo [1/5] 建立虚拟环境...
  python -m venv "%ROOT%.venv"
  if errorlevel 1 (
    echo [错误] 虚拟环境创建失败。
    pause
    exit /b 2
  )
) else (
  echo [1/5] 虚拟环境已存在，跳过。
)

set "PY=%ROOT%.venv\Scripts\python.exe"

REM ---- 4) 安装依赖（本项目仅需标准库，此步通常一闪而过）----
echo [2/5] 检查依赖...
"%PY%" -m pip install --quiet -r "%ROOT%requirements.txt" >nul 2>&1

REM ---- 5) 调用工具：自动选原版 / 校验版本 / 备份 / 构建 / 安装 / 快捷方式 ----
echo [3/5] 校验版本并构建（约需十几秒）...
echo.
"%PY%" "%ROOT%patch_tool.py" --install
set "RC=%errorlevel%"
echo.

if not "%RC%"=="0" (
  echo [停止] 汉化未完成（代码 %RC%）。上方已说明具体原因。
  echo         常见原因：找不到正确的英文原版、版本不是 2027.0.598、或 RizomUV 未关闭。
  pause
  exit /b %RC%
)

echo [4/5] 安装完成，桌面快捷方式已创建。
echo [5/5] 全部完成。
echo.
echo 现在可以启动 RizomUV，界面已是简体中文。
echo 想恢复英文原版：双击“一键还原.bat”。
echo.
pause
