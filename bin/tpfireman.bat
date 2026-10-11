@echo off
set "APP_DIR=%~dp0.."
if /I "%~1"=="version" (
    type "%APP_DIR%\VERSION"
    exit /b 0
)
if /I "%~1"=="uninstall" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%APP_DIR%\uninstall.ps1"
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="update" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%APP_DIR%\update.ps1"
    exit /b %ERRORLEVEL%
)
python "%APP_DIR%\main.py" %*
exit /b %ERRORLEVEL%
