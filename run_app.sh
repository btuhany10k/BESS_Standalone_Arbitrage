#!/usr/bin/env bash
# BESS Arbitraj Optimizasyonu Dashboard Baslatici (Linux / macOS)

set -e

echo "====================================================================="
echo "  ⚡ BESS PTF Arbitraj Optimizasyonu & Fizibilite Dashboard"
echo "====================================================================="
echo ""

# 1. Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "[HATA] Sisteminizde python3 bulunamadi! Lütfen Python 3.10+ kurun."
    exit 1
fi

# 2. Sanal ortam (venv) kontrolü ve oluşturma
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "[1/3] 'venv' sanal ortami bulunamadi, otomatik olusturuluyor..."
    python3 -m venv venv
    source venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 3. Kütüphaneleri kontrol et ve eksikse kur
if ! python3 -c "import streamlit, plotly, openpyxl, pandas" &> /dev/null; then
    echo "[2/3] Gerekli Python paketleri yukleniyor (requirements.txt)..."
    pip install -r requirements.txt
    echo "[BILGI] Paketler basariyla kuruldu."
fi

# 4. Streamlit Dashboard'u başlat
echo ""
echo "[3/3] Streamlit Dashboard baslatiliyor..."
echo "[IPUCU] Tarayicinizda http://localhost:8501 adresi otomatik acilacaktir."
echo ""
python3 -m streamlit run app.py

