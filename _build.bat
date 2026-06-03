@echo off
echo ================================================
echo Moka AI Installer - Build Script
echo ================================================
echo.
cd /d "d:\Ave\Documents\PROJECTS\moka-ai"

REM Activate venv & rebuild
echo [*] Cleaning old dist/build...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

echo [*] Building MokaAI-Setup.exe (this takes ~2-3 min)...
python -m PyInstaller --clean --noconfirm MokaAI-Setup.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [FAIL] Build failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Build complete!
if exist "dist\MokaAI-Setup.exe" (
    for %%A in ("dist\MokaAI-Setup.exe") do echo     Size: %%~zA bytes
    echo.
    echo     Output: dist\MokaAI-Setup.exe
    echo.
    echo Run the installer now? Double-click:
    echo     dist\MokaAI-Setup.exe
)
echo.
echo NOTE: After running, check the log at:
echo   %%TEMP%%\moka_install.log
echo.
pause