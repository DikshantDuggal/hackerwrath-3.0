@echo off
title EdgeRunner Guardian - Mobile App & Emulator
echo ========================================================
echo   EdgeRunner Guardian - Launching Android Emulator GUI
echo ========================================================
echo.
echo Preserving C: drive - routing SDK and AVD to D:\
cd /d "D:\edgerunner guardian frontend"

powershell -NoProfile -ExecutionPolicy Bypass -File "D:\edgerunner guardian frontend\scripts\start_emulator.ps1"

pause
