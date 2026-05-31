@echo off
cd /d "%~dp0"
set PYTHONPATH=%cd%
echo Starting Moka AI Installer at %time%
python installer_wizard\__main__.py
echo.
echo Exit code: %errorlevel%
pause