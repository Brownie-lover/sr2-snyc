@echo off
title Slime Rancher 2 Save Sync Launcher
cd /d "%~dp0"

echo ================================================
echo    Slime Rancher 2: Save Sync ^& Launcher
echo ================================================
echo.

python slime_sync_launcher.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] An error occurred during launch/sync.
    pause
)