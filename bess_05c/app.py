"""
BESS 0.5C (2 Saatlik Depolama) Sürekli Doğrusal Programlama (LP) & Kısmi Güç Modülasyonu Paneli
Standart: design-taste-frontend (Anti-Emoji, Calibrated Dark Slate UI, JetBrains Mono, Outfit/Inter)
Matematiksel Çözücü: SciPy HiGHS Doğrusal Programlama (Linear Programming)
"""

import sys
import datetime
import calendar
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Any
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Proje dizinini ekle
bess_dir = Path(__file__).resolve().parent
if str(bess_dir) not in sys.path:
    sys.path.insert(0, str(bess_dir))

from src.styles import CUSTOM_CSS, ICONS, make_icon_badge, clean_html
from src.data_loader import load_all_ptf_data
from src.optimizer_05c import (
    BESSConfig05C,
    LPStrategy,
    LP_STRATEGY_METADATA,
    simulate_period_05c,
    aggregate_monthly_05c
)
from src.excel_export import generate_05c_excel_report
from src.metrics import build_strategy_comparison_table, build_yearly_comparison_table
from src.charts import (
    build_daily_dispatch_chart,
    build_cumulative_profit_chart,
    build_daily_cycles_bar_chart,
    build_monthly_financial_chart,
    build_monthly_cycles_chart,
    build_strategy_comparison_barchart,
    build_yearly_comparison_chart
)
from src.ui_cards import (
    render_header_banner,
    render_kpi_cards,
    render_daily_mini_kpi_cards,
    render_strategy_comparison_cards,
    render_strategy_guide_cards
)

# Sayfa Konfigürasyonu
st.set_page_config(
    page_title="Standalone BESS Arbitraj Stratejisi | 0.5C Depolama",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Enjeksiyonu
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =============================================================================
# VERİ VE SİMÜLASYON ÖNBELLEKLEME (Streamlit Cache)
# =============================================================================
@st.cache_data(show_spinner=False)
def get_cached_ptf_data() -> Dict[int, pd.DataFrame]:
    """EPİAŞ PTF verilerini bir kez yükler ve önbelleğe alır."""
    return load_all_ptf_data()


@st.cache_data(show_spinner=False)
def get_cached_excel_report(
    year: int,
    power_mw: float,
    c_rate: float,
    rte: float,
    soc_start_pct: float,
    soc_end_pct: float,
    degradation_cost: float,
    strategy: str,
    ramp_limit_mw: Optional[float],
    _hourly_df: pd.DataFrame,
    _daily_df: pd.DataFrame,
    _kpis: dict,
    _monthly_df: pd.DataFrame,
    _comp_df: pd.DataFrame
) -> bytes:
    """Excel raporunu parametreler değişmediği sürece önbellekten sunar."""
    cfg = BESSConfig05C(
        power_mw=power_mw,
        c_rate=c_rate,
        rte=rte,
        soc_start_pct=soc_start_pct,
        soc_end_pct=soc_end_pct,
        degradation_cost=degradation_cost,
        strategy=strategy,
        ramp_limit_mw=ramp_limit_mw
    )
    return generate_05c_excel_report(
        year=year,
        config=cfg,
        hourly_df=_hourly_df,
        daily_df=_daily_df,
        kpis=_kpis,
        monthly_df=_monthly_df,
        comp_df=_comp_df
    )


@st.cache_data(show_spinner=False)
def get_cached_period_simulation(
    year: int,
    power_mw: float,
    c_rate: float,
    rte: float,
    soc_start_pct: float,
    soc_end_pct: float,
    degradation_cost: float,
    strategy: str,
    ramp_limit_mw: Optional[float],
    num_days: Optional[int]
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any]]:
    """Belirli bir yıl ve parametre seti için LP simülasyonunu çözer ve önbelleğe alır."""
    data = get_cached_ptf_data()
    df = data.get(year)
    if df is None:
        return None, None, {}
    cfg = BESSConfig05C(
        power_mw=power_mw,
        c_rate=c_rate,
        rte=rte,
        soc_start_pct=soc_start_pct,
        soc_end_pct=soc_end_pct,
        degradation_cost=degradation_cost,
        strategy=strategy,
        ramp_limit_mw=ramp_limit_mw
    )
    return simulate_period_05c(df, cfg, strategy=strategy, num_days=num_days)


# =============================================================================
# SOL PANEL: PARAMETRELER VE SENARYO SEÇİCİLERİ
# =============================================================================
raw_data = get_cached_ptf_data()
available_years = sorted(list(raw_data.keys())) if raw_data else [2024, 2025]

st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.65rem; font-size: 1.02rem; font-weight: 700; color: #ffffff; margin-bottom: 0.85rem;">
        {make_icon_badge(ICONS['calendar'], color="#38bdf8", bg="rgba(14, 165, 233, 0.15)", border="rgba(14, 165, 233, 0.35)", size=30)}
        <span>Piyasa & Analiz Yılı</span>
    </div>
    """),
    unsafe_allow_html=True
)

if not raw_data:
    st.sidebar.warning("PTF CSV dosyaları bulunamadı, varsayılan sentetik fiyatlar kullanılıyor.")

if "selected_year_05c" not in st.session_state:
    st.session_state["selected_year_05c"] = available_years[-1] if available_years else 2025

selected_year = st.sidebar.selectbox(
    "Analiz Yılı",
    available_years,
    key="selected_year_05c",
    help="Seçilen yılın saatlik EPİAŞ PTF ($/MWh) fiyat eğrisi üzerinde senaryo optimizasyonu yapılır."
)

# -----------------------------------------------------------------------------
# 1. STRATEJİ
# -----------------------------------------------------------------------------
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1rem 0;'>", unsafe_allow_html=True)
st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">
        {make_icon_badge(ICONS['battery'], color="#38bdf8", bg="rgba(14, 165, 233, 0.12)", border="rgba(14, 165, 233, 0.28)", size=26)}
        <span>Strateji</span>
    </div>
    """),
    unsafe_allow_html=True
)

