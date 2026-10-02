# ⚡ BESS PTF Arbitraj Optimizasyonu ve Fizibilite Dashboard'u

> **EPİAŞ Gün Öncesi Piyasası (GÖP) Gerçek Saatlik Piyasa Takas Fiyatı (PTF) Verileriyle Batarya Enerji Depolama Sistemleri (BESS) 1C Arbitraj Simülasyonu, Yıpranma Analizi ve Karar Destek Platformu.**

---

## 📌 Proje Genel Bakışı

Bu proje; Türkiye elektrik piyasasında (EPİAŞ GÖP) 2024 ve 2025 yıllarına ait **8.784** ve **8.760** saatlik gerçek PTF verilerini kullanarak, şebeke ölçeğinde Batarya Enerji Depolama Sistemlerinin (BESS) arbitraj potansiyelini simüle eden ve fizibilite analizini gerçekleştiren interaktif bir analitik platformdur.

Batarya yatırımı yapacak enerji yatırımcıları, portföy yöneticileri ve analistler için tasarlanmış olup; **parçalı ve gerçek dışı alım-satımları engelleyen**, günde en kârlı tekil dip saatte şarj ve akşam pikinde deşarj yapan **1C Blok Arbitraj Stratejisi** ile çalışır.

---

## ✨ Temel Özellikler

1. **🔋 Esnek Batarya Parametreleri (Sol Panel):**
   - **Nominal Güç:** 0.5 MW ile 150.0 MW arasında serbest seçim.
   - **Depolama Kapasitesi:** 1C konfigürasyonunda otomatik hesaplama (Örn: 10 MW ➔ 10 MWh).
   - **Çevrim Verimliliği (Round-Trip Efficiency - RTE):** %70 ile %98 arasında ayarlanabilir.
   - **İşletmeci SoC Yönetimi:** Güne Başlangıç SoC (%) ve Gün Sonu Hedef SoC (%) sınırlandırması.

2. **🛠️ Yıpranma Maliyeti & Sermaye Koruma (Pas Geçme / Idle Mekanizması):**
   - Kullanıcı tarafından serbestçe girilebilen döngü başı **Yıpranma Maliyeti ($/MWh)** parametresi.
   - Eğer gün içi PTF fiyat makası (spread), verimlilik kaybını ve yıpranma maliyetini karşılamıyorsa (**Net Kâr $\le$ $0.00$**), batarya o gün kesinlikle çalıştırılmaz (**Pas Geçilir: 0 MW, 0 Cycle, $0 Maliyet, $0 Kâr**).
   - Yıllık ve aylık toplamlar negatif kârlı günlerden tamamen arındırılır.

3. **📈 4 Dinamik Analiz Sekmesi:**
   - **1. Günlük Arbitraj Detayı:**
     - 4'lü interaktif tarih seçim kartları (📌 Gün, 📆 Ay, 🗓️ Yıl) ve senkronize 📅 Takvim Kartı.
     - 24 saatlik PTF eğrisi, tekil şarj ve deşarj noktaları ve saatlik batarya doluluk (SoC %) grafiği.
     - Accordion içinde 24 saatin tamamını gösteren renklendirilmiş detay tablosu (🔵 Mavi: Şarj saati, 🟢 Yeşil: Deşarj saati).
   - **2. Aylık ve Yıllık Kırılım & 365 Günlük Excel İndirme:**
     - Tek satırda 3 kompakt piyasa ve finans grafiği:
       1. *Aylık Net Kâr ($) ve Yapılan Cycle Sayısı*
       2. *Aylık Cycle Başına Net Kâr ($/Cycle)*
       3. *Aylık Ortalama PTF ($/MWh) ve Günlük Fiyat Makası (Spread) Dinamikleri (Çift Eksenli)*
     - **365 Günlük Detaylı Excel (.xlsx) Raporu:** Sol paneldeki tüm kısıtlara göre anlık üretilen, 5 sayfalı kurumsal Excel dosyası (Özet, Aylık Kırılım, 365 Günlük Özet, 8760 Saatlik Detay, 2024 vs 2025 Kıyaslama).
   - **3. 2024 vs 2025 Kıyaslama:**
     - Aynı batarya konfigürasyonu ile 2024 ve 2025 PTF spread dinamiklerinin arbitraj kârlılığına etkisini yan yana kıyaslayan metrikler, karşılaştırma tablosu ve aylık kâr grafiği.
   - **4. LinkedIn Fizibilite Kartı:**
     - Tek tıkla kopyalanabilir, profesyonel formatta hazırlanmış sosyal medya / yatırımcı özeti metni.

---

