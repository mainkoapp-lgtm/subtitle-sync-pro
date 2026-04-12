@echo off
title Subtitle Sync Pro - Integrated Launcher
set BASE_DIR=%~dp0
cd /d "%BASE_DIR%"

echo [1/3] 백엔드 엔진(API) 시작 중...
start "Subtitle_Backend" /min cmd /c "cd /d backend && ..\venv\Scripts\python.exe main.py"

echo [2/3] 프론트엔드 UI(Vite) 시작 중...
start "Subtitle_Frontend" /min cmd /c "cd /d frontend && npm run dev"

echo [3/3] 잠시 후 서버가 가동되면 웹 브라우저가 열립니다.
timeout /t 5 > nul
start http://localhost:3000

echo.
echo ==========================================
echo  Subtitle Sync Pro가 실행되었습니다.
echo  작업을 마치려면 이 창을 닫아주세요.
echo ==========================================
pause
