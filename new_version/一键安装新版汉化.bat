@echo off
cd /d "%~dp0"
echo ============================================
echo   Install UI patch for NEW RizomUV build
echo   621 terms - backup / replace / verify
echo ============================================
echo.
echo Requesting admin permission. Click YES on the UAC popup...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','E:\A_1\ai\wd\rizom_cn\do_install_newver.ps1' -Verb RunAs -Wait"
echo.
echo ============ Install result ============
type "E:\A_1\ai\wd\rizom_cn\install_result_newver.txt" 2>nul
echo =========================================
echo.
pause
