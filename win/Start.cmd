@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
if not exist "runtime\python.exe" (
  echo [ERROR] Windows Python runtime is missing. Copy the complete win folder.
  pause
  exit /b 1
)
"runtime\python.exe" -s "launcher.py" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
