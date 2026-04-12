@echo off
echo ========================================
echo   SubFast Manager - Firebase Deploy
echo ========================================
echo.

if exist "node_modules\.bin\firebase.cmd" (
    echo Deploying to Firebase Hosting...
    call "node_modules\.bin\firebase.cmd" deploy --only hosting
) else (
    echo Firebase tools not found locally.
    echo Installing firebase-tools...
    npm install firebase-tools
    echo.
    echo Now deploying...
    call "node_modules\.bin\firebase.cmd" deploy --only hosting
)

echo.
echo Deploy completed! Check: https://subfast-manager.web.app/latest_version.json
pause
