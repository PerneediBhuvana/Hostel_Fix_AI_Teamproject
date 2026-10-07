@echo off
REM ============================================
REM  HOSTELFIX AI - Backend Starter (Windows)
REM  Starts Flask API on http://localhost:5000
REM ============================================
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo Installing backend dependencies...
pip install -r requirements.txt -q

echo Starting HOSTELFIX AI Backend...
echo Seeding database (idempotent)...
python seed.py

echo Starting Flask server on port 5000...
python run.py
