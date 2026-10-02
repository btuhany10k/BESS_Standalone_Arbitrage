#!/usr/bin/env bash
# BESS Arbitraj Optimizasyonu Dashboard Baslatici (Linux / macOS)

set -e

echo "====================================================================="
echo "  ⚡ BESS PTF Arbitraj Optimizasyonu & Fizibilite Dashboard"
echo "====================================================================="
echo ""

# Sanal ortam varsa otomatik aktive et
if [ -d "venv" ]; then
    echo "[BILGI] 'venv' sanal ortami aktive ediliyor..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "[BILGI] '.venv' sanal ortami aktive ediliyor..."
    source .venv/bin/activate
fi

echo "[BILGI] Streamlit Dashboard baslatiliyor..."
python -m streamlit run app.py
