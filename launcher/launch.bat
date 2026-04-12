@echo off
title Subtitle Sync Pro Launcher
set BASE_DIR=%~dp0..
cd /d "%BASE_DIR%"

echo [1/3] 백엔드 엔진(API) 시작 중...
start "Subtitle_Backend" /min cmd /c "cd /d backend && ..\venv\Scripts\python.exe main.py"

echo [2/3] 프론트엔드 UI(Vite) 시작 중...
start "Subtitle_Frontend" /min cmd /c "cd /d frontend && npm run dev"

echo [3/3] 웹 브라우저를 띄웁니다...
timeout /t 5 > nul
start http://localhost:3000
exit
