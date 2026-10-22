@echo off
title CardioVision AI — Local Server Launcher
echo ==========================================================
echo    CardioVision AI - AFib Detection and Cardiac Platform
echo ==========================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found in .\venv!
    echo Please create one: python -m venv venv
    pause
    exit /b 1
)

echo [2/3] Checking frontend build...
if not exist "frontend\dist\index.html" (
    echo Frontend build not found! Building frontend now...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo [3/3] Starting CardioVision AI Server on http://localhost:5000 ...
echo Press Ctrl+C in this terminal to stop the server.
echo.

start http://localhost:5000
.\venv\Scripts\python.exe backend\server.py
pause
