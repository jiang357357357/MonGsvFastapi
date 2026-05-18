@echo off
chcp 65001 >nul 2>&1
title MonGSV - ElaWidget

set "APP_DIR=D:\code\model\MonGSV"
set "APP_EXE=%APP_DIR%\Config\ElaWidgetTools\ElaWidget\bin\appElaWidget.exe"

echo ========================================
echo   MonGSV - ElaWidget Launcher
echo ========================================
echo.
echo ????: %APP_DIR%
echo ????: %APP_EXE%
echo.

if not exist "%APP_EXE%" (
    echo [??] ???????!
    echo        %APP_EXE%
    pause
    exit /b 1
)

cd /d "%APP_DIR%"
start "" "%APP_EXE%"