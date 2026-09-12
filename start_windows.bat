@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 scripts\setup.py
    goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python scripts\setup.py
    goto end
)

echo [TIP] Python 3 not found. Opening download page...
echo       Please install Python 3.9+ (check "Add to PATH"), then run this file again.
start https://www.python.org/downloads/

:end
echo.
pause
