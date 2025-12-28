@echo off
REM Close any running instance first, then rebuild
echo Make sure the Kalima app is closed first!
echo.
pause
echo Rebuilding...
cd desktop\src-tauri
cargo tauri build
echo.
echo Done! Run 'run-desktop.bat' to start the app.
pause
