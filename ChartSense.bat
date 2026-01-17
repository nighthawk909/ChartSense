@echo off
title ChartSense Trading Platform

echo.
echo  ========================================================
echo      ChartSense - AI-Powered Trading Platform
echo  ========================================================
echo.

REM Get the directory where this batch file is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo  [1/7] Cleaning up temp files and processes...
echo  --------------------------------------------------------

REM Kill any Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any Node processes on port 5173
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Clear Python cache to ensure fresh imports
if exist "%PROJECT_DIR%api\__pycache__" rd /s /q "%PROJECT_DIR%api\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\routes\__pycache__" rd /s /q "%PROJECT_DIR%api\routes\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\services\__pycache__" rd /s /q "%PROJECT_DIR%api\services\__pycache__" >nul 2>&1

echo         Done.
echo.

echo  [2/7] Checking Python installation...
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

echo  [3/7] Checking Node.js installation...
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

echo  [4/7] Starting API Server (port 8000)...
echo  --------------------------------------------------------
cd /d "%PROJECT_DIR%api"
start "ChartSense API" cmd /k python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
echo         API server starting...
timeout /t 3 /nobreak >nul
echo.

echo  [5/7] Starting Web Application (port 5173)...
echo  --------------------------------------------------------
cd /d "%PROJECT_DIR%apps\web"
start "ChartSense Web" cmd /k npm run dev -- --port 5173
echo         Web app starting...
timeout /t 5 /nobreak >nul
echo.

cd /d "%PROJECT_DIR%"

echo  [6/7] Opening browser...
echo  --------------------------------------------------------
start http://localhost:5173
echo         Browser launched!
echo.

echo  [7/7] Ready!
echo  ========================================================
echo.
echo   Web App:    http://localhost:5173
echo   API Docs:   http://localhost:8000/docs
echo.
echo   Paper Trading: $100,000 virtual funds
echo   Crypto: 24/7 (BTC, ETH, SOL, etc.)
echo.
echo  ========================================================
echo   Press any key to STOP all servers and exit...
echo  ========================================================
pause >nul

echo.
echo  Shutting down servers...

REM Kill the servers
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  Goodbye!
timeout /t 2 /nobreak >nul
