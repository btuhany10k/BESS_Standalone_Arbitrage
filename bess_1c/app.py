"""
BESS Day-Ahead Price Spread Arbitrage Optimization (Full-Block 1C & Operator SoC Management)
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

# Add project root directory
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.data_loader import load_all_ptf_data
from src.optimizer import BESSConfig, optimize_year
from src.metrics import compute_kpis, compute_monthly_breakdown
from src.exporter import generate_bess_excel_report

# Page Configuration
st.set_page_config(
    page_title="Standalone BESS Arbitrage Strategy | 1C Storage",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark / Light Compatible Modern & Minimalist CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header */
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
    
    /* KPI Cards - Glassmorphic Dark UI */
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
    
    /* Date Mini Cards */
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
    """Loads raw market price data."""
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
    Executes annual simulation with Full-Block 1C, Operator SoC management,
    Degradation cost, and 1/2 Cycling Strategy.
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


# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ System & Market Parameters")

raw_data = get_cached_raw_data()
available_years = sorted(list(raw_data.keys()))

if not available_years:
    st.error("Market price files (PTF2024.csv, PTF2025.csv) not found. Please verify the data directory.")
    st.stop()

if "selected_year_sidebar" not in st.session_state:
    st.session_state["selected_year_sidebar"] = available_years[-1]

selected_year = st.sidebar.selectbox(
    "📅 Analysis Year",
    available_years,
    key="selected_year_sidebar",
    help="Simulation is performed using real hourly day-ahead market price ($/MWh) data for the selected year."
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🔋 Battery Specifications")

power_mw = st.sidebar.slider(
    "Nominal Power (MW)",
    min_value=0.5,
    max_value=150.0,
    value=50.0,
    step=0.5,
    help="Maximum continuous charge and discharge power capacity of the battery system."
)

c_rate = 1.0  # Fixed 1C
capacity_mwh = power_mw / c_rate

st.sidebar.info(
    f"⚡ **Configuration: 1C (1-Hour Duration)**\n\n"
    f"• Power: **{power_mw:.1f} MW**\n"
    f"• Capacity: **{capacity_mwh:.1f} MWh**"
)

rte_percent = st.sidebar.slider(
    "Round-Trip Efficiency (RTE %)",
    min_value=70,
    max_value=98,
    value=85,
    step=1,
    help="AC-AC Round-Trip Efficiency. E.g., at 85% RTE, 1.0 MWh of charging energy delivers 0.85 MWh net discharged energy."
)
rte = rte_percent / 100.0

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 Operator SoC Management (Start / End of Day)")

soc_start_pct = st.sidebar.slider(
    "Day-Start Initial SoC (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="Minimum reserve or initial battery state of charge retained at the start of the day (00:00)."
)

soc_end_pct = st.sidebar.slider(
    "Day-End Target SoC (%)",
    min_value=0,
    max_value=50,
    value=0,
    step=5,
    help="Target state of charge the operator maintains at the close of the day (23:00)."
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 💸 Cost Parameters")

degradation_cost = st.sidebar.number_input(
    "Battery Degradation Cost ($/MWh)",
    min_value=0.0,
    max_value=200.0,
    value=0.0,
    step=1.0,
    help="Cell amortization and degradation cost per MWh throughput ($/MWh). If arbitrage profit does not exceed degradation cost and round-trip losses (net profit <= 0), the battery remains on standby (idle/skipped)."
)

if degradation_cost > 0:
    st.sidebar.caption(
        f"ℹ️ For a {power_mw:.1f} MW battery, **${degradation_cost * capacity_mwh:,.1f}** degradation cost is incurred per full cycle. Operations are skipped on unprofitable days."
    )

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🛡️ Operational Strategy")

strategy_option = st.sidebar.radio(
    "Arbitrage Strategy",
    options=["1 Cycle per Day (Single Block)", "Up to 2 Cycles per Day (Dual Block)"],
    index=0,
    help="Strategy for executing 1 primary cycle or an additional 2nd cycle in profitable non-overlapping windows."
)
strategy = "2_cycle" if "2" in strategy_option else "1_cycle"

if strategy == "2_cycle":
    st.sidebar.info(
        "⚡ **Up to 2 Cycles per Day (Dual Block) Strategy:**\n\n"
        "• **1st Cycle:** Primary charge and discharge executed during the widest daily price spread.\n"
        "• **2nd Cycle:** Most profitable secondary hour-pair outside 1st cycle hours (before or after).\n"
        "• **Economic Filter:** 2nd cycle is only dispatched if incremental net profit > $0; otherwise stays at 1 cycle.\n"
        "• **Chronological Index:** Dispatches are sequentially labelled as Charge 1 / Discharge 1 and Charge 2 / Discharge 2."
    )
else:
    st.sidebar.success(
        "⚡ **1C Single Block Arbitrage:**\n\n"
        "• Single full charge during deepest daily price trough.\n"
        "• Single full discharge during peak evening price window.\n"
        "• If net profit is non-positive, system stands by ($0 profit, 0 cycles)."
    )

# Execute Simulation (Selected Year)
hourly_df, daily_df, kpis, monthly_df = calculate_optimization(
    selected_year, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy
)

# 2024 and 2025 Multi-year Comparison (for Excel report and Comparison Tab)
_, _, kpis_2024, monthly_2024 = calculate_optimization(2024, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy)
_, _, kpis_2025, monthly_2025 = calculate_optimization(2025, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), strategy)

comp_df = pd.DataFrame([
    {
        "Year": "2024",
        "Discharge Revenue ($)": kpis_2024["total_revenue"],
        "Charge Cost ($)": kpis_2024["total_cost"],
        "Gross Profit ($)": kpis_2024["gross_profit"],
        "Degradation Cost ($)": kpis_2024["total_degradation_cost"],
        "Net Profit ($)": kpis_2024["net_profit"],
        "Total Cycles (EFC)": kpis_2024["total_cycles"],
        "Active Days": kpis_2024["active_days"],
        "Standby Days": kpis_2024["passed_days"],
        "Net Profit per Cycle ($/Cycle)": kpis_2024["profit_per_cycle"],
        "Avg. Discharge Price ($/MWh)": kpis_2024["avg_discharge_price"],
        "Avg. Charge Price ($/MWh)": kpis_2024["avg_charge_price"],
        "Realized Spread ($/MWh)": kpis_2024["realized_spread"],
    },
    {
        "Year": "2025",
        "Discharge Revenue ($)": kpis_2025["total_revenue"],
        "Charge Cost ($)": kpis_2025["total_cost"],
        "Gross Profit ($)": kpis_2025["gross_profit"],
        "Degradation Cost ($)": kpis_2025["total_degradation_cost"],
        "Net Profit ($)": kpis_2025["net_profit"],
        "Total Cycles (EFC)": kpis_2025["total_cycles"],
        "Active Days": kpis_2025["active_days"],
        "Standby Days": kpis_2025["passed_days"],
        "Net Profit per Cycle ($/Cycle)": kpis_2025["profit_per_cycle"],
        "Avg. Discharge Price ($/MWh)": kpis_2025["avg_discharge_price"],
        "Avg. Charge Price ($/MWh)": kpis_2025["avg_charge_price"],
        "Realized Spread ($/MWh)": kpis_2025["realized_spread"],
    }
])

# --- MAIN SCREEN ---
strat_display_name = "Up to 2 Cycles per Day (Dual Block)" if strategy == "2_cycle" else "1 Cycle per Day (Single Block)"
st.markdown('<div class="main-title">🔋 Standalone BESS Arbitrage Strategy</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">Day-Ahead Market Real Hourly Prices ($/MWh) — {selected_year} | {strat_display_name} | Initial SoC: %{soc_start_pct} ➔ Target SoC: %{soc_end_pct} | Degradation: ${degradation_cost:.1f}/MWh</div>',
    unsafe_allow_html=True
)

# --- KPI METRIC CARDS ---
cards = [
    f"""<div class="kpi-card">
