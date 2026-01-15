@echo off
setlocal enabledelayedexpansion
title ChartSense Trading Platform

echo.
echo  ========================================================
echo   ____ _                _   ____
echo  / ___^| ^|__   __ _ _ __^| ^|_/ ___|  ___ _ __  ___  ___
echo  ^| ^|   ^| '_ \ / _` ^| '__^| __\___ \ / _ \ '_ \/ __|/ _ \
echo  ^| ^|___^| ^| ^| ^| (_^| ^| ^|  ^| ^|_ ___) ^|  __/ ^| ^| \__ \  __/
echo   \____^|_^| ^|_^|\__,_^|_^|   \__^|____/ \___^|_^| ^|_^|___/\___^|
echo.
echo   AI-Powered Trading Platform
echo  ========================================================
echo.

REM Get the directory where this batch file is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo  [1/6] Cleaning up existing processes...
echo  --------------------------------------------------------

REM Kill any Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any Node processes on port 5173
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo         Done.
echo.

echo  [2/6] Checking Python installation...
echo  --------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo         ERROR: Python is not installed or not in PATH
    echo         Please install Python from https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo         %%i found
echo.

echo  [3/6] Checking Node.js installation...
echo  --------------------------------------------------------
node --version >nul 2>&1
if errorlevel 1 (
    echo         ERROR: Node.js is not installed or not in PATH
    echo         Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo         Node.js %%i found
echo.

echo  [4/6] Starting API Server (port 8000)...
echo  --------------------------------------------------------
start "ChartSense API Server" /min cmd /c "cd /d "%PROJECT_DIR%api" && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo         API server starting in background...
timeout /t 3 /nobreak >nul
echo.

echo  [5/6] Starting Web Application (port 5173)...
echo  --------------------------------------------------------
start "ChartSense Web App" /min cmd /c "cd /d "%PROJECT_DIR%apps\web" && npm run dev -- --port 5173 --host"
echo         Web app starting in background...
timeout /t 5 /nobreak >nul
echo.

echo  [6/6] Opening browser...
echo  --------------------------------------------------------
start "" http://localhost:5173
echo         Browser launched!
echo.

echo  ========================================================
echo   ChartSense is now running!
echo  ========================================================
echo.
echo   Web App:    http://localhost:5173
echo   API Docs:   http://localhost:8000/docs
echo.
echo   Paper Trading Account: $100,000 virtual funds
echo   Crypto Trading: 24/7 (BTC, ETH, SOL, etc.)
echo.
echo  --------------------------------------------------------
echo   Press any key to STOP all servers and exit...
echo  ========================================================
pause >nul

echo.
echo  Shutting down servers...

REM Kill the servers we started
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  Goodbye!
timeout /t 2 /nobreak >nul
exit /b 0
