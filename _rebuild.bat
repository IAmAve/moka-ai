REM Moka AI Installer Quick Build
REM ================================================
REM Prerequisites: Python 3.10+ with:
REM   pip install pyinstaller dearpygui yaml jinja2 psutil screeninfo
REM
REM Usage: Double-click this file OR run in terminal:
REM   _rebuild.bat

@echo off
cd /d "d:\Ave\Documents\PROJECTS\moka-ai"

echo Building MokaAI-Setup.exe...
python -m PyInstaller --clean --noconfirm MokaAI-Setup.spec