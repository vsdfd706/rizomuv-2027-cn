@echo off
cd /d "%~dp0"
echo ============================================
echo   Install Transform panel labels (8 terms)
echo   backup / replace / verify
echo ============================================
echo.
echo IMPORTANT: Close RizomUV before installing.
echo Requesting admin permission. Click YES on the UAC popup...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','E:\A_1\ai\wd\rizom_cn\do_install_panel.ps1' -Verb RunAs -Wait"
echo.
echo ============ Install result ============
type "E:\A_1\ai\wd\rizom_cn\install_result_panel.txt" 2>nul
echo =========================================
echo.
pause
