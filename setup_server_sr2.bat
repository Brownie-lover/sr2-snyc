@echo off
title Save Sync Server Setup ^& Launcher
cd /d "%~dp0"

echo ================================================
echo     Setting up Node.js ^& Ngrok Save Server
echo ================================================
echo.

:: 1. Create package.json if missing
if not exist "package.json" (
    echo [*] Creating package.json...
    call npm init -y >nul
)

:: 2. Install Node dependencies
echo [*] Installing Node.js packages (express, multer)...
call npm install express multer

echo.
echo ================================================
echo     Launching Node Server ^& Ngrok Tunnel...
echo ================================================
echo.

:: 3. Launch Node Server in a new window
start "Node.js Express Server" cmd /k "node server.js"

:: 4. Launch Ngrok in this window
ngrok http --url=jaunt-happiness-tinsmith.ngrok-free.dev 3000

pause