@echo off
setlocal
chcp 65001 >nul 2>&1
title MonGSV - Start

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "PROJECT_ROOT=%%~fI"
set "LAUNCHER=%PROJECT_ROOT%\Code\Main\launch.py"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"

echo ========================================
echo   MonGSV - Production Launcher
echo ========================================
echo.
echo Project : %PROJECT_ROOT%
echo Launcher: %LAUNCHER%
echo.

if not exist "%LAUNCHER%" (
    echo [ERROR] Launcher not found:
    echo         %LAUNCHER%
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%LAUNCHER%" %*
) else (
    python "%LAUNCHER%" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo MonGSV exited with code %EXIT_CODE%.
if /i not "%MON_GSV_NO_PAUSE%"=="1" pause
exit /b %EXIT_CODE%
