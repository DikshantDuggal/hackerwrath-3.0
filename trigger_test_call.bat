@echo off
echo ========================================================
echo   EdgeRunner Guardian - Triggering Live Demo Scam Call
echo ========================================================
echo.
curl.exe -s -X POST -H "Content-Type: application/json" -d "{\"scenario\": \"bank_fraud\"}" http://127.0.0.1:8000/api/demo/calls
echo.
echo Call triggered successfully! Check your emulator screen.
echo.
pause
