# BESS Standalone Arbitrage Platform (lucid-franklin)
## Batarya Enerji Depolama Sistemleri (BESS) Arbitraj & Fizibilite Çözümleri

Bu depo (`lucid-franklin`), EPİAŞ Gün Öncesi Piyasası (PTF) verilerini kullanarak şebeke ölçeğinde batarya arbitrajı gerçekleştiren **iki bağımsız projeyi** ayrı klasörlerde barındırmaktadır:

---

### 📁 1. `bess_05c/` - Standalone BESS Arbitraj Stratejisi (0.5C / 2-Saat Depolama) [Aktif]
- **Yapı:** 0.5C / 2 Saatlik Depolama (örn. 50 MW / 100 MWh)
- **Matematiksel Motor:** SciPy HiGHS Simplex sürekli doğrusal optimizasyon
- **Özellikler:** Değişken güç modülasyonu ($0 \le P \le P_{max}$), 1.0 Döngü vs. 1.5 Döngü senaryo karşılaştırma matrisi, dinamik hücre yıpranması
- **Tasarım:** Apple Cupertino & Google Material 3 koyu slate arayüz, sıfır emoji, vektör SVG batarya ikonları
- **Yerel Port:** `http://localhost:8502`
- **Başlatıcı:** `run_bess_05c.bat` (veya `bess_05c/run_app.bat`)

---

### 📁 2. `bess_1c/` - 1C Tam Blok Arbitraj & Sezgisel Optimizasyon [Eski Proje]
- **Yapı:** 1C / 1 Saatlik Depolama (örn. 1 MW / 1 MWh veya 50 MW / 50 MWh)
- **Model:** Tam blok ikili (on/off) şarj ve deşarj eşleştirme sezgiselleri (1-Döngü ve 2-Döngü)
- **Yerel Port:** `http://localhost:8501`
- **Başlatıcı:** `run_bess_1c.bat` (veya `bess_1c/run_app.bat`)

---

### 📊 Ortak Veri Seti (`data/`)
Her iki proje de ana dizindeki `data/` klasöründeki EPİAŞ PTF verilerini paylaşır:
- `data/PTF2024.csv`: 2024 yılı saatlik PTF ($/MWh) verisi (8.784 satır, artık yıl)
- `data/PTF2025.csv`: 2025 yılı saatlik PTF ($/MWh) verisi (8.760 satır, tam yıl)

---

### 🚀 Hızlı Başlatma (Windows)
1. **0.5C LP Panelini Başlatmak İçin:** Çift tıklayın: **`run_bess_05c.bat`** (Port 8502)
2. **1C Blok Panelini Başlatmak İçin:** Çift tıklayın: **`run_bess_1c.bat`** (Port 8501)
3. **Seçim Menüsü İçin:** Çift tıklayın: **`run_app.bat`**
