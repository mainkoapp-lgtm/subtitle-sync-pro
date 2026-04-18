@echo off
setlocal

echo [Subtitle Sync Pro] Local Test Environment Starting...
cd /d "%~dp0"

echo [+] Starting Backend Server...
cd /d backend
start "Subtitle Backend" ..\venv\Scripts\python.exe main.py
cd /d ..

timeout /t 3 /nobreak > nul

echo [+] Starting Frontend Server...
cd /d frontend
start "Subtitle Frontend" npm run dev

echo.
echo ======================================================
echo  [Execution Complete]
echo  - Frontend: http://localhost:5173
echo  - Backend: http://localhost:8000
echo ======================================================
echo.

pause
