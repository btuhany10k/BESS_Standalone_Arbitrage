"""
BESS PTF Spread Arbitraj Optimizasyonu (Tam Blok 1C & İşletmeci SoC Yönetimi)
"""

import sys
import datetime
import calendar
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Proje dizinini ekle
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import importlib
import src.data_loader
import src.optimizer
import src.metrics
import src.exporter
importlib.reload(src.data_loader)
importlib.reload(src.optimizer)
importlib.reload(src.metrics)
importlib.reload(src.exporter)
from src.data_loader import load_all_ptf_data
from src.optimizer import BESSConfig, optimize_year
from src.metrics import compute_kpis, compute_monthly_breakdown
from src.exporter import generate_bess_excel_report

# Sayfa Konfigürasyonu
st.set_page_config(
    page_title="BESS Arbitraj Optimizasyonu | Fizibilite Paneli",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark / Light Uyumlu Modern & Minimalist CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Başlık */
    .main-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-title {
        font-size: 0.92rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    
    /* KPI Kartları - Glassmorphic Dark UI */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px -2px rgba(0, 0, 0, 0.25);
    }
    .kpi-label {
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 0.35rem;
    }
    .kpi-profit {
        color: #10b981 !important;
    }
    .kpi-cost {
        color: #f87171 !important;
    }
    .kpi-cycle {
        color: #38bdf8 !important;
    }
    
    /* Tarih Mini Kartları */
    .date-mini-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_cached_raw_data():
    """Ham PTF verilerini yükler."""
    return load_all_ptf_data(root_dir)


def calculate_optimization(
    year: int,
    power_mw: float,
    c_rate: float,
    rte: float,
    soc_start_pct: float,
    soc_end_pct: float,
    degradation_cost: float = 0.0,
    strategy: str = "1_cycle",
):
    """
    Tam Blok 1C, İşletmeci SoC, Yıpranma Maliyeti ve 1/2 Döngü Stratejisiyle yıllık simülasyonu çalıştırır.
    """
    data_dict = get_cached_raw_data()
    if year not in data_dict:
        return None, None, None, None

    df = data_dict[year]
    config = BESSConfig(
        power_mw=power_mw,
        c_rate=c_rate,
        rte=rte,
        soc_start_pct=soc_start_pct,
        soc_end_pct=soc_end_pct,
        degradation_cost=degradation_cost,
        strategy=strategy,
    )
    hourly_df, daily_df = optimize_year(df, config)
    kpis = compute_kpis(daily_df, {
        "power_mw": power_mw,
        "capacity_mwh": config.capacity_mwh,
        "c_rate": c_rate,
        "rte": rte,
        "degradation_cost": degradation_cost,
        "strategy": strategy,
    })
    monthly_df = compute_monthly_breakdown(daily_df, config.capacity_mwh)
    return hourly_df, daily_df, kpis, monthly_df


# --- SIDEBAR KONTROLLERİ ---
st.sidebar.markdown("### ⚙️ Sistem & Piyasa Parametreleri")

raw_data = get_cached_raw_data()
available_years = sorted(list(raw_data.keys()))

if not available_years:
    st.error("PTF veri dosyaları (PTF2024.csv, PTF2025.csv) bulunamadı. Lütfen proje dizinini kontrol ediniz.")
    st.stop()

if "selected_year_sidebar" not in st.session_state:
    st.session_state["selected_year_sidebar"] = available_years[-1]

selected_year = st.sidebar.selectbox(
    "📅 Analiz Yılı",
    available_years,
    key="selected_year_sidebar",
    help="Seçilen yılın saatlik EPİAŞ PTF ($/MWh) verisi üzerinde simülasyon yapılır."
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🔋 Batarya Özellikleri")

power_mw = st.sidebar.slider(
    "Nominal Güç (MW)",
    min_value=0.5,
    max_value=150.0,
    value=50.0,
    step=0.5,
    help="Bataryanın maksimum şarj ve deşarj gücü."
)

c_rate = 1.0  # Sabit 1C
capacity_mwh = power_mw / c_rate

st.sidebar.info(
    f"⚡ **Konfigürasyon: 1C (1 Saat)**\n\n"
    f"• Güç: **{power_mw:.1f} MW**\n"
    f"• Kapasite: **{capacity_mwh:.1f} MWh**"
)

rte_percent = st.sidebar.slider(
    "Çevrim Verimliliği (RTE %)",
    min_value=70,
    max_value=98,
    value=85,
    step=1,
    help="Şarj-Deşarj Round-Trip Efficiency. Örn: %85 verimlilikte 1 MWh şarj karşılığı 0.85 MWh net elektrik elde edilir."
)
rte = rte_percent / 100.0

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 İşletmeci SoC Yönetimi (Gün Başı / Sonu)")

soc_start_pct = st.sidebar.slider(
    "Güne Başlangıç SoC (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="İşletmecinin gün başında (00:00) bataryada devraldığı minimum rezerv / doluluk yüzdesi."
)

soc_end_pct = st.sidebar.slider(
    "Gün Sonu Hedef SoC (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="İşletmecinin gün sonunda (23:00) bataryayı bırakmak istediği hedef doluluk yüzdesi."
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 💸 Maliyet Kalemleri")

degradation_cost = st.sidebar.number_input(
    "Yıpranma Maliyeti ($/MWh)",
    min_value=0.0,
    max_value=200.0,
    value=0.0,
    step=1.0,
    help="Döngü başına MWh bazında hücre amortisman ve yıpranma maliyeti ($/MWh). Arbitraj kârı bu maliyeti ve verimlilik kaybını kurtarmıyorsa (net kâr <= 0) o gün batarya çalıştırılmaz (pas geçilir)."
)

if degradation_cost > 0:
    st.sidebar.caption(
        f"ℹ️ {power_mw:.1f} MW batarya için 1 tam döngüde **${degradation_cost * capacity_mwh:,.1f}** yıpranma maliyeti hesaplanır. Net kâr negatif kalacaksa o gün pas geçilir."
    )

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🛡️ Operasyon Stratejisi")

strategy_option = st.sidebar.radio(
    "Arbitraj Stratejisi",
    options=["Günde 1 Döngü (Tek Blok)", "Günde 2 Döngü (Çift Blok)"],
    index=0,
    help="Günde 1 döngü veya en kârlı 1. döngünün dışındaki pencerelerde ek 2. döngü yapma stratejisi."
)
strategy = "2_cycle" if "2" in strategy_option else "1_cycle"

if strategy == "2_cycle":
    st.sidebar.info(
        "⚡ **Günde 2 Döngü (Çift Blok) Stratejisi:**\n\n"
        "• **1. Döngü:** Günün en yüksek spreadine sahip birincil şarj ve deşarjı.\n"
        "• **2. Döngü:** 1. döngü saatlerinin dışındaki (önce veya sonra) en kârlı 2. saat çifti.\n"
        "• **Ekonomik Filtre:** 2. döngü sadece net kârı > 0 ise yapılır, kârsızsa 1 döngüde kalınır.\n"
        "• **Kronolojik İndeks:** Gün içi saat sırasına göre Şarj 1 / Deşarj 1 ve Şarj 2 / Deşarj 2 olarak etiketlenir."
    )
else:
    st.sidebar.success(
        "⚡ **1C Tek Blok Arbitrajı:**\n\n"
        "• Günün en derin dip saatinde şarj.\n"
        "• Akşam en yüksek pik saatinde deşarj.\n"
        "• Net kâr negatif kalırsa gün pas geçilir ($0 kâr, 0 döngü)."
    )

# Hesaplamayı Çalıştır (Seçilen Yıl)
hourly_df, daily_df, kpis, monthly_df = calculate_optimization(
    selected_year, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy
)

# 2024 ve 2025 Yıllık Kıyaslama Verileri (Excel raporu ve Kıyaslama Sekmesi için)
_, _, kpis_2024, monthly_2024 = calculate_optimization(2024, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy)
_, _, kpis_2025, monthly_2025 = calculate_optimization(2025, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy)

comp_df = pd.DataFrame([
    {
        "Yıl": "2024",
        "Deşarj Geliri ($)": kpis_2024["total_revenue"],
        "Şarj Maliyeti ($)": kpis_2024["total_cost"],
        "Brüt Kâr ($)": kpis_2024["gross_profit"],
        "Yıpranma Maliyeti ($)": kpis_2024["total_degradation_cost"],
        "Net Kâr ($)": kpis_2024["net_profit"],
        "Cycle Sayısı": kpis_2024["total_cycles"],
        "Aktif Gün": kpis_2024["active_days"],
        "Pas Geçilen Gün": kpis_2024["passed_days"],
        "Cycle Başı Kâr ($)": kpis_2024["profit_per_cycle"],
        "Ort. Deşarj Fiyatı ($/MWh)": kpis_2024["avg_discharge_price"],
        "Ort. Şarj Fiyatı ($/MWh)": kpis_2024["avg_charge_price"],
        "Gerçekleşen Spread ($/MWh)": kpis_2024["realized_spread"],
    },
    {
        "Yıl": "2025",
        "Deşarj Geliri ($)": kpis_2025["total_revenue"],
        "Şarj Maliyeti ($)": kpis_2025["total_cost"],
        "Brüt Kâr ($)": kpis_2025["gross_profit"],
        "Yıpranma Maliyeti ($)": kpis_2025["total_degradation_cost"],
        "Net Kâr ($)": kpis_2025["net_profit"],
        "Cycle Sayısı": kpis_2025["total_cycles"],
        "Aktif Gün": kpis_2025["active_days"],
        "Pas Geçilen Gün": kpis_2025["passed_days"],
        "Cycle Başı Kâr ($)": kpis_2025["profit_per_cycle"],
        "Ort. Deşarj Fiyatı ($/MWh)": kpis_2025["avg_discharge_price"],
        "Ort. Şarj Fiyatı ($/MWh)": kpis_2025["avg_charge_price"],
        "Gerçekleşen Spread ($/MWh)": kpis_2025["realized_spread"],
    }
])

# --- ANA EKRAN ---
strat_display_name = "Günde 2 Döngü (Çift Blok)" if strategy == "2_cycle" else "Günde 1 Döngü (Tek Blok)"
st.markdown('<div class="main-title">⚡ BESS PTF Spread Arbitraj Optimizasyonu</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">EPİAŞ {selected_year} Yılı Saatlik Gerçek PTF ($/MWh) | {strat_display_name} | Başlangıç SoC: %{soc_start_pct} ➔ Bitiş SoC: %{soc_end_pct} | Yıpranma: ${degradation_cost:.1f}/MWh</div>',
    unsafe_allow_html=True
)

# --- KPI METRİK KARTLARI ---
cards = [
    f"""<div class="kpi-card">
<div class="kpi-label">💰 Net Arbitraj Kârı</div>
<div class="kpi-value kpi-profit">${kpis['net_profit']:,.0f}</div>
<div class="kpi-sub">Brüt: ${kpis['gross_profit']:,.0f} | Günlük Ort: ${kpis['avg_daily_profit']:,.1f}</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🟢 Deşarj Geliri</div>
<div class="kpi-value">${kpis['total_revenue']:,.0f}</div>
<div class="kpi-sub">Ort: ${kpis['avg_discharge_price']:.1f} / MWh</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🔴 Şarj Maliyeti</div>
<div class="kpi-value kpi-cost">${kpis['total_cost']:,.0f}</div>
<div class="kpi-sub">Ort: ${kpis['avg_charge_price']:.1f} / MWh</div>
</div>"""
]

if degradation_cost > 0:
    cards.append(f"""<div class="kpi-card">
<div class="kpi-label">🛠️ Yıpranma Maliyeti</div>
<div class="kpi-value kpi-cost">${kpis['total_degradation_cost']:,.0f}</div>
<div class="kpi-sub">${degradation_cost:.1f} / MWh birim</div>
</div>""")

cards.extend([
    f"""<div class="kpi-card">
<div class="kpi-label">🔋 Toplam Yapılan Cycle</div>
<div class="kpi-value kpi-cycle">{kpis['total_cycles']:,.0f}</div>
<div class="kpi-sub">{kpis['active_days']} aktif / {kpis['passed_days']} pas geçilen gün</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">💎 Cycle Başı Net Kâr</div>
<div class="kpi-value kpi-profit">${kpis['profit_per_cycle']:,.2f}</div>
<div class="kpi-sub">Net kâr / Toplam cycle</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🎯 Yıl Boyu Ortalama Fiyat Makası (Alış-Satış Farkı)</div>
<div class="kpi-value">${kpis['realized_spread']:,.1f} <span style="font-size: 0.95rem; font-weight: 500; color: #94a3b8;">/ MWh</span></div>
<div class="kpi-sub">Ort. Deşarj Satış - Ort. Şarj Alış</div>
</div>"""
])

kpi_html = f'<div class="kpi-container">{"".join(cards)}</div>'
st.markdown(kpi_html, unsafe_allow_html=True)

# --- SEKME DÜZENİ ---
tab_daily, tab_monthly, tab_comparison = st.tabs([
    "📈 Günlük Arbitraj Detayı (Seçilen Gün)",
    "📊 Aylık ve Yıllık Kırılım",
    "⚖️ 2024 vs 2025 Kıyaslama",
])

# =========================================================================
# SEKME 1: GÜNLÜK ARBİTRAJ DETAYI
# =========================================================================
with tab_daily:
    st.markdown("#### 📅 Gün Seçimi ve 24 Saatlik Şarj / Deşarj Grafiği")
    st.caption("Günün en uygun fiyatlı saatinde şarj, en yüksek fiyatlı saatinde deşarj operasyonu ve saatlik batarya doluluk (SoC) profili.")

    # Tarih Seçim Paneli (Takvim Kartı + Gün, Ay, Yıl Kartları)
    months_dict = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
        5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
        9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }

    # Session state başlangıç değerleri
    if "card_day" not in st.session_state:
        st.session_state["card_day"] = 1
    if "card_month" not in st.session_state:
        st.session_state["card_month"] = 1
    if "card_year" not in st.session_state:
        st.session_state["card_year"] = selected_year
    if "cal_date_val" not in st.session_state:
        st.session_state["cal_date_val"] = datetime.date(selected_year, 1, 1)

    # Eğer sidebar'dan yıl değiştiyse kartları ve takvimi senkronize et
    if st.session_state.get("card_year") != selected_year:
        st.session_state["card_year"] = selected_year
        m = st.session_state.get("card_month", 1)
        max_d = calendar.monthrange(selected_year, m)[1]
        d = min(st.session_state.get("card_day", 1), max_d)
        st.session_state["card_day"] = d
        st.session_state["cal_date_val"] = datetime.date(selected_year, m, d)

    def sync_from_calendar():
        new_d = st.session_state["cal_date_val"]
        st.session_state["card_day"] = new_d.day
        st.session_state["card_month"] = new_d.month
        st.session_state["card_year"] = new_d.year
        if st.session_state.get("selected_year_sidebar") != new_d.year:
            st.session_state["selected_year_sidebar"] = new_d.year
            st.rerun()

    def sync_from_cards():
        y = st.session_state["card_year"]
        m = st.session_state["card_month"]
        max_d = calendar.monthrange(y, m)[1]
        d = min(st.session_state["card_day"], max_d)
        st.session_state["card_day"] = d
        st.session_state["cal_date_val"] = datetime.date(y, m, d)
        if st.session_state.get("selected_year_sidebar") != y:
            st.session_state["selected_year_sidebar"] = y
            st.rerun()

    # 4 Tarih Kartı + 2 Özet Metrik Kartı
    col_d, col_m, col_y, col_cal, col_d2, col_d3 = st.columns([1.0, 1.35, 1.0, 1.45, 1.2, 1.2])

    with col_d:
        st.markdown('<div class="date-mini-label">📌 GÜN</div>', unsafe_allow_html=True)
        cur_y = st.session_state.get("card_year", selected_year)
        cur_m = st.session_state.get("card_month", 1)
        max_days = calendar.monthrange(cur_y, cur_m)[1]
        if st.session_state.get("card_day", 1) > max_days:
            st.session_state["card_day"] = max_days
        elif st.session_state.get("card_day", 1) < 1:
            st.session_state["card_day"] = 1
        st.number_input(
            "Gün",
            min_value=1,
            max_value=max_days,
            key="card_day",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_m:
        st.markdown('<div class="date-mini-label">📆 AY</div>', unsafe_allow_html=True)
        st.selectbox(
            "Ay",
            options=list(months_dict.keys()),
            format_func=lambda x: f"{x:02d} - {months_dict[x]}",
            key="card_month",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_y:
        st.markdown('<div class="date-mini-label">🗓️ YIL</div>', unsafe_allow_html=True)
        st.selectbox(
            "Yıl",
            options=available_years,
            key="card_year",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_cal:
        st.markdown('<div class="date-mini-label">📅 TAKVİM KARTI</div>', unsafe_allow_html=True)
        active_cal_y = st.session_state["card_year"]
        if st.session_state.get("cal_date_val") and st.session_state["cal_date_val"].year != active_cal_y:
            m = st.session_state.get("card_month", 1)
            max_d = calendar.monthrange(active_cal_y, m)[1]
            d = min(st.session_state.get("card_day", 1), max_d)
            st.session_state["cal_date_val"] = datetime.date(active_cal_y, m, d)
        st.date_input(
            "Takvim",
            min_value=datetime.date(active_cal_y, 1, 1),
            max_value=datetime.date(active_cal_y, 12, 31),
            key="cal_date_val",
            on_change=sync_from_calendar,
            label_visibility="collapsed"
        )

    # Seçilen günün tarihi
    selected_date_dt = st.session_state["cal_date_val"]
    selected_date = pd.to_datetime(selected_date_dt)

    # Seçilen günün verilerini al
    day_matches = daily_df[daily_df["date"] == selected_date]
    if day_matches.empty:
        selected_date = daily_df["date"].iloc[0]
        day_summary = daily_df.iloc[0]
    else:
        day_summary = day_matches.iloc[0]

    day_hourly = hourly_df[hourly_df["date"] == selected_date].copy().sort_values("hour").reset_index(drop=True)

    with col_d2:
        if day_summary.get("is_passed", False):
            st.metric("Günlük Net Kâr", "$0.00", "🛡️ Pas Geçildi", delta_color="off")
        else:
            sub_txt = f"Brüt: ${day_summary['gross_profit']:.1f}" if degradation_cost > 0 else f"Spread: ${day_summary['ptf_spread']:.1f}"
            st.metric("Günlük Net Kâr", f"${day_summary['net_profit']:.2f}", sub_txt)
    with col_d3:
        if day_summary.get("is_passed", False):
            st.metric("O Günkü Cycle", "0.00 EFC", f"Spread: ${day_summary['ptf_spread']:.1f}")
        else:
            deg_sub = f"Yıpranma: -${day_summary['degradation_cost']:.1f}" if degradation_cost > 0 else f"Spread: ${day_summary['ptf_spread']:.1f}"
            st.metric("O Günkü Cycle", f"{day_summary['cycles']:.2f} EFC", deg_sub)

    # Eğer gün pas geçildiyse bilgilendirme kartı göster
    if day_summary.get("is_passed", False):
        st.warning(
            f"🛡️ **Bu Gün Pas Geçildi (İşlem Yapılmadı):** "
            f"Günün PTF fiyat farkı (${day_summary['ptf_spread']:.1f}/MWh), şarj maliyetini ve yıpranma maliyetini (${degradation_cost:.1f}/MWh) "
            "karşılamadığı için net kâr negatife düşecekti. Batarya gün boyu bekletilmiş (idle), kâr/zarar $0.00 olarak korunmuştur."
        )

    # Plotly Grafiği: PTF Eğrisi + Kesinlikle Tekil Şarj/Deşarj Noktaları + SoC Alanı
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Saatlik PTF ($/MWh) & Şarj / Deşarj Noktaları", "Batarya Doluluk Oranı (SoC %)"),
        row_heights=[0.68, 0.32]
    )

    # 1. PTF Çizgisi
    fig.add_trace(
        go.Scatter(
            x=day_hourly["hour"],
            y=day_hourly["ptf_usd"],
            mode="lines",
            name="PTF ($/MWh)",
            line=dict(color="#cbd5e1", width=2.8, shape="spline", smoothing=0.5),
            hovertemplate="Saat %{x:02d}:00<br>PTF: <b>$%{y:.2f}/MWh</b><extra></extra>",
        ),
        row=1, col=1
    )

    # 1. ve 2. Şarj & Deşarj Noktaları (Eğer o gün kârlı bir işlem yapıldıysa)
    if not day_summary.get("is_passed", False) and day_summary["net_profit"] > 0:
        ch1_val = day_summary.get("ch1_hour")
        if ch1_val is None or pd.isna(ch1_val):
            ch1_val = day_summary.get("best_ch")
        dis1_val = day_summary.get("dis1_hour")
        if dis1_val is None or pd.isna(dis1_val):
            dis1_val = day_summary.get("best_dis")
        ch2_val = day_summary.get("ch2_hour")
        dis2_val = day_summary.get("dis2_hour")

        has_two_cycles = pd.notna(ch2_val) and ch2_val is not None

        # 1. Şarj Noktası
        if pd.notna(ch1_val) and ch1_val is not None:
            ch1_int = int(ch1_val)
            ch1_row = day_hourly[day_hourly["hour"] == ch1_int].iloc[0]
            ch1_name = "🔋 1. Şarj Saati" if has_two_cycles else "🔋 Şarj Saati"
            ch1_txt = f"Şarj 1: {ch1_row['p_ch_mw']:.1f}MW" if has_two_cycles else f"Şarj: {ch1_row['p_ch_mw']:.1f}MW"
            fig.add_trace(
                go.Scatter(
                    x=[ch1_int],
                    y=[ch1_row["ptf_usd"]],
                    mode="markers+text",
                    name=ch1_name,
                    marker=dict(
                        color="#38bdf8",
                        size=16,
                        symbol="circle",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[ch1_txt],
                    textposition="bottom center",
                    textfont=dict(size=12, color="#38bdf8", family="Inter"),
                    hovertemplate=f"<b>{'1. ' if has_two_cycles else ''}ŞARJ SAATİ</b><br>Saat: {ch1_int:02d}:00<br>Fiyat: ${ch1_row['ptf_usd']:.2f}/MWh<br>Şarj: {ch1_row['p_ch_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        # 1. Deşarj Noktası
        if pd.notna(dis1_val) and dis1_val is not None:
            dis1_int = int(dis1_val)
            dis1_row = day_hourly[day_hourly["hour"] == dis1_int].iloc[0]
            dis1_name = "⚡ 1. Deşarj Saati" if has_two_cycles else "⚡ Deşarj Saati"
            dis1_txt = f"Deşarj 1: {dis1_row['p_dis_mw']:.1f}MW" if has_two_cycles else f"Deşarj: {dis1_row['p_dis_mw']:.1f}MW"
            fig.add_trace(
                go.Scatter(
                    x=[dis1_int],
                    y=[dis1_row["ptf_usd"]],
                    mode="markers+text",
                    name=dis1_name,
                    marker=dict(
                        color="#10b981",
                        size=16,
                        symbol="circle",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[dis1_txt],
                    textposition="top center",
                    textfont=dict(size=12, color="#34d399", family="Inter"),
                    hovertemplate=f"<b>{'1. ' if has_two_cycles else ''}DEŞARJ SAATİ</b><br>Saat: {dis1_int:02d}:00<br>Fiyat: ${dis1_row['ptf_usd']:.2f}/MWh<br>Deşarj: {dis1_row['p_dis_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        # 2. Şarj Noktası (varsa)
        if has_two_cycles:
            ch2_int = int(ch2_val)
            ch2_row = day_hourly[day_hourly["hour"] == ch2_int].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[ch2_int],
                    y=[ch2_row["ptf_usd"]],
                    mode="markers+text",
                    name="🔋 2. Şarj Saati",
                    marker=dict(
                        color="#60a5fa",
                        size=16,
                        symbol="diamond",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[f"Şarj 2: {ch2_row['p_ch_mw']:.1f}MW"],
                    textposition="bottom center",
                    textfont=dict(size=12, color="#60a5fa", family="Inter"),
                    hovertemplate=f"<b>2. ŞARJ SAATİ</b><br>Saat: {ch2_int:02d}:00<br>Fiyat: ${ch2_row['ptf_usd']:.2f}/MWh<br>Şarj: {ch2_row['p_ch_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        # 2. Deşarj Noktası (varsa)
        if pd.notna(dis2_val) and dis2_val is not None:
            dis2_int = int(dis2_val)
            dis2_row = day_hourly[day_hourly["hour"] == dis2_int].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[dis2_int],
                    y=[dis2_row["ptf_usd"]],
                    mode="markers+text",
                    name="⚡ 2. Deşarj Saati",
                    marker=dict(
                        color="#34d399",
                        size=16,
                        symbol="diamond",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[f"Deşarj 2: {dis2_row['p_dis_mw']:.1f}MW"],
                    textposition="top center",
                    textfont=dict(size=12, color="#34d399", family="Inter"),
                    hovertemplate=f"<b>2. DEŞARJ SAATİ</b><br>Saat: {dis2_int:02d}:00<br>Fiyat: ${dis2_row['ptf_usd']:.2f}/MWh<br>Deşarj: {dis2_row['p_dis_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

    # 2. SoC Eğrisi (Alt Panel)
    fig.add_trace(
        go.Scatter(
            x=day_hourly["hour"],
            y=day_hourly["soc_pct"],
            mode="lines",
            name="SoC (%)",
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.18)",
            line=dict(color="#38bdf8", width=2.2, shape="hv"),
            hovertemplate="Saat %{x:02d}:00<br>SoC: <b>%{y:.1f}%</b><extra></extra>",
        ),
        row=2, col=1
    )

    # Grafik Tasarım Ayarları (Dark Theme Uyumlu)
    fig.update_layout(
        height=540,
        margin=dict(l=40, r=40, t=50, b=30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#e2e8f0")
        ),
        xaxis2=dict(
            title="Saat (00:00 - 23:00)",
            tickmode="linear",
            tick0=0,
            dtick=1,
            gridcolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color="#94a3b8"),
            title_font=dict(color="#cbd5e1"),
            linecolor="rgba(148, 163, 184, 0.25)"
        ),
        xaxis=dict(
            tickmode="linear",
            tick0=0,
            dtick=1,
            gridcolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color="#94a3b8"),
            linecolor="rgba(148, 163, 184, 0.25)"
        ),
        yaxis=dict(
            title="PTF ($/MWh)",
            gridcolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color="#94a3b8"),
            title_font=dict(color="#cbd5e1"),
            linecolor="rgba(148, 163, 184, 0.25)"
        ),
        yaxis2=dict(
            title="SoC (%)",
            range=[0, 110],
            gridcolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color="#94a3b8"),
            title_font=dict(color="#cbd5e1"),
            linecolor="rgba(148, 163, 184, 0.25)"
        ),
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=13, color='#e2e8f0', family='Inter')

    st.plotly_chart(fig, width="stretch")

    # Günlük Saatlik İşlem Tablosu (Accordion)
    with st.expander("📋 Bu Günün 24 Saatlik Detay Tablosunu Gör"):
        st.markdown(
            '<div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.6rem;">'
            '🔵 <b style="color: #38bdf8;">Mavi Satır:</b> Şarj Yapılan Saatler (Şarj 1 / Şarj 2) &nbsp;|&nbsp; '
            '🟢 <b style="color: #34d399;">Yeşil Satır:</b> Deşarj Yapılan Saatler (Deşarj 1 / Deşarj 2)'
            '</div>',
            unsafe_allow_html=True
        )
        display_day = day_hourly[[
            "saat_str", "ptf_usd", "p_ch_mw", "p_dis_mw", "soc_mwh", "soc_pct", "charge_cost", "discharge_revenue", "degradation_cost", "net_profit", "action_label"
        ]].copy()
        display_day.columns = [
            "Saat", "PTF ($/MWh)", "Şarj (MW)", "Deşarj (MW)", "SoC (MWh)", "SoC (%)", "Şarj Maliyeti ($)", "Deşarj Geliri ($)", "Yıpranma Maliyeti ($)", "Net Kâr ($)", "İşlem Durumu"
        ]

        def highlight_charge_discharge(row):
            # Şarj satırı mavi
            if row["Şarj (MW)"] > 0.001:
                return ["background-color: rgba(56, 189, 248, 0.28); color: #38bdf8; font-weight: 600;"] * len(row)
            # Deşarj satırı yeşil
            elif row["Deşarj (MW)"] > 0.001:
                return ["background-color: rgba(16, 185, 129, 0.28); color: #34d399; font-weight: 600;"] * len(row)
            return [""] * len(row)

        styled_display = display_day.style.apply(highlight_charge_discharge, axis=1).format({
            "PTF ($/MWh)": "${:.2f}",
            "Şarj (MW)": "{:.2f}",
            "Deşarj (MW)": "{:.2f}",
            "SoC (MWh)": "{:.2f}",
            "SoC (%)": "{:.1f}%",
            "Şarj Maliyeti ($)": "${:.2f}",
            "Deşarj Geliri ($)": "${:.2f}",
            "Yıpranma Maliyeti ($)": "${:.2f}",
            "Net Kâr ($)": "${:.2f}",
        })

        st.dataframe(styled_display, width="stretch")

# =========================================================================
# SEKME 2: AYLIK VE YILLIK KIRILIM
# =========================================================================
with tab_monthly:
    st.markdown("#### 📊 Aylık ve Yıllık Kırılım & 365 Günlük Excel Raporu")
    st.caption("Aylık bazda gerçekleşen net arbitraj kârı, yapılan tam döngü sayısı, cycle başına üretilen kâr ve 365 günlük Excel dışa aktarım aracı.")

    # 365 Günlük Kapsamlı Excel Rapor Kartı
    excel_card_html = (
        '<div style="background: rgba(30, 41, 59, 0.65); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1.2rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);">'
        '<div style="font-size: 1.12rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.5rem;">'
        '📥 <span>365 Günlük Detaylı Simülasyon ve Fizibilite Raporu (.xlsx)</span>'
        '</div>'
        '<div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.55;">'
        f'Seçilen <b>{selected_year}</b> yılı ve sol paneldeki <b>{power_mw:.1f} MW</b> güç, <b>%{rte*100:.0f}</b> RTE, <b>${degradation_cost:.1f}/MWh</b> yıpranma maliyeti, <b>%{soc_start_pct}</b> ➔ <b>%{soc_end_pct}</b> SoC ve <b>{strat_display_name}</b> parametrelerinize göre oluşturulan 5 sayfalı kapsamlı çalışma kitabı:<br>'
        '• ⏱️ <b>8760 Saatlik Detay:</b> Görseldeki 24 saatlik tablonun 365 günlük saatlik tam versiyonu (Tarih, Saat, PTF, Şarj/Deşarj MW, SoC %, Maliyet, Gelir, Yıpranma, Net Kâr, İşlem Durumu)<br>'
        '• 📅 <b>Günlük Özet (365 Gün):</b> Gün gün 1. ve 2. şarj/deşarj saatleri, enerji miktarları, döngüler ve aktif/pas durumları<br>'
        '• 📑 <b>Aylık Kırılım:</b> 12 ayın tüm finansal ve operasyonel metrikleri<br>'
        '• 📊 <b>Özet & Parametreler:</b> Sistem konfigürasyonu ve yıllık fizibilite KPI\'ları<br>'
        '• ⚖️ <b>2024 vs 2025 Kıyaslama:</b> Yıllık performans karşılaştırma tablosu'
        '</div>'
        '</div>'
    )
    st.markdown(excel_card_html, unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns([1.6, 1])
    with col_btn1:
        excel_bytes = generate_bess_excel_report(
            year=selected_year,
            config=BESSConfig(
                power_mw=power_mw,
                c_rate=c_rate,
                rte=rte,
                soc_start_pct=float(soc_start_pct),
                soc_end_pct=float(soc_end_pct),
                degradation_cost=float(degradation_cost),
                strategy=strategy,
            ),
            hourly_df=hourly_df,
            daily_df=daily_df,
            kpis=kpis,
            monthly_df=monthly_df,
            comp_df=comp_df
        )
        st.download_button(
            label="📥 365 Günlük Kapsamlı Excel Raporunu İndir (.xlsx)",
            data=excel_bytes,
            file_name=f"BESS_Arbitraj_{selected_year}_{power_mw:.0f}MW_365Gunluk_Detay.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )
    with col_btn2:
        st.caption("📁 **İçerik:** 5 Çalışma Sayfası | 8.760 Saatlik Tablo + 365 Günlük Özet + Aylık Kırılım + KPI + 2024/2025 Kıyaslama")

    st.markdown("---")

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        # 1. Aylık Net Kâr & Cycle Grafiği
        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])

        fig_monthly.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["net_profit"],
                name="Net Kâr ($)",
                marker=dict(color="#10b981", opacity=0.88, line=dict(color="#059669", width=1)),
                hovertemplate="%{x}<br>Net Kâr: <b>$%{y:,.2f}</b><extra></extra>"
            ),
            secondary_y=False
        )

        if degradation_cost > 0:
            fig_monthly.add_trace(
                go.Bar(
                    x=monthly_df["month_name"],
                    y=monthly_df["degradation_cost"],
                    name="Yıpranma ($)",
                    marker=dict(color="#f87171", opacity=0.75, line=dict(color="#dc2626", width=1)),
                    hovertemplate="%{x}<br>Yıpranma: <b>$%{y:,.2f}</b><extra></extra>"
                ),
                secondary_y=False
            )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["month_name"],
                y=monthly_df["cycles"],
                name="Cycle",
                mode="lines+markers",
                marker=dict(color="#38bdf8", size=6),
                line=dict(color="#38bdf8", width=2),
                hovertemplate="%{x}<br>Cycle: <b>%{y:.0f}</b><extra></extra>"
            ),
            secondary_y=True
        )

        fig_monthly.update_layout(
            title=dict(text="Aylık Net Kâr ($) ve Cycle", font=dict(size=12.5, color="#f8fafc")),
            height=315,
            margin=dict(l=35, r=35, t=45, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9.5, color="#e2e8f0")),
            xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9)),
            yaxis=dict(title="Dolar ($)", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9), title_font=dict(color="#cbd5e1", size=10)),
            yaxis2=dict(title="Cycle", overlaying="y", side="right", showgrid=False, tickfont=dict(color="#38bdf8", size=9), title_font=dict(color="#38bdf8", size=10))
        )
        st.plotly_chart(fig_monthly, width="stretch")

    with col_m2:
        # 2. Aylık Cycle Başına Kâr ($/Cycle)
        fig_per_cycle = go.Figure()
        fig_per_cycle.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["profit_per_cycle"],
                marker=dict(color="#38bdf8", opacity=0.88, line=dict(color="#0284c7", width=1)),
                hovertemplate="%{x}<br>Cycle Başı Kâr: <b>$%{y:.2f}</b><extra></extra>"
            )
        )
        fig_per_cycle.update_layout(
            title=dict(text="Aylık Cycle Başı Net Kâr ($/Cycle)", font=dict(size=12.5, color="#f8fafc")),
            height=315,
            margin=dict(l=35, r=25, t=45, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9)),
            yaxis=dict(title="$/Cycle", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9), title_font=dict(color="#cbd5e1", size=10)),
        )
        st.plotly_chart(fig_per_cycle, width="stretch")

    with col_m3:
        # 3. Aylık Ortalama PTF ve Günlük PTF Spread (Makas) Grafiği
        fig_spread_ptf = make_subplots(specs=[[{"secondary_y": True}]])

        # Bar Grafiği: Aylık Ortalama Günlük PTF Spread ($/MWh)
        fig_spread_ptf.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["avg_spread"],
                name="Ort. Spread",
                marker=dict(
                    color="#f59e0b",
                    opacity=0.85,
                    line=dict(color="#d97706", width=1.0)
                ),
                hovertemplate="%{x}<br>Ort. Spread: <b>$%{y:.2f} / MWh</b><extra></extra>"
            ),
            secondary_y=False
        )

        # Çizgi Grafiği: Aylık Ortalama PTF ($/MWh)
        fig_spread_ptf.add_trace(
            go.Scatter(
                x=monthly_df["month_name"],
                y=monthly_df["avg_ptf"],
                name="Ort. PTF",
                mode="lines+markers",
                marker=dict(
                    color="#38bdf8",
                    size=6,
                    symbol="circle",
                    line=dict(color="#ffffff", width=1.2)
                ),
                line=dict(color="#38bdf8", width=2),
                hovertemplate="%{x}<br>Aylık Ort. PTF: <b>$%{y:.2f} / MWh</b><extra></extra>"
            ),
            secondary_y=True
        )

        fig_spread_ptf.update_layout(
            title=dict(
                text="Ortalama PTF ve Fiyat Spreadi ($/MWh)",
                font=dict(size=12.5, color="#f8fafc")
            ),
            height=315,
            margin=dict(l=35, r=35, t=45, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=9.5, color="#e2e8f0")
            ),
            xaxis=dict(
                gridcolor="rgba(148, 163, 184, 0.12)",
                tickfont=dict(color="#94a3b8", size=9)
            ),
            yaxis=dict(
                title="Spread ($/MWh)",
                gridcolor="rgba(148, 163, 184, 0.12)",
                tickfont=dict(color="#f59e0b", size=9),
                title_font=dict(color="#f59e0b", size=10),
                linecolor="rgba(148, 163, 184, 0.25)",
                rangemode="tozero"
            ),
            yaxis2=dict(
                title="Ort. PTF ($/MWh)",
                overlaying="y",
                side="right",
                showgrid=False,
                tickfont=dict(color="#38bdf8", size=9),
                title_font=dict(color="#38bdf8", size=10),
                linecolor="rgba(56, 189, 248, 0.25)",
                rangemode="tozero"
            )
        )

        st.plotly_chart(fig_spread_ptf, width="stretch")

    # Aylık Tablo
    st.markdown("##### 📑 Aylık Özet Performans Tablosu")
    display_monthly = monthly_df[[
        "month_name", "discharge_revenue", "charge_cost", "gross_profit", "degradation_cost",
        "net_profit", "cycles", "active_days", "passed_days", "profit_per_cycle", "avg_spread", "avg_ptf"
    ]].copy()
    display_monthly.columns = [
        "Ay", "Deşarj Geliri ($)", "Şarj Maliyeti ($)", "Brüt Kâr ($)", "Yıpranma Maliyeti ($)",
        "Net Arbitraj Kârı ($)", "Toplam Cycle", "Aktif Gün", "Pas Geçilen Gün", "Cycle Başı Kâr ($/Cycle)",
        "Ort. Günlük Spread ($/MWh)", "Aylık Ort. PTF ($/MWh)"
    ]

    st.dataframe(
        display_monthly.style.format({
            "Deşarj Geliri ($)": "${:,.2f}",
            "Şarj Maliyeti ($)": "${:,.2f}",
            "Brüt Kâr ($)": "${:,.2f}",
            "Yıpranma Maliyeti ($)": "${:,.2f}",
            "Net Arbitraj Kârı ($)": "${:,.2f}",
            "Toplam Cycle": "{:.0f}",
            "Aktif Gün": "{:.0f}",
            "Pas Geçilen Gün": "{:.0f}",
            "Cycle Başı Kâr ($/Cycle)": "${:.2f}",
            "Ort. Günlük Spread ($/MWh)": "${:.2f}",
            "Aylık Ort. PTF ($/MWh)": "${:.2f}",
        }),
        width="stretch"
    )

