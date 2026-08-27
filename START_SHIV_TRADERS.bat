@echo off
cd /d "%~dp0"
title Shiv Traders - Luxury Manufacturing Website
color 0E

echo =====================================================================
echo           SHIV TRADERS - LUXURY MANUFACTURING PLATFORM
echo         "Building Strong Foundations. Creating Better Spaces."
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
    echo Please install Python 3.10+ or check C:\Users\HP\python311\python.exe
    pause
    exit /b 1
)

echo [1/2] Starting Shiv Traders Flask Server...
echo [2/2] Opening browser at http://127.0.0.1:5000 ...
echo.

:: Launch browser in background after 1 second
start "" "http://127.0.0.1:5000"

echo =====================================================================
echo   Website URL:  http://127.0.0.1:5000
echo   Admin Portal: http://127.0.0.1:5000/admin/login
echo.
echo   Default Admin Email:    admin@shivtraders.com
echo   Default Admin Password: Admin@ShivTraders2026
echo =====================================================================
echo.
echo Server is running live! Keep this window open while using the website.
echo Press CTRL+C to stop the server anytime.
echo.

"%PYTHON_CMD%" app.py

if %errorlevel% neq 0 (
    echo.
    echo Server stopped with error code %errorlevel%.
    pause
)
