# BESS Standalone Arbitrage Optimization

EPİAŞ Gün Öncesi Piyasası (GÖP) saatlik Piyasa Takas Fiyatı (PTF) verilerini kullanarak şebeke ölçeğindeki Batarya Enerji Depolama Sistemleri (BESS) için 1C arbitraj simülasyonu, yıpranma maliyeti hesabı ve ekonomik fizibilite analizi sunan analitik bir modeldir.

Model, 2024 (artık yıl, 8.784 saat) ve 2025 (8.760 saat) gerçekleşen piyasa takas fiyatları üzerinde çalışır.

---

## Model Yaklaşımı

Model, gün içi fiyat hareketlerine göre batarya işletimini simüle eder:
- **Operasyon Stratejileri (1 veya 2 Döngü / Gün):**
  - **Günde 1 Döngü (Tek Blok):** Günlük 24 saatlik fiyat eğrisinde şarjın deşarjdan önce gerçekleşmesi koşuluyla en yüksek net kârı sağlayan tekil $(ch_1, dis_1)$ saat çiftini belirler.
  - **Günde 2 Döngü (Çift Blok):** En kârlı 1. döngünün saat aralığı dışındaki serbest pencerelerde ($ch_2 < dis_2 < ch_1$ veya $dis_1 < ch_2 < dis_2$) ikinci bir kârlı döngü arar. İkinci döngü sadece net kârı $> 0$ ise devreye alınır; kârsızsa 1 döngüde kalınır. İşlemler gün içi kronolojik sırasına göre `Şarj 1`, `Deşarj 1`, `Şarj 2`, `Deşarj 2` olarak indekslenir.
- **İşletmeci SoC Yönetimi:** Başlangıç ve hedef bitiş doluluk sınırları kullanıcı tarafından belirlenir; şarj dip saatte bataryayı tam kapasiteye ulaştırırken, deşarj bataryayı hedef bitiş seviyesine indirir.
- **Yıpranma Maliyeti ve Pas Geçme Kuralı:** Döngü başına hücre amortisman maliyeti ($/MWh) hesaba katılır. Fiyat farkı verimlilik kaybı ve yıpranma maliyetini karşılamıyorsa batarya o gün çalıştırılmaz (bekleme / standby modu; 0 döngü, $0 maliyet, $0 kâr).

---

## Temel Fonksiyonlar

- **Parametre Yönetimi:** 0.5 - 150 MW nominal güç aralığı, %70 - %98 çevrim verimliliği (RTE), serbest başlangıç/bitiş SoC ve birim yıpranma maliyeti girişi.
- **Günlük Detay Analizi:** 24 saatlik PTF eğrisi, tekil şarj/deşarj noktaları, saatlik SoC profili ve renklendirilmiş saatlik işlem dökümü.
- **Aylık Kırılım ve Piyasa Dinamikleri:** Aylık net kâr, döngü sayısı, döngü başı birim kâr ile aylık ortalama PTF ve günlük PTF spread grafiklerinin çift eksenli analizi.
- **Çok Sayfalı Excel Raporlama:** Seçilen parametrelerle anlık üretilen 5 sayfalı Excel raporu (Parametreler, Aylık Kırılım, 365 Günlük Özet, 8.760 Saatlik Detay, 2024 vs 2025 Kıyaslama).
- **Yıllık Karşılaştırma:** Aynı sistem konfigürasyonunun 2024 ve 2025 piyasa koşullarındaki karşılaştırmalı performans analizi.

---

## Proje Yapısı

```plaintext
├── data/
│   ├── PTF2024.csv            # 2024 EPİAŞ saatlik PTF verisi (8.784 satır)
│   └── PTF2025.csv            # 2025 EPİAŞ saatlik PTF verisi (8.760 satır)
├── src/
│   ├── data_loader.py         # CSV veri işleme ve zaman serisi düzenleme
│   ├── optimizer.py           # Blok arbitraj ve ekonomik optimizasyon motoru
│   ├── metrics.py             # Finansal KPI, döngü ve aylık metrik hesaplamaları
│   └── exporter.py            # Excel (.xlsx) rapor üreticisi
├── tests/
│   ├── test_optimizer.py      # Optimizasyon motoru birim testleri
│   └── test_e2e.py            # Uçtan uca sınır durum ve veri doğrulama testleri
├── app.py                     # Streamlit kullanıcı arayüzü
├── requirements.txt           # Bağımlılık listesi
├── run_app.bat                # Windows ortamı başlatma betiği
├── run_app.sh                 # Linux / macOS başlatma betiği
└── .gitignore                 # Versiyon kontrol dışlama kuralları
```

---

## Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.10 veya üzeri
- Git

### Adımlar

1. Depoyu yerel ortamınıza klonlayın:
   ```bash
   git clone https://github.com/btuhany10k/BESS_Standalone_Arbitrage.git
   cd BESS_Standalone_Arbitrage
   ```

2. Sanal ortam oluşturup aktive edin (önerilir):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. Uygulamayı başlatın:
   ```bash
   # Windows üzerinde doğrudan
   .\run_app.bat

   # veya komut satırından
   streamlit run app.py
   ```
   Uygulama varsayılan olarak `http://localhost:8501` adresinde çalışır.

---

## Testler

Depo içindeki test paketlerini çalıştırmak için:

```bash
# Birim testler (yıpranma ve pas geçme mantığı)
python tests/test_optimizer.py

# Uçtan uca doğrulama testleri (sınır durumlar, veri bütünlüğü ve excel çıktısı)
python tests/test_e2e.py
```

---

## Lisans
Bu çalışma MIT Lisansı altında sunulmaktadır.
