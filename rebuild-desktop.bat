@echo off
REM Close any running instance first, then rebuild
echo Make sure the Kalima app is closed first!
echo.
pause
echo Rebuilding...
cd desktop\src-tauri
cargo build --release
echo.
echo Done! Run 'run-desktop.bat' to start the app.
pause
