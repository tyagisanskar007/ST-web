@echo off
cd /d "%~dp0"
title Shiv Traders - Admin Portal Launcher
color 0B

echo =====================================================================
echo           SHIV TRADERS - ADMINISTRATOR MANAGEMENT PORTAL
echo =====================================================================
echo.

:: Detect Python path
set "PYTHON_CMD="
if exist "C:\Users\HP\python311\python.exe" (
    set "PYTHON_CMD=C:\Users\HP\python311\python.exe"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        where py >nul 2>&1
        if %errorlevel% equ 0 (
            set "PYTHON_CMD=py"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not detected on this system.
    pause
    exit /b 1
)

start "" "http://127.0.0.1:5000/admin/login"

echo =====================================================================
echo   Admin Login:   http://127.0.0.1:5000/admin/login
echo   Email:         admin@shivtraders.com
echo   Password:      Admin@ShivTraders2026
echo =====================================================================
echo.
echo Starting backend server...

"%PYTHON_CMD%" app.py

if %errorlevel% neq 0 (
    echo Server stopped with error code %errorlevel%.
    pause
)
