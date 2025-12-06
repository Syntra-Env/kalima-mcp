@echo off
REM Launch the Kalima CLI against the local API server.
REM Adjust the --api URL if your server runs elsewhere.
cd /d "%~dp0"
kalima.exe --api http://127.0.0.1:8080
pause