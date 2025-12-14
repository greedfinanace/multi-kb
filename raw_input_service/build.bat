@echo off
REM Build script for Raw Input Service
REM Requires Visual Studio Build Tools or Visual Studio with C++ workload

echo === Building Raw Input Service ===

REM Check if cl.exe is available
where cl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Visual Studio C++ compiler not found.
    echo Please run this from a Developer Command Prompt or run vcvarsall.bat first.
    echo.
    echo Example: "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
    exit /b 1
)

REM Create output directory
if not exist "build" mkdir build

echo.
echo Compiling console version...
cl /EHsc /std:c++17 /O2 /W4 ^
    /Fe:build\raw_input_service_console.exe ^
    /Fo:build\ ^
    raw_input_service.cpp device_detector.cpp socket_server.cpp ^
    ws2_32.lib hid.lib setupapi.lib user32.lib ^
    /link /SUBSYSTEM:CONSOLE

if %ERRORLEVEL% NEQ 0 (
    echo Console build failed!
    exit /b 1
)

echo.
echo Compiling Windows subsystem version (no console)...
cl /EHsc /std:c++17 /O2 /W4 ^
    /Fe:build\raw_input_service.exe ^
    /Fo:build\ ^
    raw_input_service.cpp device_detector.cpp socket_server.cpp ^
    ws2_32.lib hid.lib setupapi.lib user32.lib ^
    /link /SUBSYSTEM:WINDOWS /ENTRY:wWinMainCRTStartup

if %ERRORLEVEL% NEQ 0 (
    echo Windows build failed!
    exit /b 1
)

echo.
echo === Build Complete ===
echo Output files:
echo   build\raw_input_service_console.exe  (with console window)
echo   build\raw_input_service.exe          (no console window)
echo.
echo Run as Administrator for full functionality.
