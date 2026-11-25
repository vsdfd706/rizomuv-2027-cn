@echo off
cd /d "%~dp0"
echo ============================================
echo   Install toolbar-title patch (7 terms)
echo   backup / replace / verify
echo ============================================
echo.
echo Requesting admin permission. Click YES on the UAC popup...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','E:\A_1\ai\wd\rizom_cn\do_install_toolbar.ps1' -Verb RunAs -Wait"
echo.
echo ============ Install result ============
type "E:\A_1\ai\wd\rizom_cn\install_result_toolbar.txt" 2>nul
echo =========================================
echo.
pause
