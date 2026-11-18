@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
if not exist "runtime\python.exe" (
  echo [ERROR] Windows Python runtime is missing.
  pause
  exit /b 1
)
"runtime\python.exe" -s "diagnose.py" %*
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
