@echo off
echo ========================================
echo Building TestAuto.exe...
echo ========================================

REM Build exe
call .venv\Scripts\python.exe -m PyInstaller build_exe.spec --noconfirm
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo ========================================
echo Build complete! Starting app...
echo ========================================

REM Start the app
start "" "dist\TestAuto.exe"
