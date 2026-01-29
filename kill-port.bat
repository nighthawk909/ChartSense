@echo off
REM Kill all processes on a specified port
REM Usage: kill-port.bat 8000

if "%1"=="" (
    echo Usage: kill-port.bat PORT
    echo Example: kill-port.bat 8000
    exit /b 1
)

set PORT=%1
echo Killing processes on port %PORT%...

REM Method 1: Use netstat to find PIDs and kill them
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo   Killing PID %%a...
    taskkill /F /PID %%a 2>nul
)

REM Method 2: PowerShell fallback (more reliable for stubborn processes)
powershell -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction Stop; Write-Host '  Killed PID' $_.OwningProcess } catch { } }"

REM Verify
echo.
echo Checking if port %PORT% is now free...
netstat -ano 2>nul | findstr ":%PORT%" | findstr "LISTENING"
if errorlevel 1 (
    echo   Port %PORT% is now free!
) else (
    echo   WARNING: Port %PORT% may still be in use. Try restarting your computer.
)
