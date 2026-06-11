@echo off
setlocal
chcp 65001 >nul 2>&1
title MonGSV - Build Frontend

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "PROJECT_ROOT=%%~fI"
set "FRONTEND_DIR=%PROJECT_ROOT%\Code\GptSov_Front"

echo ========================================
echo   MonGSV - Build Frontend
echo ========================================
echo.
echo Project : %PROJECT_ROOT%
echo Frontend: %FRONTEND_DIR%
echo.

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend package.json not found:
    echo         %FRONTEND_DIR%\package.json
    if /i not "%MON_GSV_NO_PAUSE%"=="1" pause
    exit /b 1
)

cd /d "%FRONTEND_DIR%"

if exist "package-lock.json" (
    if not exist "node_modules" npm ci
) else (
    if not exist "node_modules" npm install
)

npm run build

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Frontend build exited with code %EXIT_CODE%.
if /i not "%MON_GSV_NO_PAUSE%"=="1" pause
exit /b %EXIT_CODE%
