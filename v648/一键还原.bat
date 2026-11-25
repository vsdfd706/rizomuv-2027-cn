@echo off
chcp 65001 >nul
setlocal
REM ============================================================
REM  一键还原.bat —— 把 RizomUV 恢复为英文原版
REM  运行前请先关闭 RizomUV。
REM ============================================================
title RizomUV 2027.0.648 一键还原

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM ---- 自动请求管理员权限 ----
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 请求管理员权限...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo ============================================================
echo   RizomUV 2027.0.648 一键还原（恢复英文原版）
echo ============================================================
echo.

set "PY=%ROOT%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%ROOT%patch_tool.py" --restore
set "RC=%errorlevel%"
echo.

if not "%RC%"=="0" (
  echo [停止] 还原未完成（代码 %RC%）。上方已说明具体原因。
  pause
  exit /b %RC%
)

echo 全部完成：已恢复英文原版。
pause
