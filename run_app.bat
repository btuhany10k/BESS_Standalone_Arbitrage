@echo off
chcp 65001 >nul
title BESS Arbitraj Optimizasyonu Dashboard
echo =====================================================================
echo   ⚡ BESS PTF Arbitraj Optimizasyonu ^& Fizibilite Dashboard
echo =====================================================================
echo.

:: Sanal ortam varsa otomatik aktive et
if exist "venv\Scripts\activate.bat" (
    echo [BILGI] 'venv' sanal ortami tespit edildi ve aktive ediliyor...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [BILGI] '.venv' sanal ortami tespit edildi ve aktive ediliyor...
    call .venv\Scripts\activate.bat
)

echo [BILGI] Streamlit Dashboard baslatiliyor...
echo [IPUCU] Tarayicinizda http://localhost:8501 adresi otomatik acilacaktir.
echo.
python -m streamlit run app.py
pause