## 📂 Proje Dizin Yapısı

```plaintext
├── data/                      # EPİAŞ Saatlik PTF Veri Dosyaları
│   ├── PTF2024.csv            # 2024 PTF verisi (8,784 satır - Artık Yıl)
│   └── PTF2025.csv            # 2025 PTF verisi (8,760 satır)
├── src/                       # Çekirdek Python Modülleri
│   ├── __init__.py
│   ├── data_loader.py         # PTF veri okuma, temizleme ve önbellekleme
│   ├── optimizer.py           # 1C Arbitraj, SoC ve Pas Geçme optimizasyon motoru
│   ├── metrics.py             # Finansal KPI, döngü istatistikleri ve aylık toplayıcı
│   └── exporter.py            # Çok sayfalı profesyonel Excel raporu üreticisi
├── tests/                     # Test Paketleri
│   ├── test_optimizer.py      # Optimizasyon motoru ve yıpranma birim testleri
│   └── test_e2e.py            # Uçtan uca veri, sınır durumları ve Excel doğrulama testleri
├── app.py                     # Streamlit kullanıcı arayüzü ve görselleştirme katmanı
├── requirements.txt           # Python bağımlılık listesi
├── run_app.bat                # Windows için tek tıkla başlatma betiği
├── run_app.sh                 # Linux / macOS için başlatma betiği
├── .gitignore                 # Git versiyon kontrolü dışlama kuralları
└── README.md                  # Proje dokümantasyonu
```

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- **Python 3.10** veya daha güncel bir sürüm (Python 3.11, 3.12, 3.13 veya 3.14 önerilir)
- Git

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/btuhany10k/BESS_Standalone_Arbitrage.git
cd BESS_Standalone_Arbitrage
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktive Edin (Önerilir)
- **Windows:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Uygulamayı Başlatın
- **Windows (Hızlı Başlat):**  
  `run_app.bat` dosyasına çift tıklayın veya terminalde:
  ```powershell
  .\run_app.bat
  ```
- **Terminalden Doğrudan Çalıştırma:**
  ```bash
  streamlit run app.py
  ```

Tarayıcınızda otomatik olarak **http://localhost:8501** adresi açılacaktır.

---

## 🧪 Testleri Çalıştırma

Uygulamanın veri doğruluğunu ve matematiksel modellerini doğrulamak için hazırlanan test suitlerini çalıştırabilirsiniz:

```bash
# 1. Optimizasyon Motoru ve Yıpranma Birim Testleri
python tests/test_optimizer.py

# 2. Uçtan Uca (E2E) Kapsamlı Doğrulama Testi
python tests/test_e2e.py
```

Testler; veri sürekliliğini, artık yıl (2024 Şubat 29) takvim yönetimini, aşırı yıpranma maliyetlerinde sermaye koruma kararını ve Excel raporlarının satır bazlı doğruluğunu test eder.

---

## 📐 Matematiksel Formülasyon ve Mantık

### 1. Enerji Değişimleri
- **Kapasite:** $E_{\max} = \frac{P_{\text{nominal}}}{\text{C-Rate}}$ (1C için $E_{\max} = P_{\text{nominal}}$ MWh)
- **Başlangıç Seviyesi:** $E_{\text{start}} = \frac{\text{SoC}_{\text{start}}}{100} \times E_{\max}$
- **Şarj Enerjisi (Dip Saat):** $\Delta E_{\text{ch}} = E_{\max} - E_{\text{start}}$
- **Deşarj Enerjisi (Pik Saat):** $\Delta E_{\text{dis, grid}} = (E_{\max} - E_{\text{end}}) \times \text{RTE}$

### 2. Kârlılık ve Karar Mekanizması
$$\text{Brüt Kâr} = (\Delta E_{\text{dis, grid}} \times \text{PTF}_{\text{dis}}) - (\Delta E_{\text{ch}} \times \text{PTF}_{\text{ch}})$$
$$\text{Yıpranma Maliyeti} = \text{Birim Yıpranma (\$/MWh)} \times (E_{\max} - E_{\text{end}})$$
$$\text{Net Kâr} = \text{Brüt Kâr} - \text{Yıpranma Maliyeti}$$

- **Eğer $\text{Net Kâr} \le 0$ ise:**  
  Batarya beklemeye (standby) alınır, döngü yapılmaz. $\text{Net Kâr} = \$0.00$, $\text{Cycle} = 0$, $\text{Maliyet} = \$0.00$.

---

## 📄 Lisans & Katkı
Bu proje MIT Lisansı ile lisanslanmıştır. Katkıda bulunmak için lütfen bir Pull Request gönderin veya Issue açın.
