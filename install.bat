@echo off
chcp 65001 >nul
setlocal
REM ============================================================
REM  安装汉化版：把 build_all.py 生成的 out\rizomuv_cn.exe
REM  替换到 RizomUV 安装目录。自动请求管理员权限。
REM  运行前请先关闭 RizomUV。
REM ============================================================
set "ROOT=%~dp0"
set "SRC=%ROOT%out\rizomuv_cn.exe"
set "DIR=C:\Program Files\Rizom Lab\RizomUV 2027.0"
set "DST=%DIR%\rizomuv.exe"
set "BAK=%DIR%\rizomuv_en_backup.exe"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 请求管理员权限...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if not exist "%SRC%" (
  echo [错误] 找不到汉化版：%SRC%
  echo 请先运行 python build_all.py 生成。
  pause
  exit /b 1
)

tasklist /FI "IMAGENAME eq rizomuv.exe" | find /I "rizomuv.exe" >nul
if %errorlevel% equ 0 (
  echo [错误] RizomUV 仍在运行，请先关闭再安装。
  pause
  exit /b 1
)

if not exist "%BAK%" (
  echo 备份英文原版到 %BAK%
  copy /Y "%DST%" "%BAK%" >nul
)
copy /Y "%SRC%" "%DST%" >nul
if errorlevel 1 (
  echo [错误] 复制失败，请检查安装目录权限。
  pause
  exit /b 1
)
echo [完成] 汉化版已安装到 %DST%
pause
