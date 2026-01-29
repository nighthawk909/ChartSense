@echo off
REM TASK-020 QA: Restart server and test execute-opportunity endpoint
REM Run this script to apply the fix

echo.
echo ========================================
echo TASK-020 QA: Restarting API Server
echo ========================================
echo.

REM Kill existing Python processes (API server)
echo Stopping existing Python processes...
taskkill /F /IM python3.11.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Clear Python cache
echo Clearing Python cache...
cd /d "%~dp0..\..\..\"
for /d /r api %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

REM Start the API server in a new window
echo Starting API server...
start "ChartSense API" cmd /k "cd /d %~dp0..\..\..\api && python -m uvicorn main:app --reload --port 8000"

REM Wait for server to start
echo Waiting 5 seconds for server to start...
timeout /t 5 /nobreak >nul

REM Test the endpoint
echo.
echo ========================================
echo Testing execute-opportunity endpoint...
echo ========================================
curl -s -X POST "http://localhost:8000/api/bot/execute-opportunity?symbol=AAPL&signal=BUY&confidence=75"
echo.
echo.
echo ========================================
echo If you see "success":true above, the fix is working!
echo If you see an error, the bot may not be running or market may be closed.
echo ========================================
pause
