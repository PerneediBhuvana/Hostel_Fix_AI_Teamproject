@echo OFF
REM ============================================
REM  HOSTELFIX AI - Frontend Starter (Windows)
REM  Starts Vite dev server on http://localhost:5173
REM ============================================
cd /d "%~dp0frontend"

echo Starting HOSTELFIX AI Frontend...
echo If node_modules is missing, run: npm install
npm run dev
