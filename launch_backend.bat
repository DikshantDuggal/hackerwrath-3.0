@echo off
title EdgeRunner Guardian - Backend Server
echo ========================================================
echo   EdgeRunner Guardian - Launching FastAPI Backend Server
echo ========================================================
echo.
cd /d "D:\edgerunner guardian frontend"

powershell -NoProfile -ExecutionPolicy Bypass -File "D:\edgerunner guardian frontend\scripts\start_backend.ps1"

pause
