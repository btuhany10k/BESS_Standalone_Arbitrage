# Standalone BESS Arbitraj Stratejisi
## 0.5C / 2 Saatlik Depolama & Güç Modülasyonu

Bu klasör, 0.5C (2 Saatlik Depolama, örn. 50 MW / 100 MWh) şebeke ölçeğindeki Batarya Enerji Depolama Sistemleri için geliştirilmiş sürekli doğrusal programlama (SciPy HiGHS) arbitraj ve optimizasyon modelini içerir.

### Temel Özellikler
- **Matematiksel Optimizasyon:** SciPy HiGHS Simplex çözücüsü ile 24 saatlik sürekli güç modülasyonu.
- **Değişken Güç Modülasyonu:** 0 ile P_max arasında herhangi bir kesirli güçte (örn. 25 MW, 37.5 MW) şarj/deşarj olanağı.
- **Stratejiler:** 1.0 Döngü Senaryosu (Koruyucu / Pil Ömrü) vs. 1.5 Döngü Kısmi Modülasyon Senaryosu (Olası Pikleri Yakalama).
- **Arayüz Tasarımı:** Apple Cupertino & Google Material 3 standartlarında koyu slate tasarım, sıfır emoji, saf SVG batarya ikonları.
- **Excel Raporu:** 5 sekmeli tam finansal fizibilite ve saatlik fiziksel simülasyon çıktısı.

### Çalıştırma
```bash
run_app.bat
# veya terminalden:
streamlit run app.py --server.port 8502
```
Tarayıcı: `http://localhost:8502`
