@echo off
setlocal
chcp 65001 >nul 2>&1
title MonGSV - Start

set "PROJECT_ROOT=%~dp0"
set "LAUNCHER=%PROJECT_ROOT%Script\Cmd\Win\start.cmd"

if not exist "%LAUNCHER%" (
    echo [ERROR] Launcher not found:
    echo         %LAUNCHER%
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
call "%LAUNCHER%" %*
exit /b %ERRORLEVEL%
