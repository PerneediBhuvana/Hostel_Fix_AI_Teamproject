@echo off
REM ============================================================
REM  HOSTELFIX AI - One-Click Start (Windows)
REM  Starts BOTH backend (Flask :5000) and frontend (Vite :5173)
REM  then opens the app in your browser.
REM ============================================================
title HOSTELFIX AI Launcher
cd /d "%~dp0"

echo.
echo ============================================
echo   HOSTELFIX AI - Hostel Complaint System
echo ============================================
echo.

REM --- 1. Backend setup & start ---
echo [1/3] Preparing backend...
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo     Creating Python virtual environment...
    python -m venv .venv
)

echo     Installing backend dependencies...
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt -q

echo     Seeding database...
python seed.py

echo     Starting backend on http://localhost:5000 ...
start "HOSTELFIX Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python run.py"

REM --- 2. Frontend setup & start ---
echo [2/3] Preparing frontend...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo     Installing frontend dependencies (this may take a while)...
    call npm install
)

echo     Starting frontend on http://localhost:5173 ...
start "HOSTELFIX Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM --- 3. Open browser ---
echo [3/3] Opening browser...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo ============================================
echo   HOSTELFIX AI is starting up.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:5000
echo ============================================
echo.
echo   Login credentials:
echo     Student : student@college.edu / Student@12345
echo     Admin   : admin@college.edu   / Admin@12345
echo     Warden  : warden1@college.edu / WardenA@2026
echo     Faculty : faculty1@college.edu / Smith@2026
echo     Staff   : staff1@college.edu  / Staff1@2026
echo ============================================
echo.
pause
