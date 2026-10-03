@echo off
chcp 65001 >nul
title BESS Arbitraj Optimizasyonu Dashboard
echo =====================================================================
echo   ⚡ BESS PTF Arbitraj Optimizasyonu ^& Fizibilite Dashboard
echo =====================================================================
echo.

:: 1. Python kurulu mu kontrol et
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Bilgisayarınızda Python bulunamadı!
    echo Lütfen https://www.python.org/downloads/ adresinden Python 3.10+ kurun.
    echo Kurulum sırasında "Add Python to PATH" seçeneğini işaretlemeyi unutmayın.
    echo.
    pause
    exit /b 1
)

:: 2. Sanal ortam (venv) var mı kontrol et, yoksa otomatik oluştur
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Sanal ortam (venv) bulunamadı, otomatik oluşturuluyor...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [HATA] Sanal ortam oluşturulamadı!
        pause
        exit /b 1
    )
    echo [BILGI] Sanal ortam başarıyla oluşturuldu.
)

:: 3. Sanal ortamı aktive et
call venv\Scripts\activate.bat

:: 4. Gerekli kütüphaneler kurulu mu kontrol et, eksikse otomatik kur
python -c "import streamlit, plotly, openpyxl, pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/3] Gerekli kütüphaneler yükleniyor (requirements.txt)...
    echo       (Bu işlem sadece ilk çalıştırmada 1-2 dakika sürer.)
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [HATA] Kütüphaneler kurulurken bir sorun oluştu!
        pause
        exit /b 1
    )
    echo [BILGI] Tüm kütüphaneler başarıyla kuruldu.
)

:: 5. Dashboard'u başlat
echo.
echo [3/3] Streamlit Dashboard başlatılıyor...
echo [IPUCU] Tarayıcınızda http://localhost:8501 adresi otomatik açılacaktır.
echo.
python -m streamlit run app.py
pause

