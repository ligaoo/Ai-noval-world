@echo off
chcp 65001 >nul
title Novel Simulator V5.2

echo.
echo ===========================================================
echo         Novel Simulator V5.2 - Quick Start
echo ===========================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Backend API (Port 8421)...
start "Backend API - Port 8421" cmd /k "set PYTHONPATH=%~dp0 && python -m uvicorn api.server:app --host 0.0.0.0 --port 8421 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend dev server...
cd web
start "Frontend Web - Port 4242" cmd /k "npm run dev"
cd ..

echo.
echo ===========================================================
echo.
echo   Backend API:  http://localhost:8421
echo   API Docs:     http://localhost:8421/docs
echo   Frontend:     http://localhost:4242
echo.
echo ===========================================================
echo.
echo Services started in separate windows
echo Close windows to stop services
echo.
pause
