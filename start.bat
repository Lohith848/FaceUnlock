@echo off
REM FaceUnlock Startup Script
REM This script starts the FaceUnlock service

echo ========================================
echo FaceUnlock - Face Recognition Unlock
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

REM Check if profile exists
if not exist "data\profile.pkl" (
    echo [WARNING] Face profile not found!
    echo Please run register.py first to create your face profile
    echo.
    echo Starting registration...
    python register.py
    if errorlevel 1 (
        echo [ERROR] Registration failed
        pause
        exit /b 1
    )
)

REM Start the unlock service
echo Starting FaceUnlock service...
echo Press Ctrl+C to stop
echo.
python unlock.py

if errorlevel 1 (
    echo.
    echo [ERROR] FaceUnlock service stopped with error
    pause
)

exit /b 0
