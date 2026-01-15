@echo off
echo ========================================
echo   ChartSense Web App
echo ========================================
echo.

cd /d "%~dp0apps\web"

echo Installing dependencies...
call npm install

echo.
echo Starting development server...
echo Web app will open at http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev

pause
