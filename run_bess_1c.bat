@echo off
chcp 65001 >nul
title BESS 1C Arbitraj Optimizasyonu Dashboard (Port 8501)
cd /d "%~dp0bess_1c"

echo =====================================================================
echo   ⚡ BESS 1C Arbitraj Optimizasyonu & Fizibilite Dashboard
echo   🌐 Host: http://localhost:8501
echo =====================================================================
echo.

if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

start http://localhost:8501
python -m streamlit run app.py --server.port 8501 --server.headless false
pause
