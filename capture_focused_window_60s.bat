@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0capture_focused_window_60s.ps1"
pause
endlocal
