@echo off
title CardioVision AI — Instant Public External Sharing
echo ==========================================================
echo    CardioVision AI - Instant Public External Tunnel
echo ==========================================================
echo.
echo This tool exposes your local running CardioVision AI (port 5000)
echo to an external HTTPS URL accessible from ANY smartphone, laptop,
echo or external reviewer worldwide.
echo.
echo Make sure the local server is running (run_local.bat) before continuing!
echo.
echo Select your preferred free tunnel method:
echo   [1] LocalTunnel (No account needed, requires Node.js/npx)
echo   [2] Cloudflare Tunnel (Quick, secure, no account needed)
echo   [3] Ngrok (Requires free ngrok installed)
echo.
set /p choice="Enter choice [1, 2, or 3]: "

if "%choice%"=="1" (
    echo.
    echo Starting LocalTunnel on port 5000...
    echo If prompted with an endpoint password, your public IP is shown by localtunnel.
    npx localtunnel --port 5000
) else if "%choice%"=="2" (
    echo.
    echo Starting Cloudflare Tunnel on port 5000...
    cloudflared tunnel --url http://localhost:5000
) else if "%choice%"=="3" (
    echo.
    echo Starting Ngrok on port 5000...
    ngrok http 5000
) else (
    echo Invalid choice.
)

pause
