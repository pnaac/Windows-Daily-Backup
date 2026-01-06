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
echo   Kriplani Backup Agent - Service Installer
echo ========================================================
echo.

set "AGENT_EXE=KriplaniBackupAgent.exe"
set "TASK_NAME=KriplaniBackupAgent"

if not exist "%AGENT_EXE%" (
    echo [ERROR] %AGENT_EXE% not found in current directory!
    echo Please run this script in the same folder as the Agent executable.
    pause
    exit /b
)

echo 1. Stopping existing instances...
taskkill /IM "%AGENT_EXE%" /F >nul 2>&1

echo 2. Removing existing task (if any)...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

echo 3. Creating Scheduled Task...
:: Logic:
:: /SC ONSTART - Runs when the system boots (even before login)
:: /RL HIGHEST - Runs with Admin rights
:: /RU SYSTEM - Runs as the SYSTEM account (no password expiry)
:: /TR ... - The path to the exe
set "CWD=%~dp0"
set "FULL_PATH=%CWD%%AGENT_EXE%"

schtasks /Create /TN "%TASK_NAME%" /SC ONSTART /RL HIGHEST /RU SYSTEM /TR "'%FULL_PATH%'"

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Task created successfully!
    echo The Agent will now start automatically whenever the server turns on.
    echo.
    echo 4. Starting Agent now...
    schtasks /Run /TN "%TASK_NAME%"
) else (
    echo [ERROR] Failed to create task.
)

pause
