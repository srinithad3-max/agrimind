@echo off
title Push AgriMind to GitHub
cd /d "%~dp0"
where git >NUL 2>&1 || (echo Git is not installed. Run Git-2.55.0.5-64-bit.exe from your Downloads folder, then try again. & pause & exit /b)
if not exist .git git init -b main
git config user.name >NUL 2>&1 || git config user.name "srinithad3-max"
git config user.email >NUL 2>&1 || git config user.email "srinithad3-max@users.noreply.github.com"
git add -A
git commit -m "AgriMind: multi-agent crop intelligence (PS14)"
git remote remove origin >NUL 2>&1
git remote add origin https://github.com/srinithad3-max/agrimind.git
git branch -M main
git push -u origin main
echo.
echo Done. Open https://github.com/srinithad3-max/agrimind
pause
