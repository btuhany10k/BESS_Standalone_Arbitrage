@echo off
chcp 65001 >nul
title BESS 0.5C Surekli LP Arbitraj Paneli (Port 8502)
cd /d "%~dp0"

echo =====================================================================
echo   ⚡ BESS 0.5C Sürekli Doğrusal Programlama (LP) Arbitraj Paneli
echo   🎨 Tasarım: Apple Cupertino / Google M3 Hassas Arayüz
echo   🌐 Host: http://localhost:8502
echo =====================================================================
echo.

if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

start http://localhost:8502
python -m streamlit run app.py --server.port 8502 --server.headless false
pause
