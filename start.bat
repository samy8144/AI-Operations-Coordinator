@echo off
setlocal
echo ========================================
echo   Skylark Drones AI Operations System
echo ========================================
echo.

:: 1. CLEANUP - Kill any existing servers to avoid "Port already in use" errors
echo Cleaning up existing processes...
taskkill /F /IM node.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM uvicorn.exe /T 2>nul
timeout /t 2 /nobreak >nul

:: 2. PATH SETUP
set "BASE=%~dp0"

echo [1/2] Starting Backend (FastAPI)...
start "Backend Server" /D "%BASE%backend" cmd /k "python -m uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend (Next.js)...
start "Frontend Server" /D "%BASE%frontend" cmd /k "npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Servers are starting!
echo ----------------------------------------
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo ========================================
echo.
echo Opening browser...
start http://localhost:3000

echo.
echo Press any key to close this window.
pause >nul
