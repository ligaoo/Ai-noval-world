@echo off
chcp 65001 >nul
title Novel Simulator V5.2

:MENU
cls
echo.
echo ===========================================================
echo              Novel Simulator V5.2
echo ===========================================================
echo.
echo   [1] Start All Services (Recommended)
echo   [2] Backend API Only
echo   [3] Frontend Web Only
echo   [4] Install Dependencies
echo   [5] Help
echo   [0] Exit
echo.
echo ===========================================================
echo.
set /p choice="Please select [0-5]: "

if /i "%choice%"=="1" goto START_ALL
if /i "%choice%"=="2" goto START_BACKEND
if /i "%choice%"=="3" goto START_FRONTEND
if /i "%choice%"=="4" goto INSTALL_DEPS
if /i "%choice%"=="5" goto HELP
if /i "%choice%"=="0" goto EXIT

echo.
echo Invalid choice!
pause
goto MENU

:START_ALL
cls
echo.
echo ========================================
echo  Starting services...
echo ========================================
echo.
cd /d "%~dp0"
start "Backend API - Port 8421" cmd /k "set PYTHONPATH=%~dp0 && python -m uvicorn api.server:app --host 0.0.0.0 --port 8421 --reload"
timeout /t 3 /nobreak >nul
cd web
start "Frontend Web - Port 4242" cmd /k "npm run dev"
cd ..
echo.
echo   Backend API:  http://localhost:8421
echo   API Docs:     http://localhost:8421/docs
echo   Frontend:     http://localhost:4242
echo.
pause
goto MENU

:START_BACKEND
cls
echo.
echo ========================================
echo  Starting Backend API...
echo ========================================
echo.
cd /d "%~dp0"
set PYTHONPATH=%~dp0
python -m uvicorn api.server:app --host 0.0.0.0 --port 8421 --reload
pause
goto MENU

:START_FRONTEND
cls
echo.
echo ========================================
echo  Starting Frontend Web...
echo ========================================
echo.
cd /d "%~dp0\web"
npm run dev
pause
goto MENU

:INSTALL_DEPS
cls
echo.
echo ========================================
echo  Installing dependencies...
echo ========================================
echo.

cd /d "%~dp0"
echo [1/2] Installing Python dependencies...
pip install -r requirements.txt
echo.

echo [2/2] Installing frontend dependencies...
cd web
if not exist node_modules (
    npm install
) else (
    echo node_modules already exists, skipping
)
cd ..

echo.
echo ========================================
echo  Dependencies installed!
echo ========================================
echo.
pause
goto MENU

:HELP
cls
echo.
echo ========================================
echo  Novel Simulator V5.2 - Help
echo ========================================
echo.
echo Quick Start:
echo    Select [1] to start all services
echo.
echo Service URLs:
echo    - Frontend: http://localhost:4242
echo    - Backend:  http://localhost:8421
echo    - API Docs: http://localhost:8421/docs
echo.
echo First Run:
echo    First select [4] to install dependencies
echo    Then select [1] to start services
echo.
echo Features:
echo    - Genre Abstraction Layer
echo    - Horror Genre Pack
echo    - Story Quality Evaluator
echo    - 4-stage horror progression control
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
echo.
timeout /t 1 /nobreak >nul
exit /b
