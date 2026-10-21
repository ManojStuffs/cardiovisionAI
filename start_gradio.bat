@echo off
title CardioVision AI — Gradio Space Launcher
echo ==========================================================
echo    CardioVision AI - Gradio Space Local Launcher
echo ==========================================================
echo.
cd /d "%~dp0"

echo Starting Gradio Space on http://localhost:7860 ...
echo Press Ctrl+C in this terminal to stop the server.
echo.

.\venv\Scripts\python.exe app.py
pause
