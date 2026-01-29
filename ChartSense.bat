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

REM Kill ALL Python processes that might be running uvicorn
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ChartSense API*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq uvicorn*" >nul 2>&1

REM Kill any processes on port 8000 and 8001
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any Node processes on port 5173
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Wait a moment for ports to release
timeout /t 2 /nobreak >nul

REM Clear Python cache to ensure fresh imports
if exist "%PROJECT_DIR%api\__pycache__" rd /s /q "%PROJECT_DIR%api\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\routes\__pycache__" rd /s /q "%PROJECT_DIR%api\routes\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\services\__pycache__" rd /s /q "%PROJECT_DIR%api\services\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\models\__pycache__" rd /s /q "%PROJECT_DIR%api\models\__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%api\database\__pycache__" rd /s /q "%PROJECT_DIR%api\database\__pycache__" >nul 2>&1

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

REM Check if port 8000 is still in use (zombie processes)
set "API_PORT=8000"
netstat -ano 2>nul | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo  [!] Port 8000 still in use by zombie processes
    echo      Falling back to port 8001...
    set "API_PORT=8001"
)

echo  [4/7] Starting API Server (port %API_PORT%)...
echo  --------------------------------------------------------
cd /d "%PROJECT_DIR%api"
start "ChartSense API" cmd /k python -m uvicorn main:app --host 0.0.0.0 --port %API_PORT% --reload
echo         API server starting on port %API_PORT%...
timeout /t 3 /nobreak >nul
echo.

echo  [5/7] Starting Web Application (port 5173)...
echo  --------------------------------------------------------
REM Write the API port to .env file for vite to pick up
echo VITE_API_PORT=%API_PORT%> "%PROJECT_DIR%apps\web\.env"

cd /d "%PROJECT_DIR%apps\web"
start "ChartSense Web" cmd /k npm run dev -- --port 5173
echo         Web app starting (connecting to API on port %API_PORT%)...
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
echo   API Docs:   http://localhost:%API_PORT%/docs
echo   Backtest:   http://localhost:5173/backtest
echo.
echo   Paper Trading: $100,000 virtual funds
echo   Crypto: 24/7 (BTC, ETH, SOL, etc.)
echo.
if "%API_PORT%"=="8001" (
    echo  [!] NOTE: Using port 8001 due to zombie processes on 8000.
    echo      Restart your computer to fully clear zombie processes.
    echo.
)
echo  ========================================================
echo   Press any key to STOP all servers and exit...
echo  ========================================================
pause >nul

echo.
echo  Shutting down servers...

REM Kill the servers on both possible ports
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Clean up the .env file
del "%PROJECT_DIR%apps\web\.env" >nul 2>&1

echo  Goodbye!
timeout /t 2 /nobreak >nul
