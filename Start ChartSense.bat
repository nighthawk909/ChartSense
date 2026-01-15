@echo off
title ChartSense Trading Platform
color 0A

echo.
echo  ========================================================
echo     _____ _                _   _____
echo    / ____^| ^|              ^| ^| / ____^|
echo   ^| ^|    ^| ^|__   __ _ _ __^| ^|^| ^(___   ___ _ __  ___  ___
echo   ^| ^|    ^| '_ \ / _` ^| '__^| __\___ \ / _ \ '_ \/ __^|/ _ \
echo   ^| ^|____^| ^| ^| ^| (_^| ^| ^|  ^| ^|_____) ^|  __/ ^| ^| \__ \  __/
echo    \____^|_^| ^|_^|\__,_^|_^|   \__^|_____/ \___^|_^| ^|_^|___/\___^|
echo.
echo    AI-Powered Stock Trading Platform with Auto-Trading
echo  ========================================================
echo.

:: Set the project directory
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Check for Python
echo [*] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] ERROR: Python is not installed or not in PATH!
    echo     Please install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

:: Check/Create Python virtual environment
echo [*] Checking Python environment...
if not exist "api\venv\Scripts\activate.bat" (
    echo.
    echo [+] Creating Python virtual environment...
    cd api
    python -m venv venv
    if errorlevel 1 (
        echo [!] Failed to create virtual environment
        pause
        exit /b 1
    )
    cd ..
    echo     Virtual environment created!
)

:: Install/Update Python dependencies
echo [*] Installing Python dependencies...
cd api
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [!] WARNING: Some Python packages may have failed to install
)
cd ..
echo     Python dependencies installed!

:: Check for .env file and create from example if needed
if not exist "api\.env" (
    echo.
    echo [!] WARNING: api\.env file not found!
    if exist "api\.env.example" (
        echo     Creating .env from .env.example...
        copy "api\.env.example" "api\.env" >nul
        echo.
        echo     IMPORTANT: Edit api\.env and add your API keys:
        echo     - ALPACA_API_KEY and ALPACA_SECRET_KEY for trading
        echo     - OPENAI_API_KEY for AI features (optional)
        echo.
        echo     Get Alpaca keys at: https://app.alpaca.markets
        echo.
    ) else (
        echo     The bot needs your Alpaca API keys to trade.
        echo.
        echo     1. Create api\.env file
        echo     2. Add your Alpaca API keys
        echo        Get keys at: https://app.alpaca.markets
        echo.
    )
    echo     Press any key to continue anyway...
    pause > nul
)

:: Check for Node.js
echo [*] Checking for Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] ERROR: Node.js is not installed or not in PATH!
    echo     Please install Node.js 18+ from https://nodejs.org
    echo.
    pause
    exit /b 1
)

:: Install/Update Node.js dependencies
echo [*] Checking Node.js dependencies...
if not exist "apps\web\node_modules" (
    echo.
    echo [+] Installing Node modules (this may take a minute)...
    cd apps\web
    call npm install
    cd ..\..
    echo     Node modules installed!
) else (
    echo     Node modules found!
)

echo.
echo [1/2] Starting API Server (port 8000)...
start "ChartSense API" cmd /k "cd /d "%PROJECT_DIR%api" && venv\Scripts\activate && python -m uvicorn main:app --reload --port 8000"

:: Wait for API to initialize
echo      Waiting for API to start...
timeout /t 3 /nobreak > nul

echo.
echo [2/2] Starting Web Application (port 5173)...
start "ChartSense Web" cmd /k "cd /d "%PROJECT_DIR%apps\web" && npm run dev"

:: Wait for web app
timeout /t 3 /nobreak > nul

echo.
echo [*] Opening Dashboard in browser...
timeout /t 2 /nobreak > nul
start http://localhost:5173/bot

echo.
echo  ========================================================
echo   ChartSense is now running!
echo  ========================================================
echo.
echo   Dashboard:   http://localhost:5173
echo   Trading Bot: http://localhost:5173/bot
echo   API Docs:    http://localhost:8000/docs
echo.
echo   IMPORTANT: Configure your Alpaca API keys in api\.env
echo              before starting the trading bot!
echo.
echo  ========================================================
echo.
echo   Press any key to close this window...
echo   (The servers will keep running in their own windows)
echo.
pause > nul
