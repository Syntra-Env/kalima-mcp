@echo off
REM Build the Kalima CLI and copy to root directory
echo Building Kalima CLI...
cd engine
cargo build --bin kalima-cli --release
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    cd ..
    exit /b %ERRORLEVEL%
)
cd ..
echo Copying to root as kalima.exe...
copy /Y engine\target\release\kalima-cli.exe kalima.exe
echo Done! You can now run: kalima.exe