strategy_display_map = {
    "1. Günde 1 döngü": LPStrategy.LP_1_CYCLE,
    "2. Günde 1.5 döngü(olası pikleri yakalama)": LPStrategy.LP_15_CYCLE,
}

strategy_choice = st.sidebar.radio(
    "Strateji",
    options=list(strategy_display_map.keys()),
    index=0,
    label_visibility="collapsed",
    help="Bataryanın günlük arbitraj çalışma stratejisi."
)
active_strategy = strategy_display_map[strategy_choice]

# Strateji Açıklama Rozeti
if active_strategy == LPStrategy.LP_1_CYCLE:
    st.sidebar.markdown(
        clean_html(f"""
        <div class="bess-info-box">
            <div style="font-weight: 600; color: #38bdf8; margin-bottom: 0.25rem;">Günde 1 Döngü</div>
            • <b>Döngü Limiti:</b> Günde maksimum 1.0 EFC (1 tam döngü).<br>
            • <b>Modülasyon:</b> Güç [0, P_max] aralığında sürekli değişkendir.<br>
            • <b>Hedef:</b> Hücre ömrünü ve garanti sınırlarını korur; tek döngüde en kârlı saatleri seçer.
        </div>
        """),
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        clean_html(f"""
        <div class="bess-info-box">
            <div style="font-weight: 600; color: #4edea3; margin-bottom: 0.25rem;">Günde 1.5 Döngü (Olası Pikleri Yakalama)</div>
            • <b>Döngü Limiti:</b> Günde maksimum 1.5 EFC (1.5 döngü).<br>
            • <b>Kısmi Güç:</b> Sabah veya öğle ara piklerinde fırsatçı şarj/deşarj modülasyonu.<br>
            • <b>Fırsat:</b> Tam 2 döngü yıpranması yapmadan ek pik getirisi sağlar.
        </div>
        """),
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 2. BATARYA ÖZELLİKLERİ
# -----------------------------------------------------------------------------
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1rem 0;'>", unsafe_allow_html=True)
st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">
        {make_icon_badge(ICONS['battery'], color="#38bdf8", bg="rgba(14, 165, 233, 0.12)", border="rgba(14, 165, 233, 0.28)", size=26)}
        <span>Batarya Özellikleri</span>
    </div>
    """),
    unsafe_allow_html=True
)

power_mw = st.sidebar.slider(
    "Nominal Güç (MW)",
    min_value=0.5,
    max_value=150.0,
    value=50.0,
    step=0.5,
    help="Bataryanın maksimum şarj ve deşarj gücü."
)

c_rate = 0.5
duration_hours = 2.0
capacity_mwh = power_mw * duration_hours

st.sidebar.markdown(
    clean_html(f"""
    <div class="bess-info-box">
        <div style="font-family: var(--font-mono); font-size: 0.74rem; text-transform: uppercase; color: #38bdf8; font-weight: 700; margin-bottom: 0.25rem;">
            Konfigürasyon: 0.5C (2 Saatlik Depolama)
        </div>
        <div>• Nominal Güç: <b style="color: #ffffff;">{power_mw:.1f} MW</b></div>
        <div>• Enerji Kapasitesi: <b style="color: #ffffff;">{capacity_mwh:.1f} MWh</b></div>
        <div>• C-Rate & Süre: <b style="color: #38bdf8;">0.5C (2.0 Saat)</b></div>
        <div>• Optimizasyon: <b style="color: #4edea3;">Sürekli Senaryo Modülasyonu</b></div>
    </div>
    """),
    unsafe_allow_html=True
)

rte_percent = st.sidebar.slider(
    "Döngü Verimliliği (RTE %)",
    min_value=70,
    max_value=98,
    value=85,
    step=1,
    help="Şarj-Deşarj Round-Trip Efficiency. Örn: %85 verimlilikte 100 MWh şarj karşılığı 85 MWh net elektrik şebekeye verilir."
)
rte = rte_percent / 100.0

# Rampa sınırı: BESS inverterleri milisaniye hızında tepki verdiğinden
# saatlik piyasada rampa kısıtı işletmesel kısıt oluşturmaz (None = Sınırsız).
ramp_limit_mw = None

# -----------------------------------------------------------------------------
# 3. İŞLETMECİ SOC & DoD YÖNETİMİ
# -----------------------------------------------------------------------------
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1rem 0;'>", unsafe_allow_html=True)
st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">
        {make_icon_badge(ICONS['target'], color="#38bdf8", bg="rgba(14, 165, 233, 0.12)", border="rgba(14, 165, 233, 0.28)", size=26)}
        <span>İşletmeci SoC & DoD Yönetimi</span>
    </div>
    """),
    unsafe_allow_html=True
)

soc_start_pct = st.sidebar.slider(
    "Güne Başlangıç SoC / Taban Rezerv (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="İşletmecinin gün başında (00:00) bataryada devraldığı ve gün boyu altına inilmeyecek taban güvenlik rezervi (DoD alt sınırı)."
)

