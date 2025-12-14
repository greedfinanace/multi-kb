@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
::  Multi-User Input Router - Startup Script
::  Launches all services and opens the Control Panel
:: ============================================================================

title Multi-User Input Router - Launcher

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════╗
echo  ║                                                                       ║
echo  ║            🎮  MULTI-USER INPUT ROUTER  🎮                            ║
echo  ║                                                                       ║
echo  ║         One PC. Multiple keyboards. Multiple coders.                  ║
echo  ║                                                                       ║
echo  ╚═══════════════════════════════════════════════════════════════════════╝
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  [!] WARNING: Not running as Administrator
    echo  [!] Some features may not work correctly.
    echo  [!] Right-click start.bat and select "Run as administrator"
    echo.
    pause
)

:: Get script directory
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo  [1/5] Checking prerequisites...
echo.

:: Check Node.js
where node >nul 2>&1
if %errorLevel% neq 0 (
    echo  [X] Node.js not found! Please install Node.js 18+
    echo      https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do echo  [OK] Node.js %%i

:: Check Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo  [X] Python not found! Please install Python 3.10+
    echo      https://python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo  [OK] %%i

echo.
echo  [2/5] Building Raw Input Service...
echo.

:: Build C++ service if exe doesn't exist
if not exist "%ROOT_DIR%raw_input_service\raw_input_service_console.exe" (
    echo  [..] Compiling C++ service...
    
    :: Try to find Visual Studio
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
    )
    
    pushd "%ROOT_DIR%raw_input_service"
    if exist build.bat (
        call build.bat
    ) else (
        echo  [X] build.bat not found in raw_input_service folder
        popd
        pause
        exit /b 1
    )
    popd
    
    if not exist "%ROOT_DIR%raw_input_service\raw_input_service_console.exe" (
        echo  [X] Build failed! Please build manually using Visual Studio Developer Command Prompt
        pause
        exit /b 1
    )
)
echo  [OK] Raw Input Service ready

echo.
echo  [3/5] Installing Node.js dependencies...
echo.

pushd "%ROOT_DIR%api_server"
if not exist node_modules (
    echo  [..] Running npm install...
    call npm install >nul 2>&1
    if %errorLevel% neq 0 (
        echo  [X] npm install failed!
        popd
        pause
        exit /b 1
    )
)
echo  [OK] Node.js dependencies installed
popd

echo.
echo  [4/5] Starting services...
echo.

:: Start Raw Input Service
echo  [..] Starting Raw Input Service (port 9999)...
start "Raw Input Service" /min cmd /c "cd /d "%ROOT_DIR%raw_input_service" && raw_input_service_console.exe"
timeout /t 2 /nobreak >nul
echo  [OK] Raw Input Service started

:: Start Input Router Daemon
echo  [..] Starting Input Router Daemon (port 8080)...
start "Input Router Daemon" /min cmd /c "cd /d "%ROOT_DIR%input_router" && python input_router.py run"
timeout /t 2 /nobreak >nul
echo  [OK] Input Router Daemon started

:: Start API Server
echo  [..] Starting API Server (port 3000)...
start "API Server" /min cmd /c "cd /d "%ROOT_DIR%api_server" && node server.js"
timeout /t 2 /nobreak >nul
echo  [OK] API Server started

echo.
echo  [5/5] Opening Control Panel...
echo.

:: Wait for API server to be ready
timeout /t 2 /nobreak >nul

:: Open Control Panel in browser
start "" "http://localhost:3000"
start "" "%ROOT_DIR%control_panel\index.html"

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════╗
echo  ║                                                                       ║
echo  ║   ✅  ALL SERVICES RUNNING                                            ║
echo  ║                                                                       ║
echo  ║   Raw Input Service .... localhost:9999                               ║
echo  ║   Input Router Daemon .. localhost:8080                               ║
echo  ║   API Server ........... localhost:3000                               ║
echo  ║   Control Panel ........ Opened in browser                            ║
echo  ║                                                                       ║
echo  ║   Press any key to STOP all services and exit.                        ║
echo  ║                                                                       ║
echo  ╚═══════════════════════════════════════════════════════════════════════╝
echo.

pause >nul

echo.
echo  Stopping services...

:: Kill all started processes
taskkill /FI "WINDOWTITLE eq Raw Input Service*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Input Router Daemon*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq API Server*" /F >nul 2>&1

echo  [OK] All services stopped
echo.
echo  Goodbye!
timeout /t 2 /nobreak >nul
exit /b 0
