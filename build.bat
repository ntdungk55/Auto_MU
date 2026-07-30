@echo off
echo ========================================
echo Building TestAuto.exe...
echo ========================================

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Build exe
pyinstaller build_exe.spec --noconfirm

echo.
echo ========================================
echo Build complete! Starting app...
echo ========================================

REM Start the app
start "" "dist\TestAuto.exe"
