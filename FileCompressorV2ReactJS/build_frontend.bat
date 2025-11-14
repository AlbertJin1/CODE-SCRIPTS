@echo off
:: ------------------------------------------------------------
:: build_frontend.bat
:: 1. Build React (CRA) → frontend\build
:: 2. Copy everything from build → backend\static
:: 3. Show clear success / failure
:: ------------------------------------------------------------

:: ---- 1. Go to the frontend folder --------------------------------
cd /d "%~dp0frontend"
if %errorlevel% neq 0 (
    echo [ERROR] Could not cd into frontend folder
    pause
    exit /b 1
)

:: ---- 2. Install (only if node_modules missing) -------------------
if not exist node_modules (
    echo [INFO] Installing npm packages...
    npm ci
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
)

:: ---- 3. Build the React app --------------------------------------
echo [INFO] Building React app...
npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

:: ---- 4. Copy build → backend\static -------------------------------
set "SRC=%~dp0frontend\build"
set "DST=%~dp0backend\static"

echo [INFO] Copying build to %DST% ...
if exist "%DST%" rmdir /s /q "%DST%"
xcopy /E /I /Y "%SRC%" "%DST%"
if %errorlevel% neq 0 (
    echo [ERROR] Copy failed
    pause
    exit /b 1
)

echo.
echo ================================
echo   Front-end built successfully!
echo   → %DST%
echo ================================
pause