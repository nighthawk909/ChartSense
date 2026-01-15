@echo off
echo ========================================
echo   Starting ChartSense
echo   (API Server + Web App)
echo ========================================
echo.

echo Starting API Server in background...
start "ChartSense API" cmd /c "cd /d "%~dp0" && "ChartSense API Server.bat""

echo Waiting for API to start...
timeout /t 5 /nobreak > nul

echo Starting Web App...
start "ChartSense Web" cmd /c "cd /d "%~dp0" && "ChartSense Web App.bat""

echo.
echo ========================================
echo   ChartSense is starting!
echo   - API: http://localhost:8000
echo   - Web: http://localhost:5173
echo ========================================
