# BESS 1C Arbitraj Optimizasyonu & Fizibilite Dashboard
## 1 Saatlik Depolama & Tam Blok Sezgisel Arbitraj

Bu klasör, 1C (1 Saatlik Depolama, örn. 1 MW / 1 MWh veya 50 MW / 50 MWh) şebeke ölçeğindeki BESS projeleri için tam blok ikili şarj/deşarj arbitraj modelini içerir.

### Temel Özellikler
- **Tam Blok Arbitraj:** Günde 1 veya 2 tam döngü halinde günün en ucuz ve en pahalı saatlerini eşleştiren sezgisel kural tabanlı model.
- **İşletmeci SoC Yönetimi:** Başlangıç ve gün sonu rezerv SoC sınırları.
- **Yıpranma Maliyeti & Pas Geçme:** Arbitraj kârı yıpranma maliyetini kurtarmadığında bataryayı bekleten (idle) dinamik koruma.
- **Excel Raporu:** 5 sekmeli yıllık ve saatlik nakit akışı tablosu.

### Çalıştırma
```bash
run_app.bat
# veya terminalden:
streamlit run app.py --server.port 8501
```
Tarayıcı: `http://localhost:8501`
