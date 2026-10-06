@echo off
chcp 65001 >nul
title BESS Arbitraj Optimizasyonu Projeleri
cd /d "%~dp0"

echo =====================================================================
echo   ⚡ BESS Arbitraj Optimizasyon Platformu (lucid-franklin)
echo =====================================================================
echo.
echo   Lutfen baslatmak istediginiz projeyi secin:
echo.
echo   [1] BESS 0.5C Surekli LP & Kismi Guc Modulasyonu (Port 8502) [Aktif]
echo   [2] BESS 1C Blok Arbitraj & Sezgisel Optimizasyon (Port 8501)
echo.
set /p choice="Seciminiz (1 veya 2, varsayilan: 1): "

if "%choice%"=="2" (
    call run_bess_1c.bat
) else (
    call run_bess_05c.bat
)
