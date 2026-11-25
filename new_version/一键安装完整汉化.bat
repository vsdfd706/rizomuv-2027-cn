@echo off
cd /d "%~dp0"
echo ============================================
echo   One-click install: full Chinese UI patch
echo   applies all 4 stages in order:
echo     main-621 / toolbar-7 / panel-8 / menu-6
echo   each stage: verify / backup / replace
echo ============================================
echo.
echo Close RizomUV before running. Click YES on the UAC popup.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','%~dp0do_install.ps1' -Verb RunAs -Wait"
echo.
echo ============ Install result ============
type "%~dp0install_result.txt" 2>nul
echo ========================================
echo.
pause
