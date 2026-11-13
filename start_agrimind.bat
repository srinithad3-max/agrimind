@echo off
title AgriMind server
cd /d "%~dp0"
echo Stopping any old AgriMind server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >NUL 2>&1
echo Starting AgriMind - keep this window open. Dashboard: http://localhost:8000
if exist "%USERPROFILE%\anaconda3\python.exe" ("%USERPROFILE%\anaconda3\python.exe" run.py) else (python run.py)
pause