<div class="kpi-label">💰 Net Arbitrage Profit</div>
<div class="kpi-value kpi-profit">${kpis['net_profit']:,.0f}</div>
<div class="kpi-sub">Gross: ${kpis['gross_profit']:,.0f} | Daily Avg: ${kpis['avg_daily_profit']:,.1f}</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🟢 Discharge Revenue</div>
<div class="kpi-value">${kpis['total_revenue']:,.0f}</div>
<div class="kpi-sub">Avg: ${kpis['avg_discharge_price']:.1f} / MWh</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🔴 Charge Cost</div>
<div class="kpi-value kpi-cost">${kpis['total_cost']:,.0f}</div>
<div class="kpi-sub">Avg: ${kpis['avg_charge_price']:.1f} / MWh</div>
</div>"""
]

if degradation_cost > 0:
    cards.append(f"""<div class="kpi-card">
<div class="kpi-label">🛠️ Degradation Cost</div>
<div class="kpi-value kpi-cost">${kpis['total_degradation_cost']:,.0f}</div>
<div class="kpi-sub">${degradation_cost:.1f} / MWh unit</div>
</div>""")

cards.extend([
    f"""<div class="kpi-card">
<div class="kpi-label">🔋 Total Cycles (EFC)</div>
<div class="kpi-value kpi-cycle">{kpis['total_cycles']:,.0f}</div>
<div class="kpi-sub">{kpis['active_days']} active / {kpis['passed_days']} standby days</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">💎 Net Profit per Cycle</div>
<div class="kpi-value kpi-profit">${kpis['profit_per_cycle']:,.2f}</div>
<div class="kpi-sub">Net profit / Total EFC</div>
</div>""",
    f"""<div class="kpi-card">
