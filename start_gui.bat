@echo off
REM FaceUnlock GUI Launcher
REM This script launches the FaceUnlock graphical interface

echo ========================================
echo FaceUnlock - GUI Launcher
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://python.org
    pause
    exit /b 1
)

REM Launch GUI
echo Launching FaceUnlock GUI...
python gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] GUI failed to start
    pause
)

exit /b 0
