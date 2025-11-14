@echo off
cd /d %~dp0

:: 1. Build front-end
call build_frontend.bat

:: 2. Freeze Python
pyinstaller --clean --noconfirm pyinstaller.spec

echo.
echo ==============================
echo   CompressMaster.exe ready!
echo   → dist\CompressMaster.exe
echo ==============================
pause