@echo off
:: Check for Administrator privileges
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo This script requires Administrator privileges.
    echo Please right-click and select "Run as Administrator".
    pause
    exit /b
)

echo ========================================================
echo   Kriplani Backup Agent - Uninstaller
echo ========================================================
echo.

set "AGENT_EXE=KriplaniBackupAgent.exe"
set "TASK_NAME=KriplaniBackupAgent"

echo 1. Stopping running Agent processes...
taskkill /IM "%AGENT_EXE%" /F 

echo.
echo 2. Removing Scheduled Task...
schtasks /Delete /TN "%TASK_NAME%" /F

echo.
echo 3. Cleaning up Startup Registry (Legacy)...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "KriplaniBackupAgent" /f >nul 2>&1

echo.
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Agent has been removed from startup and stopped.
    echo You can now safely delete the folder if desired.
) else (
    echo [INFO] Cleanup finished (some items might not have existed).
)

pause
