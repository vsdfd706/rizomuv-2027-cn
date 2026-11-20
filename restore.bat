@echo off
chcp 65001 >nul
setlocal
REM ============================================================
REM  还原英文原版：用 rizomuv_en_backup.exe 恢复安装目录。
REM  自动请求管理员权限。运行前请先关闭 RizomUV。
REM ============================================================
set "DIR=C:\Program Files\Rizom Lab\RizomUV 2027.0"
set "DST=%DIR%\rizomuv.exe"
set "BAK=%DIR%\rizomuv_en_backup.exe"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 请求管理员权限...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if not exist "%BAK%" (
  echo [错误] 找不到英文原版备份：%BAK%
  pause
  exit /b 1
)

tasklist /FI "IMAGENAME eq rizomuv.exe" | find /I "rizomuv.exe" >nul
if %errorlevel% equ 0 (
  echo [错误] RizomUV 仍在运行，请先关闭再还原。
  pause
  exit /b 1
)

copy /Y "%BAK%" "%DST%" >nul
if errorlevel 1 (
  echo [错误] 还原失败，请检查安装目录权限。
  pause
  exit /b 1
)
echo [完成] 已还原为英文原版。
pause