<div class="kpi-label">🎯 Realized Price Spread</div>
<div class="kpi-value">${kpis['realized_spread']:,.1f} <span style="font-size: 0.95rem; font-weight: 500; color: #94a3b8;">/ MWh</span></div>
<div class="kpi-sub">Avg. Discharge Sale - Avg. Charge Purchase</div>
</div>"""
])

kpi_html = f'<div class="kpi-container">{"".join(cards)}</div>'
st.markdown(kpi_html, unsafe_allow_html=True)

# --- TAB LAYOUT ---
tab_daily, tab_monthly, tab_comparison = st.tabs([
    "📈 Daily Arbitrage Dispatch (Selected Day)",
    "📊 Monthly & Annual Breakdown",
    "⚖️ 2024 vs 2025 Comparison",
])

# =========================================================================
# TAB 1: DAILY ARBITRAGE DISPATCH
# =========================================================================
with tab_daily:
    st.markdown("#### 📅 Date Selection & 24-Hour Dispatch Profile")
    st.caption("Optimal charging at lowest price, discharging at peak price, and hourly battery state of charge (SoC) trajectory.")

    # Date Selection Panel
    months_dict = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    if "card_day" not in st.session_state:
        st.session_state["card_day"] = 1
    if "card_month" not in st.session_state:
        st.session_state["card_month"] = 1
    if "card_year" not in st.session_state:
        st.session_state["card_year"] = selected_year
    if "cal_date_val" not in st.session_state:
        st.session_state["cal_date_val"] = datetime.date(selected_year, 1, 1)

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

    col_d, col_m, col_y, col_cal, col_d2, col_d3 = st.columns([1.0, 1.45, 1.0, 1.45, 1.2, 1.2])

    with col_d:
        st.markdown('<div class="date-mini-label">📌 DAY</div>', unsafe_allow_html=True)
        cur_y = st.session_state.get("card_year", selected_year)
        cur_m = st.session_state.get("card_month", 1)
        max_days = calendar.monthrange(cur_y, cur_m)[1]
        if st.session_state.get("card_day", 1) > max_days:
            st.session_state["card_day"] = max_days
        elif st.session_state.get("card_day", 1) < 1:
            st.session_state["card_day"] = 1
        st.number_input(
            "Day",
            min_value=1,
            max_value=max_days,
            key="card_day",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_m:
        st.markdown('<div class="date-mini-label">📆 MONTH</div>', unsafe_allow_html=True)
        st.selectbox(
            "Month",
            options=list(months_dict.keys()),
            format_func=lambda x: f"{x:02d} - {months_dict[x]}",
            key="card_month",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_y:
        st.markdown('<div class="date-mini-label">🗓️ YEAR</div>', unsafe_allow_html=True)
        st.selectbox(
            "Year",
            options=available_years,
            key="card_year",
            on_change=sync_from_cards,
            label_visibility="collapsed"
        )

    with col_cal:
        st.markdown('<div class="date-mini-label">📅 CALENDAR</div>', unsafe_allow_html=True)
        active_cal_y = st.session_state["card_year"]
        if st.session_state.get("cal_date_val") and st.session_state["cal_date_val"].year != active_cal_y:
            m = st.session_state.get("card_month", 1)
            max_d = calendar.monthrange(active_cal_y, m)[1]
            d = min(st.session_state.get("card_day", 1), max_d)
            st.session_state["cal_date_val"] = datetime.date(active_cal_y, m, d)
        st.date_input(
            "Calendar",
            min_value=datetime.date(active_cal_y, 1, 1),
            max_value=datetime.date(active_cal_y, 12, 31),
            key="cal_date_val",
            on_change=sync_from_calendar,
            label_visibility="collapsed"
        )

    selected_date_dt = st.session_state["cal_date_val"]
    selected_date = pd.to_datetime(selected_date_dt)

    day_matches = daily_df[daily_df["date"] == selected_date]
    if day_matches.empty:
        selected_date = daily_df["date"].iloc[0]
        day_summary = daily_df.iloc[0]
    else:
        day_summary = day_matches.iloc[0]

    day_hourly = hourly_df[hourly_df["date"] == selected_date].copy().sort_values("hour").reset_index(drop=True)

    with col_d2:
        if day_summary.get("is_passed", False):
            st.metric("Daily Net Profit", "$0.00", "🛡️ Standby", delta_color="off")
        else:
            sub_txt = f"Gross: ${day_summary['gross_profit']:.1f}" if degradation_cost > 0 else f"Spread: ${day_summary['ptf_spread']:.1f}"
            st.metric("Daily Net Profit", f"${day_summary['net_profit']:.2f}", sub_txt)
    with col_d3:
        if day_summary.get("is_passed", False):
            st.metric("Daily Cycles", "0.00 EFC", f"Spread: ${day_summary['ptf_spread']:.1f}")
        else:
            deg_sub = f"Degradation: -${day_summary['degradation_cost']:.1f}" if degradation_cost > 0 else f"Spread: ${day_summary['ptf_spread']:.1f}"
            st.metric("Daily Cycles", f"{day_summary['cycles']:.2f} EFC", deg_sub)

    if day_summary.get("is_passed", False):
        st.warning(
            f"🛡️ **Standby Mode Active (No Dispatch):** "
            f"Daily price spread (${day_summary['ptf_spread']:.1f}/MWh) is insufficient to clear charging efficiency losses and degradation cost (${degradation_cost:.1f}/MWh). "
            "The battery remained idle, preserving capital and cell longevity with $0.00 PnL."
        )

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Hourly Day-Ahead Price ($/MWh) & Dispatch Points", "Battery State of Charge (SoC %)"),
        row_heights=[0.68, 0.32]
    )

    fig.add_trace(
        go.Scatter(
            x=day_hourly["hour"],
            y=day_hourly["ptf_usd"],
            mode="lines",
            name="Day-Ahead Price ($/MWh)",
            line=dict(color="#cbd5e1", width=2.8, shape="spline", smoothing=0.5),
            hovertemplate="Hour %{x:02d}:00<br>Price: <b>$%{y:.2f}/MWh</b><extra></extra>",
        ),
        row=1, col=1
    )

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

        if pd.notna(ch1_val) and ch1_val is not None:
            ch1_int = int(ch1_val)
            ch1_row = day_hourly[day_hourly["hour"] == ch1_int].iloc[0]
            ch1_name = "🔋 1st Charge Hour" if has_two_cycles else "🔋 Charge Hour"
            ch1_txt = f"Charge 1: {ch1_row['p_ch_mw']:.1f}MW" if has_two_cycles else f"Charge: {ch1_row['p_ch_mw']:.1f}MW"
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
                    hovertemplate=f"<b>{'1st ' if has_two_cycles else ''}CHARGE HOUR</b><br>Hour: {ch1_int:02d}:00<br>Price: ${ch1_row['ptf_usd']:.2f}/MWh<br>Charge: {ch1_row['p_ch_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        if pd.notna(dis1_val) and dis1_val is not None:
            dis1_int = int(dis1_val)
            dis1_row = day_hourly[day_hourly["hour"] == dis1_int].iloc[0]
            dis1_name = "⚡ 1st Discharge Hour" if has_two_cycles else "⚡ Discharge Hour"
            dis1_txt = f"Discharge 1: {dis1_row['p_dis_mw']:.1f}MW" if has_two_cycles else f"Discharge: {dis1_row['p_dis_mw']:.1f}MW"
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
                    hovertemplate=f"<b>{'1st ' if has_two_cycles else ''}DISCHARGE HOUR</b><br>Hour: {dis1_int:02d}:00<br>Price: ${dis1_row['ptf_usd']:.2f}/MWh<br>Discharge: {dis1_row['p_dis_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        if has_two_cycles:
            ch2_int = int(ch2_val)
            ch2_row = day_hourly[day_hourly["hour"] == ch2_int].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[ch2_int],
                    y=[ch2_row["ptf_usd"]],
                    mode="markers+text",
                    name="🔋 2nd Charge Hour",
                    marker=dict(
                        color="#60a5fa",
                        size=16,
                        symbol="diamond",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[f"Charge 2: {ch2_row['p_ch_mw']:.1f}MW"],
                    textposition="bottom center",
                    textfont=dict(size=12, color="#60a5fa", family="Inter"),
                    hovertemplate=f"<b>2nd CHARGE HOUR</b><br>Hour: {ch2_int:02d}:00<br>Price: ${ch2_row['ptf_usd']:.2f}/MWh<br>Charge: {ch2_row['p_ch_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

        if pd.notna(dis2_val) and dis2_val is not None:
            dis2_int = int(dis2_val)
            dis2_row = day_hourly[day_hourly["hour"] == dis2_int].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[dis2_int],
                    y=[dis2_row["ptf_usd"]],
                    mode="markers+text",
                    name="⚡ 2nd Discharge Hour",
                    marker=dict(
                        color="#34d399",
                        size=16,
                        symbol="diamond",
                        line=dict(color="#ffffff", width=2.5)
                    ),
                    text=[f"Discharge 2: {dis2_row['p_dis_mw']:.1f}MW"],
                    textposition="top center",
                    textfont=dict(size=12, color="#34d399", family="Inter"),
                    hovertemplate=f"<b>2nd DISCHARGE HOUR</b><br>Hour: {dis2_int:02d}:00<br>Price: ${dis2_row['ptf_usd']:.2f}/MWh<br>Discharge: {dis2_row['p_dis_mw']:.1f}MW<extra></extra>",
                ),
                row=1, col=1
            )

    fig.add_trace(
        go.Scatter(
            x=day_hourly["hour"],
            y=day_hourly["soc_pct"],
            mode="lines",
            name="State of Charge (%)",
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.18)",
            line=dict(color="#38bdf8", width=2.2, shape="hv"),
            hovertemplate="Hour %{x:02d}:00<br>SoC: <b>%{y:.1f}%</b><extra></extra>",
        ),
        row=2, col=1
    )

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
            title="Hour of Day (00:00 - 23:00)",
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
            title="Day-Ahead Price ($/MWh)",
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

    # Detailed Hourly Breakdown Accordion
    with st.expander("📋 View 24-Hour Detailed Dispatch Table for This Day"):
        st.markdown(
            '<div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.6rem;">'
            '🔵 <b style="color: #38bdf8;">Blue Rows:</b> Charging Windows (Charge 1 / Charge 2) &nbsp;|&nbsp; '
            '🟢 <b style="color: #34d399;">Green Rows:</b> Discharging Windows (Discharge 1 / Discharge 2)'
            '</div>',
            unsafe_allow_html=True
        )
        display_day = day_hourly[[
            "saat_str", "ptf_usd", "p_ch_mw", "p_dis_mw", "soc_mwh", "soc_pct", "charge_cost", "discharge_revenue", "degradation_cost", "net_profit", "action_label"
        ]].copy()
        display_day.columns = [
            "Hour", "Price ($/MWh)", "Charge (MW)", "Discharge (MW)", "SoC (MWh)", "SoC (%)", "Charge Cost ($)", "Discharge Revenue ($)", "Degradation Cost ($)", "Net Profit ($)", "Operation Status"
        ]

        def highlight_charge_discharge(row):
            if row["Charge (MW)"] > 0.001:
                return ["background-color: rgba(56, 189, 248, 0.28); color: #38bdf8; font-weight: 600;"] * len(row)
            elif row["Discharge (MW)"] > 0.001:
                return ["background-color: rgba(16, 185, 129, 0.28); color: #34d399; font-weight: 600;"] * len(row)
            return [""] * len(row)

        styled_display = display_day.style.apply(highlight_charge_discharge, axis=1).format({
            "Price ($/MWh)": "${:.2f}",
            "Charge (MW)": "{:.2f}",
            "Discharge (MW)": "{:.2f}",
            "SoC (MWh)": "{:.2f}",
            "SoC (%)": "{:.1f}%",
            "Charge Cost ($)": "${:.2f}",
            "Discharge Revenue ($)": "${:.2f}",
            "Degradation Cost ($)": "${:.2f}",
            "Net Profit ($)": "${:.2f}",
        })

        st.dataframe(styled_display, width="stretch")

# =========================================================================
# TAB 2: MONTHLY & ANNUAL BREAKDOWN
# =========================================================================
with tab_monthly:
    st.markdown("#### 📊 Monthly & Annual Breakdown & 365-Day Excel Report")
    st.caption("Monthly net arbitrage profit, equivalent full cycles completed, profit generated per cycle, and 365-day Excel export tool.")

    # 365-Day Comprehensive Excel Report Card
    excel_card_html = (
        '<div style="background: rgba(30, 41, 59, 0.65); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1.2rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);">'
        '<div style="font-size: 1.12rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.5rem;">'
        '📥 <span>Comprehensive 365-Day Simulation & Feasibility Report (.xlsx)</span>'
        '</div>'
        '<div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.55;">'
        f'Generated 5-sheet comprehensive workbook for selected year <b>{selected_year}</b> based on <b>{power_mw:.1f} MW</b> power, <b>%{rte*100:.0f}</b> RTE, <b>${degradation_cost:.1f}/MWh</b> degradation, <b>%{soc_start_pct}</b> ➔ <b>%{soc_end_pct}</b> SoC, and <b>{strat_display_name}</b>:<br>'
        '• ⏱️ <b>Hourly Dispatch (8,760h):</b> Full 365-day hourly breakdown (Date, Hour, Price, Charge/Discharge MW, SoC %, Cost, Revenue, Degradation, Net Profit, Operation Status)<br>'
        '• 📅 <b>Daily Summary (365 Days):</b> Day-by-day 1st & 2nd dispatch hours, energy throughput, cycling, and active/standby status<br>'
        '• 📑 <b>Monthly Breakdown:</b> Full financial and operational metrics across all 12 months<br>'
        '• 📊 <b>Summary & Parameters:</b> System configuration and annual feasibility KPIs<br>'
        '• ⚖️ <b>2024 vs 2025 Comparison:</b> Multi-year performance benchmark table'
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
            label="📥 Download 365-Day Comprehensive Excel Report (.xlsx)",
            data=excel_bytes,
            file_name=f"BESS_Arbitrage_{selected_year}_{power_mw:.0f}MW_365Days_Detail.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )
    with col_btn2:
        st.caption("📁 **Contents:** 5 Worksheets | 8,760 Hourly Table + 365 Daily Summary + Monthly Breakdown + KPIs + 2024/2025 Comparison")

    st.markdown("---")

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        # 1. Monthly Net Profit & Cycles Chart
        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])

        fig_monthly.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["net_profit"],
                name="Net Profit ($)",
                marker=dict(color="#10b981", opacity=0.88, line=dict(color="#059669", width=1)),
                hovertemplate="%{x}<br>Net Profit: <b>$%{y:,.2f}</b><extra></extra>"
            ),
            secondary_y=False
        )

        if degradation_cost > 0:
            fig_monthly.add_trace(
                go.Bar(
                    x=monthly_df["month_name"],
                    y=monthly_df["degradation_cost"],
                    name="Degradation ($)",
                    marker=dict(color="#f87171", opacity=0.75, line=dict(color="#dc2626", width=1)),
                    hovertemplate="%{x}<br>Degradation: <b>$%{y:,.2f}</b><extra></extra>"
                ),
                secondary_y=False
            )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["month_name"],
                y=monthly_df["cycles"],
                name="Cycles (EFC)",
                mode="lines+markers",
                marker=dict(color="#38bdf8", size=6),
                line=dict(color="#38bdf8", width=2),
                hovertemplate="%{x}<br>Cycles: <b>%{y:.1f}</b><extra></extra>"
            ),
            secondary_y=True
        )

        fig_monthly.update_layout(
            title=dict(text="Monthly Net Profit ($) and Cycles", font=dict(size=12.5, color="#f8fafc")),
            height=315,
            margin=dict(l=35, r=35, t=45, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9.5, color="#e2e8f0")),
            xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9)),
            yaxis=dict(title="USD ($)", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9), title_font=dict(color="#cbd5e1", size=10)),
            yaxis2=dict(title="Cycles (EFC)", overlaying="y", side="right", showgrid=False, tickfont=dict(color="#38bdf8", size=9), title_font=dict(color="#38bdf8", size=10))
        )
        st.plotly_chart(fig_monthly, width="stretch")

    with col_m2:
        # 2. Monthly Net Profit per Cycle ($/Cycle)
        fig_per_cycle = go.Figure()
        fig_per_cycle.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["profit_per_cycle"],
                marker=dict(color="#38bdf8", opacity=0.88, line=dict(color="#0284c7", width=1)),
                hovertemplate="%{x}<br>Profit / Cycle: <b>$%{y:.2f}</b><extra></extra>"
            )
        )
        fig_per_cycle.update_layout(
            title=dict(text="Monthly Net Profit per Cycle ($/Cycle)", font=dict(size=12.5, color="#f8fafc")),
            height=315,
            margin=dict(l=35, r=25, t=45, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9)),
            yaxis=dict(title="$/Cycle", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9), title_font=dict(color="#cbd5e1", size=10)),
        )
        st.plotly_chart(fig_per_cycle, width="stretch")

    with col_m3:
        # 3. Monthly Average Market Price and Daily Price Spread Chart
        fig_spread_ptf = make_subplots(specs=[[{"secondary_y": True}]])

        fig_spread_ptf.add_trace(
            go.Bar(
                x=monthly_df["month_name"],
                y=monthly_df["avg_spread"],
                name="Avg. Spread",
                marker=dict(
                    color="#f59e0b",
                    opacity=0.85,
                    line=dict(color="#d97706", width=1.0)
                ),
                hovertemplate="%{x}<br>Avg. Spread: <b>$%{y:.2f} / MWh</b><extra></extra>"
            ),
            secondary_y=False
        )

        fig_spread_ptf.add_trace(
            go.Scatter(
                x=monthly_df["month_name"],
                y=monthly_df["avg_ptf"],
                name="Avg. Price",
                mode="lines+markers",
                marker=dict(
                    color="#38bdf8",
                    size=6,
                    symbol="circle",
                    line=dict(color="#ffffff", width=1.2)
                ),
                line=dict(color="#38bdf8", width=2),
                hovertemplate="%{x}<br>Avg. Price: <b>$%{y:.2f} / MWh</b><extra></extra>"
            ),
            secondary_y=True
        )

        fig_spread_ptf.update_layout(
            title=dict(
                text="Average Market Price & Daily Spread ($/MWh)",
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
                title="Avg. Price ($/MWh)",
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

    # 4. Monthly Benefit of Additional Cycle (Line Chart)
    st.markdown("##### 📈 Monthly Benefit of Additional Cycle (2nd Cycle vs 1 Cycle)")
    st.caption("Incremental net profit ($) gained each month by executing up to 2 cycles per day compared to a single daily cycle.")

    _, _, _, m_1c = calculate_optimization(selected_year, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), "1_cycle")
    _, _, _, m_2c = calculate_optimization(selected_year, power_mw, c_rate, rte, float(soc_start_pct), float(soc_end_pct), float(degradation_cost), "2_cycle")

    if m_1c is not None and m_2c is not None:
        diff_benefit = m_2c["net_profit"].values - m_1c["net_profit"].values
        fig_benefit = go.Figure()
        fig_benefit.add_trace(
            go.Scatter(
                x=monthly_df["month_name"],
                y=diff_benefit,
                mode="lines+markers+text",
                name="Incremental Profit ($)",
                line=dict(color="#10b981", width=3, shape="spline", smoothing=0.3),
                marker=dict(size=8, color="#10b981", symbol="circle", line=dict(color="#0a0e16", width=2)),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.12)",
                text=[f"+${v:,.0f}" if v > 0 else f"${v:,.0f}" for v in diff_benefit],
                textposition="top center",
                textfont=dict(color="#10b981", size=10, family="monospace"),
                hovertemplate="<b>%{x}</b><br>Incremental Benefit: <b>$%{y:,.2f}</b><extra></extra>"
            )
        )
        fig_benefit.update_layout(
            template="plotly_dark",
            height=280,
            margin=dict(l=35, r=35, t=25, b=25),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8", size=9.5)),
            yaxis=dict(
                title="Incremental Profit ($)",
                tickprefix="$",
                gridcolor="rgba(148, 163, 184, 0.12)",
                tickfont=dict(color="#94a3b8", size=9),
                title_font=dict(color="#cbd5e1", size=10),
                zeroline=True,
                zerolinecolor="rgba(255, 255, 255, 0.2)"
            )
        )
        st.plotly_chart(fig_benefit, width="stretch")

    # Monthly Summary Table
    st.markdown("##### 📋 Monthly Summary Performance Table")
    display_monthly = monthly_df[[
        "month", "month_name", "discharge_revenue", "charge_cost", "gross_profit", "degradation_cost",
        "net_profit", "cycles", "active_days", "passed_days", "profit_per_cycle", "avg_spread", "avg_ptf"
    ]].copy()
    display_monthly.columns = [
        "Month No", "Month", "Discharge Revenue ($)", "Charge Cost ($)", "Gross Profit ($)", "Degradation Cost ($)",
        "Net Arbitrage Profit ($)", "Total Cycles (EFC)", "Active Days", "Standby Days", "Net Profit per Cycle ($/Cycle)",
        "Avg. Daily Spread ($/MWh)", "Avg. Market Price ($/MWh)"
    ]

    st.dataframe(
        display_monthly.style.format({
            "Month No": "{:.0f}",
            "Discharge Revenue ($)": "${:,.2f}",
            "Charge Cost ($)": "${:,.2f}",
            "Gross Profit ($)": "${:,.2f}",
            "Degradation Cost ($)": "${:,.2f}",
            "Net Arbitrage Profit ($)": "${:,.2f}",
            "Total Cycles (EFC)": "{:.1f}",
            "Active Days": "{:.0f}",
            "Standby Days": "{:.0f}",
            "Net Profit per Cycle ($/Cycle)": "${:.2f}",
            "Avg. Daily Spread ($/MWh)": "${:.2f}",
            "Avg. Market Price ($/MWh)": "${:.2f}",
        }),
        width="stretch",
        hide_index=True
    )

# =========================================================================
# TAB 3: 2024 vs 2025 COMPARISON
# =========================================================================
with tab_comparison:
    st.markdown("#### ⚖️ 2024 vs 2025 Annual BESS Performance Comparison (1C Arbitrage)")
    st.caption("Impact of day-ahead price spread dynamics on arbitrage profitability across identical battery configurations.")

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        diff_profit = kpis_2025['net_profit'] - kpis_2024['net_profit']
        pct_diff = (diff_profit / kpis_2024['net_profit'] * 100) if kpis_2024['net_profit'] > 0 else 0.0
        st.metric(
            "2025 Net Profit",
            f"${kpis_2025['net_profit']:,.2f}",
            delta=f"${diff_profit:+,.2f} (%{pct_diff:+.1f})"
        )
    with col_c2:
        diff_cycles = kpis_2025['total_cycles'] - kpis_2024['total_cycles']
        st.metric(
            "2025 Total Cycles",
            f"{kpis_2025['total_cycles']:.0f}",
            delta=f"{diff_cycles:+.0f} Cycles"
        )
    with col_c3:
        diff_per_cy = kpis_2025['profit_per_cycle'] - kpis_2024['profit_per_cycle']
        st.metric(
            "2025 Net Profit per Cycle",
            f"${kpis_2025['profit_per_cycle']:.2f}",
            delta=f"${diff_per_cy:+.2f} / Cycle"
        )

    st.markdown("##### 📋 Annual Comparison Metrics Table")
    st.dataframe(
        comp_df.style.format({
            "Discharge Revenue ($)": "${:,.2f}",
            "Charge Cost ($)": "${:,.2f}",
            "Gross Profit ($)": "${:,.2f}",
            "Degradation Cost ($)": "${:,.2f}",
            "Net Profit ($)": "${:,.2f}",
            "Total Cycles (EFC)": "{:.0f}",
            "Active Days": "{:.0f}",
            "Standby Days": "{:.0f}",
            "Net Profit per Cycle ($/Cycle)": "${:.2f}",
            "Avg. Discharge Price ($/MWh)": "${:.2f}",
            "Avg. Charge Price ($/MWh)": "${:.2f}",
            "Realized Spread ($/MWh)": "${:.2f}",
        }),
        width="stretch",
        hide_index=True
    )

    # 2024 vs 2025 Monthly Net Profit Comparison Chart
    fig_comp_m = go.Figure()
    fig_comp_m.add_trace(
        go.Bar(
            x=monthly_2024["month_name"],
            y=monthly_2024["net_profit"],
            name="2024 Net Profit ($)",
            marker_color="#64748b"
        )
    )
    fig_comp_m.add_trace(
        go.Bar(
            x=monthly_2025["month_name"],
            y=monthly_2025["net_profit"],
            name="2025 Net Profit ($)",
            marker_color="#10b981"
        )
    )
    fig_comp_m.update_layout(
        title=dict(text="2024 vs 2025 Monthly Net Profit Comparison ($)", font=dict(color="#f8fafc")),
        barmode="group",
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1, font=dict(color="#e2e8f0")),
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8")),
        yaxis=dict(title="Net Profit ($)", gridcolor="rgba(148, 163, 184, 0.12)", tickfont=dict(color="#94a3b8"), title_font=dict(color="#cbd5e1")),
    )
    st.plotly_chart(fig_comp_m, width="stretch")