soc_end_pct = st.sidebar.slider(
    "Gün Sonu Hedef SoC (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="İşletmecinin gün sonunda (23:00) bataryayı devretmek istediği hedef doluluk yüzdesi."
)

effective_min_soc = min(soc_start_pct, soc_end_pct)
effective_dod = 100 - effective_min_soc
usable_cap_mwh = capacity_mwh * (effective_dod / 100.0)

st.sidebar.caption(
    f"🛡️ **Etkin DoD:** %{effective_dod} | "
    f"**Kullanılabilir:** {usable_cap_mwh:.1f} MWh "
    f"(Taban Rezerv: %{effective_min_soc})"
)

# -----------------------------------------------------------------------------
# 4. MALİYET KALEMLERİ
# -----------------------------------------------------------------------------
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1rem 0;'>", unsafe_allow_html=True)
st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">
        {make_icon_badge(ICONS['dollar'], color="#38bdf8", bg="rgba(14, 165, 233, 0.12)", border="rgba(14, 165, 233, 0.28)", size=26)}
        <span>Maliyet Kalemleri</span>
    </div>
    """),
    unsafe_allow_html=True
)

degradation_cost = st.sidebar.number_input(
    "Yıpranma Maliyeti ($/MWh)",
    min_value=0.0,
    max_value=200.0,
    value=0.0,
    step=1.0,
    help="Döngü başına MWh bazında hücre amortisman ve yıpranma maliyeti ($/MWh). Arbitraj kârı bu maliyeti ve verimlilik kaybını kurtarmıyorsa gün pas geçilir."
)

if degradation_cost > 0:
    st.sidebar.caption(
        f"Bilgi: {power_mw:.1f} MW / {capacity_mwh:.1f} MWh bataryada 1 tam döngüde "
        f"${degradation_cost * capacity_mwh:,.1f} yıpranma maliyeti oluşur."
    )

# -----------------------------------------------------------------------------
# 5. SİMÜLASYON KAPSAMI
# -----------------------------------------------------------------------------
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1rem 0;'>", unsafe_allow_html=True)
st.sidebar.markdown(
    clean_html(f"""
    <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">
        {make_icon_badge(ICONS['calendar'], color="#38bdf8", bg="rgba(14, 165, 233, 0.12)", border="rgba(14, 165, 233, 0.28)", size=26)}
        <span>Simülasyon Kapsamı</span>
    </div>
    """),
    unsafe_allow_html=True
)

scope_choice = st.sidebar.radio(
    "Veri Aralığı",
    options=["Tüm Veri Seti (Tüm Yıl - 365/366 Gün)", "15 Günlük Prototip (1-15 Ocak)"],
    index=0,
    help="Tüm Veri Seti: Seçilen yılın (2024 veya 2025) tüm günlerinde saatlik sürekli senaryo optimizasyonunu çözer."
)
is_15_days = ("15" in scope_choice)
num_sim_days = 15 if is_15_days else None

# =============================================================================
# MATEMATİKSEL OPTİMİZASYON SİMÜLASYONU
# =============================================================================
sim_strategy = active_strategy

config = BESSConfig05C(
    power_mw=power_mw,
    c_rate=c_rate,
    rte=rte,
    soc_start_pct=float(soc_start_pct),
    soc_end_pct=float(soc_end_pct),
    degradation_cost=float(degradation_cost),
    strategy=sim_strategy,
    ramp_limit_mw=ramp_limit_mw
)

# 1.0 EFC ve 1.5 EFC simülasyonlarını önbellekten al (Seçilen Yıl)
with st.spinner("Matematiksel Senaryo Optimizasyonu Çözülüyor (SciPy HiGHS)..."):
    daily_10, hourly_10, kpis_10 = get_cached_period_simulation(
        selected_year, power_mw, c_rate, rte, soc_start_pct, soc_end_pct, degradation_cost,
        LPStrategy.LP_1_CYCLE, ramp_limit_mw, num_sim_days
    )

    daily_15, hourly_15, kpis_15 = get_cached_period_simulation(
        selected_year, power_mw, c_rate, rte, soc_start_pct, soc_end_pct, degradation_cost,
        LPStrategy.LP_15_CYCLE, ramp_limit_mw, num_sim_days
    )

    # Aktif stratejiye göre ana göstergeleri ata
    if active_strategy == LPStrategy.LP_15_CYCLE:
        daily_df, hourly_df, kpis = daily_15, hourly_15, kpis_15
    else:
        daily_df, hourly_df, kpis = daily_10, hourly_10, kpis_10

    # Kıyaslama tabloları (İş mantığı modülü üzerinden)
    comp_lp_df = build_strategy_comparison_table(kpis_10, kpis_15)

    # Yıllık kıyaslama için 2024 ve 2025
    if selected_year == 2024:
        daily_2024, hourly_2024, kpis_2024 = daily_df, hourly_df, kpis
        daily_2025, hourly_2025, kpis_2025 = get_cached_period_simulation(
            2025, power_mw, c_rate, rte, soc_start_pct, soc_end_pct, degradation_cost,
            sim_strategy, ramp_limit_mw, None
        )
    else:
        daily_2025, hourly_2025, kpis_2025 = daily_df, hourly_df, kpis
        daily_2024, hourly_2024, kpis_2024 = get_cached_period_simulation(
            2024, power_mw, c_rate, rte, soc_start_pct, soc_end_pct, degradation_cost,
            sim_strategy, ramp_limit_mw, None
        )

    comp_df = build_yearly_comparison_table(kpis_2024, kpis_2025)

# =============================================================================
# ANA EKRAN BAŞLIĞI VE SİSTEM ETİKETLERİ
# =============================================================================
strat_meta = LP_STRATEGY_METADATA.get(sim_strategy, {"short_title": "Optimum Senaryo", "badge_color": "#0ea5e9"})
scope_pill = "15 GÜNLÜK PROTOTİP" if is_15_days else f"{selected_year} TÜM YIL"
strat_pill = strat_meta["short_title"]

st.markdown(
    render_header_banner(
        selected_year=selected_year,
        power_mw=power_mw,
        capacity_mwh=capacity_mwh,
        rte=rte,
        soc_start_pct=soc_start_pct,
        soc_end_pct=soc_end_pct,
        strat_pill=strat_pill,
        degradation_cost=degradation_cost,
        scope_pill=scope_pill
    ),
    unsafe_allow_html=True
)

# =============================================================================
# SEKME YAPISI (Apple Segmented Control)
# =============================================================================
tab_period_title = "15 Günlük Senaryo Analizi" if is_15_days else "Aylık ve Yıllık Kırılım"
tab_daily, tab_period, tab_scenarios, tab_yearly = st.tabs([
    "Günlük Güç & Arbitraj Detayı (Seçilen Gün)",
    tab_period_title,
    "1.0 vs 1.5 Döngü Kıyaslama Matrisi",
    "2024 vs 2025 Kıyaslama & Excel Raporu"
])

# -----------------------------------------------------------------------------
# SEKME 1: GÜNLÜK LP GÜÇ & ARBİTRAJ DETAYI
# -----------------------------------------------------------------------------
with tab_daily:
    months_dict = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }

    # Session State Başlatma
    if "cal_date_05" not in st.session_state:
        st.session_state["cal_date_05"] = datetime.date(selected_year, 1, 1)
        st.session_state["c_day_05"] = 1
        st.session_state["c_month_05"] = 1
        st.session_state["c_year_05"] = selected_year
    else:
        # Sınır denetimleri
        if is_15_days:
            if st.session_state.get("c_month_05", 1) != 1 or st.session_state.get("c_day_05", 1) > 15:
                st.session_state["c_month_05"] = 1
                st.session_state["c_day_05"] = min(st.session_state.get("c_day_05", 1), 15)
                st.session_state["cal_date_05"] = datetime.date(selected_year, 1, st.session_state["c_day_05"])

    if st.session_state.get("c_year_05") != selected_year:
        st.session_state["c_year_05"] = selected_year
        m_curr = 1 if is_15_days else st.session_state.get("c_month_05", 1)
        max_d = 15 if (is_15_days and m_curr == 1) else calendar.monthrange(selected_year, m_curr)[1]
        st.session_state["c_day_05"] = min(st.session_state.get("c_day_05", 1), max_d)
        st.session_state["cal_date_05"] = datetime.date(selected_year, m_curr, st.session_state["c_day_05"])

    # Streamlit Callback Fonksiyonları (st.rerun ÇAĞIRILMAZ; Streamlit state değişiminde otomatik rerun yapar)
    def sync_from_calendar_05():
        new_d = st.session_state["cal_date_05"]
        st.session_state["c_day_05"] = new_d.day
        st.session_state["c_month_05"] = new_d.month
        st.session_state["c_year_05"] = new_d.year
        if st.session_state.get("selected_year_05c") != new_d.year:
            st.session_state["selected_year_05c"] = new_d.year

    def sync_from_cards_05():
        y = st.session_state["c_year_05"]
        m = 1 if is_15_days else st.session_state["c_month_05"]
        max_d = 15 if (is_15_days and m == 1) else calendar.monthrange(y, m)[1]
        d = min(st.session_state["c_day_05"], max_d)
        st.session_state["c_day_05"] = d
        st.session_state["cal_date_05"] = datetime.date(y, m, d)
        if st.session_state.get("selected_year_05c") != y:
            st.session_state["selected_year_05c"] = y

    # Tarih Barı (4 Sütunlu Temiz Seçici)
    col_d, col_m, col_y, col_cal = st.columns([1.2, 1.8, 1.2, 2.0])

    cur_y = st.session_state.get("c_year_05", selected_year)
    cur_m = 1 if is_15_days else st.session_state.get("c_month_05", 1)
    max_days = 15 if (is_15_days and cur_m == 1) else calendar.monthrange(cur_y, cur_m)[1]

    with col_d:
        st.markdown('<div class="date-label">GÜN</div>', unsafe_allow_html=True)
        st.number_input(
            "Gün",
            min_value=1,
            max_value=max_days,
            key="c_day_05",
            on_change=sync_from_cards_05,
            label_visibility="collapsed"
        )

    with col_m:
        st.markdown('<div class="date-label">AY</div>', unsafe_allow_html=True)
        st.selectbox(
            "Ay",
            options=[1] if is_15_days else list(months_dict.keys()),
            format_func=lambda x: f"{x:02d} - {months_dict[x]}",
            key="c_month_05",
            on_change=sync_from_cards_05,
            label_visibility="collapsed",
            disabled=is_15_days
        )

    with col_y:
        st.markdown('<div class="date-label">YIL</div>', unsafe_allow_html=True)
        st.selectbox(
            "Yıl",
            options=available_years,
            key="c_year_05",
            on_change=sync_from_cards_05,
            label_visibility="collapsed"
        )

    with col_cal:
        st.markdown('<div class="date-label">TAKVİM</div>', unsafe_allow_html=True)
        active_cal_y = st.session_state["c_year_05"]
        cal_max = datetime.date(active_cal_y, 1, 15) if is_15_days else datetime.date(active_cal_y, 12, 31)
        st.date_input(
            "Takvim",
            min_value=datetime.date(active_cal_y, 1, 1),
            max_value=cal_max,
            key="cal_date_05",
            on_change=sync_from_calendar_05,
            label_visibility="collapsed"
        )

    # Seçilen gün verisi
    selected_date = st.session_state["cal_date_05"]
    day_hourly = hourly_df[hourly_df["date"].dt.date == selected_date].copy()

    if day_hourly.empty:
        st.warning(f"{selected_date.strftime('%d.%m.%Y')} tarihi için simülasyon verisi bulunamadı.")
    else:
        day_daily = daily_df[daily_df["date"].dt.date == selected_date]
        day_net = float(day_daily["net_profit"].values[0]) if not day_daily.empty else 0.0
        day_rev = float(day_daily["discharge_revenue"].values[0]) if not day_daily.empty else 0.0
        day_cost = float(day_daily["charge_cost"].values[0]) if not day_daily.empty else 0.0
        day_deg = float(day_daily["degradation_cost"].values[0]) if not day_daily.empty else 0.0
        day_cycles = float(day_daily["cycles"].values[0]) if not day_daily.empty else 0.0

        max_ptf = float(day_hourly["ptf_usd"].max()) if not day_hourly.empty else 0.0
        min_ptf = float(day_hourly["ptf_usd"].min()) if not day_hourly.empty else 0.0
        max_spread = max_ptf - min_ptf

        # Günün 5 Kibar Ufak KPI Kartı (Şarj Gideri, Deşarj Geliri, Net Kâr, Yıpranma, Maks. Spread)
        st.markdown(
            render_daily_mini_kpi_cards(
                charge_cost=day_cost,
                discharge_revenue=day_rev,
                net_profit=day_net,
                degradation_cost=day_deg,
                max_spread=max_spread,
                min_ptf=min_ptf,
                max_ptf=max_ptf,
                cycles=day_cycles
            ),
            unsafe_allow_html=True
        )

        # 3 Satırlı Senkronize Plotly Grafiği
        fig_dispatch = build_daily_dispatch_chart(
            day_df=day_hourly,
            power_mw=power_mw,
            capacity_mwh=capacity_mwh,
            date_label=selected_date.strftime("%d %B %Y")
        )
        st.plotly_chart(fig_dispatch, use_container_width=True)

        # 24 Saatlik Detay Tablosu
        with st.expander(f"📋 {selected_date.strftime('%d.%m.%Y')} Tarihli 24 Saatlik Optimum Çözüm Tablosunu Görüntüle", expanded=False):
            p_ch_col = "p_charge" if "p_charge" in day_hourly.columns else "p_charge_mw"
            p_dis_col = "p_discharge" if "p_discharge" in day_hourly.columns else "p_discharge_mw"
            p_net_col = "p_net" if "p_net" in day_hourly.columns else "p_net_mw"

            display_day = day_hourly[[
                "hour", "saat_str", "ptf_usd", p_ch_col, p_dis_col, p_net_col, "soc_mwh"
            ]].copy()
            display_day["soc_pct"] = display_day["soc_mwh"] / capacity_mwh * 100.0
            display_day.columns = [
                "Saat No", "Saat Aralığı", "PTF ($/MWh)", "Şarj Gücü (MW)",
                "Deşarj Gücü (MW)", "Net Akış (MW)", "SoC (MWh)", "SoC (%)"
            ]
            def highlight_dispatch_row(row):
                ch_val = row["Şarj Gücü (MW)"]
                dis_val = row["Deşarj Gücü (MW)"]
                if ch_val > 0.05:
                    return ["background-color: rgba(14, 165, 233, 0.16); color: #bae6fd; font-weight: 500;"] * len(row)
                elif dis_val > 0.05:
                    return ["background-color: rgba(78, 222, 163, 0.16); color: #bbf7d0; font-weight: 500;"] * len(row)
                return [""] * len(row)

            styled_day = display_day.style.apply(highlight_dispatch_row, axis=1).format({
                "PTF ($/MWh)": "${:.2f}",
                "Şarj Gücü (MW)": "{:.2f} MW",
                "Deşarj Gücü (MW)": "{:.2f} MW",
                "Net Akış (MW)": "{:+.2f} MW",
                "SoC (MWh)": "{:.2f} MWh",
                "SoC (%)": "%{:.1f}"
            })
            st.dataframe(styled_day, use_container_width=True)

# -----------------------------------------------------------------------------
# SEKME 2: 15 GÜNLÜK PROTOTİP VEYA TÜM YIL ANALİZİ
# -----------------------------------------------------------------------------
with tab_period:
    # Yıl / Dönem Boyutundaki Bento KPI Kartları
    st.markdown(render_kpi_cards(kpis, power_mw, degradation_cost), unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    if is_15_days:
        st.markdown(
            clean_html(f"""
            <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem;">
                15 Günlük Sürekli Senaryo Prototip Performansı (1-15 Ocak {selected_year})
            </div>
            <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 1.25rem;">
                SciPy HiGHS çözücüsü ile 15 günlük ardışık 360 saatlik arbitraj sonuçları ve kümülatif nakit akışı.
            </div>
            """),
            unsafe_allow_html=True
        )

        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Kümülatif Net Kâr Gelişimi ($)</div>", unsafe_allow_html=True)
            fig_cum = build_cumulative_profit_chart(daily_df)
            st.plotly_chart(fig_cum, use_container_width=True)

        with c_g2:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Günlük Eşdeğer Tam Döngü (EFC) Dağılımı</div>", unsafe_allow_html=True)
            fig_bar = build_daily_cycles_bar_chart(daily_df)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; color: #ffffff; margin-top: 1rem; margin-bottom: 0.5rem;'>15 Günlük Gün Bazlı Tablo</div>", unsafe_allow_html=True)
        display_proto = daily_df[[
            "date_str", "day_name", "net_profit", "cum_net_profit",
            "revenue", "cost", "cycles", "fractional_hours", "status"
        ]].copy()
        display_proto.columns = [
            "Tarih", "Gün", "Net Kâr ($)", "Kümülatif Kâr ($)",
            "Deşarj Geliri ($)", "Şarj Maliyeti ($)", "Döngü (EFC)",
            "Kısmi Güç (Saat)", "Durum"
        ]

        def highlight_status(row):
            color = "rgba(78, 222, 163, 0.08)" if row["Durum"] == "AKTİF" else "rgba(148, 163, 184, 0.05)"
            return [f"background-color: {color}"] * len(row)

        st.dataframe(
            display_proto.style.apply(highlight_status, axis=1).format({
                "Net Kâr ($)": "${:,.2f}",
                "Kümülatif Kâr ($)": "${:,.2f}",
                "Deşarj Geliri ($)": "${:,.2f}",
                "Şarj Maliyeti ($)": "${:,.2f}",
                "Döngü (EFC)": "{:.2f}",
                "Kısmi Güç (Saat)": "{:d} saat"
            }),
            use_container_width=True
        )
    else:
        st.markdown(
            clean_html(f"""
            <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem;">
                {selected_year} Yılı Aylık ve Kümülatif Arbitraj Analizi
            </div>
            <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 1.25rem;">
                Tüm yıl boyunca her günün 24 saatlik bağımsız optimum senaryo çözümleri üzerinden hesaplanan aylık nakit akışları.
            </div>
            """),
            unsafe_allow_html=True
        )

        monthly_df = aggregate_monthly_05c(daily_df, hourly_df)

        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Aylık Net Kâr, Gelir ve Maliyet Dağılımı ($)</div>", unsafe_allow_html=True)
            fig_m1 = build_monthly_financial_chart(monthly_df)
            st.plotly_chart(fig_m1, use_container_width=True)

        with c_m2:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Aylık Toplam Eşdeğer Döngü (EFC)</div>", unsafe_allow_html=True)
            fig_m2 = build_monthly_cycles_chart(monthly_df)
            st.plotly_chart(fig_m2, use_container_width=True)

        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; color: #ffffff; margin-top: 1rem; margin-bottom: 0.5rem;'>Aylık Performans Matrisi Tablosu</div>", unsafe_allow_html=True)
        display_m = monthly_df[[
            "month_name", "net_profit", "revenue", "cost",
            "degradation_cost", "cycles", "active_days", "passed_days",
            "realized_spread", "avg_ptf"
        ]].copy()
        display_m.index = range(1, len(display_m) + 1)
        display_m.index.name = "Ay No"
        display_m.columns = [
            "Ay", "Net Kâr ($)", "Deşarj Geliri ($)", "Şarj Maliyeti ($)",
            "Yıpranma ($)", "Toplam EFC", "Aktif Gün", "Pas Gün",
            "Spread ($/MWh)", "Ort. PTF ($/MWh)"
        ]
        st.dataframe(
            display_m.style.format({
                "Net Kâr ($)": "${:,.2f}",
                "Deşarj Geliri ($)": "${:,.2f}",
                "Şarj Maliyeti ($)": "${:,.2f}",
                "Yıpranma ($)": "${:,.2f}",
                "Toplam EFC": "{:.1f}",
                "Aktif Gün": "{:d}",
                "Pas Gün": "{:d}",
                "Spread ($/MWh)": "${:.2f}",
                "Ort. PTF ($/MWh)": "${:.2f}"
            }),
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# SEKME 3: 1.0 vs 1.5 DÖNGÜ KIYASLAMA MATRİSİ
# -----------------------------------------------------------------------------
with tab_scenarios:
    st.markdown(
        clean_html(f"""
        <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem;">
            1.0 Döngü vs 1.5 Döngü Modülasyon Kıyaslama Matrisi
        </div>
        <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 1.25rem;">
            Hücre Ömrü Koruyucu (<b>1.0 EFC</b>) ile Fırsatçı Kısmi Güç Modülasyonu (<b>1.5 EFC</b>) modellerinin <b>{scope_pill}</b> verisi üzerindeki finansal, operasyonel ve yıpranma başa-baş kıyaslaması.
        </div>
        """),
        unsafe_allow_html=True
    )

    row_10 = comp_lp_df.iloc[0]
    row_15 = comp_lp_df.iloc[1]

    delta_15 = row_15["Net Kâr ($)"] - row_10["Net Kâr ($)"]
    pct_15 = (delta_15 / row_10["Net Kâr ($)"] * 100.0) if row_10["Net Kâr ($)"] > 0 else 0.0
    delta_efc = row_15["Toplam Döngü (EFC)"] - row_10["Toplam Döngü (EFC)"]

    card1_html, card2_html, card3_html = render_strategy_comparison_cards(row_10, row_15, delta_15, pct_15, delta_efc)
    sc_c1, sc_c2, sc_c3 = st.columns(3)
    with sc_c1:
        st.markdown(card1_html, unsafe_allow_html=True)
    with sc_c2:
        st.markdown(card2_html, unsafe_allow_html=True)
    with sc_c3:
        st.markdown(card3_html, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    col_fig1, col_fig2 = st.columns(2)
    with col_fig1:
        st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Finansal Bileşenler Kıyaslaması ($)</div>", unsafe_allow_html=True)
        fig_lp_comp = build_strategy_comparison_barchart(comp_lp_df, degradation_cost)
        st.plotly_chart(fig_lp_comp, use_container_width=True)

    with col_fig2:
        st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 0.4rem;'>Kümülatif Net Kâr Farkı (1.5 EFC vs 1.0 EFC)</div>", unsafe_allow_html=True)
        cum_10_y = daily_10["cum_net_profit"] if "cum_net_profit" in daily_10.columns else daily_10["net_profit"].cumsum()
        cum_15_y = daily_15["cum_net_profit"] if "cum_net_profit" in daily_15.columns else daily_15["net_profit"].cumsum()

        fig_cum_comp = go.Figure()
        fig_cum_comp.add_trace(
            go.Scatter(
                x=daily_10["date"],
                y=cum_10_y,
                name="1.0 EFC (Koruyucu)",
                mode="lines",
                line=dict(color="#64748b", width=2.2),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>1.0 EFC: <b>$%{y:,.2f}</b><extra></extra>"
            )
        )
        fig_cum_comp.add_trace(
            go.Scatter(
                x=daily_15["date"],
                y=cum_15_y,
                name="1.5 EFC (Fırsatçı)",
                mode="lines",
                line=dict(color="#4edea3", width=2.8),
                fill="tonexty",
                fillcolor="rgba(78, 222, 163, 0.12)",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>1.5 EFC: <b>$%{y:,.2f}</b><extra></extra>"
            )
        )
        fig_cum_comp.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(24, 28, 36, 0.5)",
            plot_bgcolor="rgba(15, 19, 28, 0.6)",
            font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
            height=360,
            margin=dict(l=15, r=15, t=25, b=15),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
            yaxis=dict(title="Kümülatif Net Kâr ($)", gridcolor="rgba(255, 255, 255, 0.06)", tickprefix="$"),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
        )
        st.plotly_chart(fig_cum_comp, use_container_width=True)

    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; color: #ffffff; margin-top: 1rem; margin-bottom: 0.5rem;'>Senaryo Karşılaştırma Matrisi Tablosu</div>", unsafe_allow_html=True)
    st.dataframe(
        comp_lp_df.style.format({
            "Net Kâr ($)": "${:,.2f}",
            "1.0 Döngüye Göre Fark ($)": "${:+,.2f}",
            "Fark (%)": "{:+.2f}%",
            "Deşarj Geliri ($)": "${:,.2f}",
            "Şarj Maliyeti ($)": "${:,.2f}",
            "Yıpranma ($)": "${:,.2f}",
            "Gerçekleşen Spread ($/MWh)": "${:.2f}",
            "Toplam Döngü (EFC)": "{:.1f}",
            "Döngü Başı Kâr ($/Cycle)": "${:,.2f}",
            "Kısmi Güç Saatleri": "{:d} saat"
        }),
        use_container_width=True
    )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    guide1_html, guide2_html = render_strategy_guide_cards(row_10, row_15, delta_15, pct_15)
    col_strat1, col_strat2 = st.columns(2)
    with col_strat1:
        st.markdown(guide1_html, unsafe_allow_html=True)
    with col_strat2:
        st.markdown(guide2_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SEKME 4: 2024 vs 2025 KARŞILAŞTIRMA & EXCEL RAPORU
# -----------------------------------------------------------------------------
with tab_yearly:
    st.markdown(
        clean_html(f"""
        <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem;">
            2024 vs 2025 Yıllık Karşılaştırma & Excel Fizibilite İndirme
        </div>
        <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 1.25rem;">
            Seçilen konfigürasyon ({power_mw:.0f} MW / {capacity_mwh:.0f} MWh, %{rte*100:.0f} RTE, {strat_pill}) için 2024 (artık yıl) ve 2025 EPİAŞ saatlik PTF fiyatları üzerinde yıllık makro getiri kıyaslaması.
        </div>
        """),
        unsafe_allow_html=True
    )

    row_24 = comp_df[comp_df["Yıl"].str.contains("2024")].iloc[0]
    row_25 = comp_df[comp_df["Yıl"].str.contains("2025")].iloc[0]
    yearly_delta = row_25["Net Kâr ($)"] - row_24["Net Kâr ($)"]
    yearly_pct = (yearly_delta / row_24["Net Kâr ($)"] * 100.0) if row_24["Net Kâr ($)"] > 0 else 0.0

    yc1, yc2, yc3 = st.columns(3)
    with yc1:
        st.markdown(clean_html(f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">2024 Yıllık Net Kâr (Artık Yıl - 366 Gün)</div>
                <div class="card-icon">{ICONS['calendar']}</div>
            </div>
            <div class="card-metric sky">${row_24['Net Kâr ($)']:,.2f}</div>
            <div class="card-foot">
                <span>Döngü Sayısı:</span>
                <span class="val-mono">{row_24['Döngü Sayısı (EFC)']:.1f} EFC</span>
            </div>
            <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
                Ort. Spread: <b style="color: #dfe2ee;">${row_24['Gerçekleşen Spread ($/MWh)']:.2f}/MWh</b> | Aktif: {row_24['Aktif Gün']} gün
            </div>
        </div>
        """), unsafe_allow_html=True)

    with yc2:
        st.markdown(clean_html(f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">2025 Yıllık Net Kâr (365 Gün)</div>
                <div class="card-icon">{ICONS['calendar']}</div>
            </div>
            <div class="card-metric emerald">${row_25['Net Kâr ($)']:,.2f}</div>
            <div class="card-foot">
                <span>Döngü Sayısı:</span>
                <span class="val-mono">{row_25['Döngü Sayısı (EFC)']:.1f} EFC</span>
            </div>
            <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
                Ort. Spread: <b style="color: #dfe2ee;">${row_25['Gerçekleşen Spread ($/MWh)']:.2f}/MWh</b> | Aktif: {row_25['Aktif Gün']} gün
            </div>
        </div>
        """), unsafe_allow_html=True)

    with yc3:
        st.markdown(clean_html(f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">Yıllık Performans Değişimi</div>
                <div class="card-icon" style="color: {'#4edea3' if yearly_delta >= 0 else '#f43f5e'};">{ICONS['trending']}</div>
            </div>
            <div class="card-metric {'emerald' if yearly_delta >= 0 else 'rose'}">{'+' if yearly_delta >= 0 else ''}${yearly_delta:,.2f}</div>
            <div class="card-foot">
                <span>Yüzdesel Değişim:</span>
                <span class="val-mono" style="color: {'#4edea3' if yearly_pct >= 0 else '#f43f5e'};">{'+' if yearly_pct >= 0 else ''}%{yearly_pct:.2f}</span>
            </div>
            <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
                Spread Farkı: <b style="color: #dfe2ee;">{'+' if row_25['Gerçekleşen Spread ($/MWh)'] >= row_24['Gerçekleşen Spread ($/MWh)'] else ''}${row_25['Gerçekleşen Spread ($/MWh)'] - row_24['Gerçekleşen Spread ($/MWh)']:,.2f}/MWh</b>
            </div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # 5 Sayfalı Excel Raporu İndirme Kartı
    st.markdown(clean_html(f"""
    <div class="excel-download-card">
        <div class="excel-title">
            <span style="color: #38bdf8;">{ICONS['download']}</span>
            <span>BESS 0.5C Kapsamlı Finansal Fizibilite Raporu (.xlsx)</span>
        </div>
        <div class="excel-desc">
            Bu Excel dosyası, banka ve yatırımcı standartlarında hazırlanmış olup <b>5 ayrı çalışma sayfası</b> içerir:<br>
            • <b>1. Yönetici Özeti:</b> Tüm teknik girdiler, yıllık gelir/maliyet tablosu ve finansal KPI'lar.<br>
            • <b>2. Aylık Özet:</b> 12 ayın gelir, maliyet, yıpranma, döngü sayısı ve ortalama fiyat dökümü.<br>
            • <b>3. Günlük Özet:</b> Yılın tüm günlerinin net kârı, döngüleri ve operasyonel kararları.<br>
            • <b>4. 8760 Saatlik Veri:</b> Her saatin PTF fiyatı, şarj/deşarj gücü (MW), SoC seviyesi (MWh ve %).<br>
            • <b>5. Strateji Karşılaştırması:</b> 1.0 vs 1.5 Döngü senaryolarının başa-baş finansal matrisi.
        </div>
    </div>
    """), unsafe_allow_html=True)

    with st.spinner("Finansal Excel Raporu Hazırlanıyor..."):
        monthly_for_excel = aggregate_monthly_05c(daily_df, hourly_df)
        excel_data = get_cached_excel_report(
            year=selected_year,
            power_mw=power_mw,
            c_rate=c_rate,
            rte=rte,
            soc_start_pct=float(soc_start_pct),
            soc_end_pct=float(soc_end_pct),
            degradation_cost=float(degradation_cost),
            strategy=sim_strategy,
            ramp_limit_mw=ramp_limit_mw,
            _hourly_df=hourly_df,
            _daily_df=daily_df,
            _kpis=kpis,
            _monthly_df=monthly_for_excel,
            _comp_df=comp_lp_df
        )

        st.download_button(
            label=f"📥 {selected_year} Yılı Kapsamlı Fizibilite Raporunu İndir (.xlsx)",
            data=excel_data,
            file_name=f"Standalone_BESS_Arbitraj_Raporu_{selected_year}_{power_mw:.0f}MW_{capacity_mwh:.0f}MWh_{strat_meta['short_title'].replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; color: #ffffff; margin-top: 1rem; margin-bottom: 0.5rem;'>Yıllık Karşılaştırma Tablosu</div>", unsafe_allow_html=True)
    st.dataframe(
        comp_df.style.format({
            "Deşarj Geliri ($)": "${:,.2f}",
            "Şarj Maliyeti ($)": "${:,.2f}",
            "Brüt Kâr ($)": "${:,.2f}",
            "Yıpranma Maliyeti ($)": "${:,.2f}",
            "Net Kâr ($)": "${:,.2f}",
            "Döngü Sayısı (EFC)": "{:.1f}",
            "Aktif Gün": "{:d}",
            "Pas Geçilen Gün": "{:d}",
            "Döngü Başı Kâr ($)": "${:,.2f}",
            "Ort. Deşarj Fiyatı ($/MWh)": "${:.2f}",
            "Ort. Şarj Fiyatı ($/MWh)": "${:.2f}",
            "Gerçekleşen Spread ($/MWh)": "${:.2f}"
        }),
        use_container_width=True
    )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    fig_comp = build_yearly_comparison_chart(comp_df)
    st.plotly_chart(fig_comp, use_container_width=True)
