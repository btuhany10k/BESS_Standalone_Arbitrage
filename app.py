"""
BESS Standalone Arbitraj Platformu
Streamlit Cloud Başlatıcı (Root Entrypoint)
"""
import sys
from pathlib import Path

# Proje dizinini ve bess_05c alt modülünü sys.path'e ekle
root_dir = Path(__file__).resolve().parent
bess_05c_dir = root_dir / "bess_05c"

if str(bess_05c_dir) not in sys.path:
    sys.path.insert(0, str(bess_05c_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# bess_05c altındaki app.py dosyasını çalıştır
import bess_05c.app
