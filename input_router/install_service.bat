@echo off
REM Install Input Router Daemon as a Windows Service using NSSM
REM Download NSSM from https://nssm.cc/download

echo Input Router Daemon - Service Installer
echo ========================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if NSSM exists
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo NSSM not found in PATH.
    echo.
    echo To install as a service, you need NSSM:
    echo 1. Download from https://nssm.cc/download
    echo 2. Extract and add to PATH
    echo 3. Run this script again
    echo.
    echo Alternatively, use Task Scheduler:
    echo 1. Open Task Scheduler
    echo 2. Create Basic Task
    echo 3. Trigger: At startup
    echo 4. Action: Start a program
    echo 5. Program: python
    echo 6. Arguments: %~dp0input_router.py run
    echo 7. Start in: %~dp0
    pause
    exit /b 1
)

set SERVICE_NAME=InputRouterDaemon
set PYTHON_PATH=python
set SCRIPT_PATH=%~dp0input_router.py

echo Installing service: %SERVICE_NAME%
echo Python: %PYTHON_PATH%
echo Script: %SCRIPT_PATH%
echo.

nssm install %SERVICE_NAME% %PYTHON_PATH% "%SCRIPT_PATH%" run
nssm set %SERVICE_NAME% AppDirectory %~dp0
nssm set %SERVICE_NAME% DisplayName "Input Router Daemon"
nssm set %SERVICE_NAME% Description "Routes input from multiple devices to separate editor instances"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

echo.
echo Service installed successfully!
echo.
echo Commands:
echo   nssm start %SERVICE_NAME%    - Start service
echo   nssm stop %SERVICE_NAME%     - Stop service
echo   nssm remove %SERVICE_NAME%   - Uninstall service
echo.
pause