# =========================================================================
# SEKME 3: 2024 vs 2025 KARŞILAŞTIRMA
# =========================================================================
with tab_comparison:
    st.markdown("#### ⚖️ 2024 ve 2025 Yıllık BESS Performans Kıyaslaması (1C Arbitraj)")
    st.caption("Aynı batarya konfigürasyonu ile 2024 ve 2025 PTF spread dinamiklerinin arbitraj kârlılığına etkisi.")

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        diff_profit = kpis_2025['net_profit'] - kpis_2024['net_profit']
        pct_diff = (diff_profit / kpis_2024['net_profit'] * 100) if kpis_2024['net_profit'] > 0 else 0.0
        st.metric(
            "2025 Net Kâr",
            f"${kpis_2025['net_profit']:,.2f}",
            delta=f"${diff_profit:+,.2f} (%{pct_diff:+.1f})"
        )
    with col_c2:
        diff_cycles = kpis_2025['total_cycles'] - kpis_2024['total_cycles']
        st.metric(
            "2025 Toplam Cycle",
            f"{kpis_2025['total_cycles']:.0f}",
            delta=f"{diff_cycles:+.0f} Cycle"
        )
    with col_c3:
        diff_per_cy = kpis_2025['profit_per_cycle'] - kpis_2024['profit_per_cycle']
        st.metric(
            "2025 Cycle Başı Net Kâr",
            f"${kpis_2025['profit_per_cycle']:.2f}",
            delta=f"${diff_per_cy:+.2f} / Cycle"
        )

    st.markdown("##### 📋 Yıllık Karşılaştırma Metrikleri Tablosu")
    st.dataframe(
        comp_df.style.format({
            "Deşarj Geliri ($)": "${:,.2f}",
            "Şarj Maliyeti ($)": "${:,.2f}",
            "Brüt Kâr ($)": "${:,.2f}",
            "Yıpranma Maliyeti ($)": "${:,.2f}",
            "Net Kâr ($)": "${:,.2f}",
            "Cycle Sayısı": "{:.0f}",
            "Aktif Gün": "{:.0f}",
            "Pas Geçilen Gün": "{:.0f}",
            "Cycle Başı Kâr ($)": "${:.2f}",
            "Ort. Deşarj Fiyatı ($/MWh)": "${:.2f}",
            "Ort. Şarj Fiyatı ($/MWh)": "${:.2f}",
            "Gerçekleşen Spread ($/MWh)": "${:.2f}",
        }),
        width="stretch"
    )

    # 2024 vs 2025 Aylık Net Kâr Karşılaştırma Grafiği
    fig_comp_m = go.Figure()
    fig_comp_m.add_trace(
        go.Bar(
            x=monthly_2024["month_name"],
            y=monthly_2024["net_profit"],
            name="2024 Net Kâr ($)",
            marker_color="#64748b"
        )
    )
    fig_comp_m.add_trace(
        go.Bar(
            x=monthly_2025["month_name"],
            y=monthly_2025["net_profit"],
            name="2025 Net Kâr ($)",
            marker_color="#10b981"
        )
    )
    fig_comp_m.update_layout(
        title=dict(text="2024 vs 2025 Aylık Net Kâr Karşılaştırması ($)", font=dict(color="#f8fafc")),
        barmode="group",
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1, font=dict(color="#e2e8f0")),
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8")),
        yaxis=dict(title="Net Kâr ($)", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8"), title_font=dict(color="#cbd5e1")),
    )
    st.plotly_chart(fig_comp_m, width="stretch")
