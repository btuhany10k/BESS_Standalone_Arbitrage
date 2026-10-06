"""
BESS 0.5C (2 Saatlik Depolama) Mock Simülasyon Motoru (Scaffolding Engine)
NOT: Kullanıcı direktifi doğrultusunda bu aşamada matematiksel optimizasyon ve dinamik modelleme yapılmamıştır.
Panel tasarımı, bileşenler ve grafikler için 0.5C (2 saat bloklu şarj/deşarj) yapısına uygun gerçekçi sentetik veri üretir.
Matematiksel optimizasyon modeli sonraki iterasyonlarda kullanıcıyla birlikte geliştirilecektir.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import calendar
import numpy as np
import pandas as pd


@dataclass
class BESSConfig05C:
    """0.5C (2 Saatlik Depolama) BESS Parametreleri."""
    power_mw: float = 50.0
    c_rate: float = 0.5  # Sabit 0.5C (2 saat)
    rte: float = 0.85     # %85
    soc_start_pct: float = 0.0
    soc_end_pct: float = 0.0
    degradation_cost: float = 0.0  # $/MWh
    strategy: str = "1_cycle"      # "1_cycle" veya "2_cycle"

    @property
    def duration_hours(self) -> float:
        return 1.0 / self.c_rate  # 2.0 saat

    @property
    def capacity_mwh(self) -> float:
        return self.power_mw * self.duration_hours  # 50 MW * 2h = 100 MWh


def generate_mock_05c_simulation(
    year_df: pd.DataFrame,
    config: BESSConfig05C
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, pd.DataFrame]:
    """
    0.5C (2 saat blok) için görselleştirme ve panel prototipi amaçlı mock veri üretir.
    2 saatlik şarj penceresi ve 2 saatlik deşarj penceresi simüle eder.
    """
    power = config.power_mw
    cap = config.capacity_mwh
    rte = config.rte
    deg_unit = config.degradation_cost
    is_two_cycle = (config.strategy == "2_cycle")

    # Benzersiz günleri al
    unique_dates = year_df["date"].drop_duplicates().sort_values().reset_index(drop=True)

    daily_rows = []
    hourly_rows = []

    # Mock çarpanlar (0.5C için 2 saat deşarj kapasitesi = 2 * power MWh)
    daily_energy_discharged = power * 2.0 * rte  # MWh
    daily_energy_charged = power * 2.0           # MWh

    for d in unique_dates:
        day_p = year_df[year_df["date"] == d].sort_values("hour").reset_index(drop=True)
        if len(day_p) < 24:
            continue

        prices = day_p["ptf_usd"].values

        # 0.5C: 2 ardışık saatlik şarj ve 2 ardışık saatlik deşarj pencereleri (Mock belirleme)
        # Gece dip saatleri (01:00-06:00 arası 2 saat)
        night_hours = [1, 2, 3, 4]
        ch1_h1 = int(np.argmin(prices[1:5]) + 1)
        ch1_h2 = min(ch1_h1 + 1, 23)

        # Akşam pik saatleri (17:00-21:00 arası 2 saat)
        peak_hours = [17, 18, 19, 20]
        dis1_h1 = int(np.argmax(prices[17:21]) + 17)
        dis1_h2 = min(dis1_h1 + 1, 23)

        ch1_hours = [ch1_h1, ch1_h2]
        dis1_hours = [dis1_h1, dis1_h2]

        ch2_hours = []
        dis2_hours = []

        if is_two_cycle:
            # 2. döngü: Öğle güneş fazlası (12:00-13:00) şarj, gece geç pik (21:00-22:00) deşarj
            ch2_hours = [12, 13]
            dis2_hours = [21, 22]

        # Fiyat ortalamaları
        avg_ch_price = np.mean([prices[h] for h in ch1_hours])
        avg_dis_price = np.mean([prices[h] for h in dis1_hours])
        spread = avg_dis_price - avg_ch_price

        # Yıpranma ve net kâr hesaplaması (Mock)
        cycle_count = 2.0 if is_two_cycle else 1.0
        tot_deg_cost = cycle_count * cap * deg_unit
        
        # 1 döngülük gelir ve maliyet
        revenue_1 = daily_energy_discharged * avg_dis_price
        cost_1 = daily_energy_charged * avg_ch_price
        gross_1 = revenue_1 - cost_1

        if is_two_cycle:
            revenue = gross_1 * 1.85 + (cost_1 * 1.85)
            cost = cost_1 * 1.85
            gross = gross_1 * 1.85
        else:
            revenue = revenue_1
            cost = cost_1
            gross = gross_1

        net = gross - tot_deg_cost

        # Pas geçme simülasyonu: Spread çok düşükse pas geç
        is_passed = (spread < (deg_unit * 1.2 + 8.0)) and (deg_unit > 0)
        if is_passed:
            net = 0.0
            gross = 0.0
            revenue = 0.0
            cost = 0.0
            tot_deg_cost = 0.0
            cycle_count = 0.0

        daily_rows.append({
            "date": d,
            "ptf_spread": spread,
            "gross_profit": gross,
            "net_profit": net,
            "discharge_revenue": revenue,
            "charge_cost": cost,
            "degradation_cost": tot_deg_cost,
            "cycles": cycle_count,
            "is_passed": is_passed,
            "ch1_h1": ch1_h1,
            "ch1_h2": ch1_h2,
            "dis1_h1": dis1_h1,
            "dis1_h2": dis1_h2,
            "ch2_h1": ch2_hours[0] if ch2_hours else None,
            "ch2_h2": ch2_hours[1] if ch2_hours else None,
            "dis2_h1": dis2_hours[0] if dis2_hours else None,
            "dis2_h2": dis2_hours[1] if dis2_hours else None,
        })

        # Saatlik profil oluştur (0.5C 2 saatlik dolma/boşalma profili)
        current_soc = config.soc_start_pct / 100.0 * cap
        for h in range(24):
            p_val = prices[h]
            p_ch = 0.0
            p_dis = 0.0
            act_label = "Beklemede (Idle)"

            if not is_passed:
                if h in ch1_hours:
                    p_ch = power
                    act_label = f"1. Şarj (Blok {ch1_hours.index(h)+1}/2)"
                    current_soc = min(cap, current_soc + power * (1.0 - (config.soc_start_pct/100.0))/2.0)
                elif h in dis1_hours:
                    p_dis = power
                    act_label = f"1. Deşarj (Blok {dis1_hours.index(h)+1}/2)"
                    current_soc = max(cap * (config.soc_end_pct/100.0), current_soc - (cap / 2.0))
                elif is_two_cycle and h in ch2_hours:
                    p_ch = power
                    act_label = f"2. Şarj (Blok {ch2_hours.index(h)+1}/2)"
                    current_soc = min(cap, current_soc + (cap / 2.0))
                elif is_two_cycle and h in dis2_hours:
                    p_dis = power
                    act_label = f"2. Deşarj (Blok {dis2_hours.index(h)+1}/2)"
                    current_soc = max(cap * (config.soc_end_pct/100.0), current_soc - (cap / 2.0))

            h_cost = p_ch * p_val
            h_rev = p_dis * p_val * rte
            h_deg = (p_ch + p_dis) / 2.0 * deg_unit if (p_ch + p_dis) > 0 else 0.0
            h_net = h_rev - h_cost - h_deg

            hourly_rows.append({
                "date": d,
                "hour": h,
                "saat_str": f"{h:02d}:00",
                "ptf_usd": p_val,
                "p_ch_mw": p_ch,
                "p_dis_mw": p_dis,
                "soc_mwh": current_soc,
                "soc_pct": (current_soc / cap * 100.0) if cap > 0 else 0.0,
                "charge_cost": h_cost,
                "discharge_revenue": h_rev,
                "degradation_cost": h_deg,
                "net_profit": h_net,
                "action_label": act_label
            })

    daily_df = pd.DataFrame(daily_rows)
    hourly_df = pd.DataFrame(hourly_rows)

    # Yıllık KPI Metrikleri
    tot_revenue = float(daily_df["discharge_revenue"].sum())
    tot_cost = float(daily_df["charge_cost"].sum())
    gross_profit = float(daily_df["gross_profit"].sum())
    tot_deg = float(daily_df["degradation_cost"].sum())
    net_profit = float(daily_df["net_profit"].sum())
    tot_cycles = float(daily_df["cycles"].sum())
    active_days = int((daily_df["cycles"] > 0).sum())
    passed_days = int((daily_df["cycles"] == 0).sum())

    charged_hours = hourly_df[hourly_df["p_ch_mw"] > 0]
    discharged_hours = hourly_df[hourly_df["p_dis_mw"] > 0]

    avg_ch_p = float(charged_hours["ptf_usd"].mean()) if len(charged_hours) > 0 else 0.0
    avg_dis_p = float(discharged_hours["ptf_usd"].mean()) if len(discharged_hours) > 0 else 0.0
    realized_spread = avg_dis_p - avg_ch_p
    profit_per_cycle = (net_profit / tot_cycles) if tot_cycles > 0 else 0.0
    avg_daily_profit = (net_profit / len(daily_df)) if len(daily_df) > 0 else 0.0

    kpis = {
        "total_revenue": tot_revenue,
        "total_cost": tot_cost,
        "gross_profit": gross_profit,
        "total_degradation_cost": tot_deg,
        "net_profit": net_profit,
        "total_cycles": tot_cycles,
        "active_days": active_days,
        "passed_days": passed_days,
        "profit_per_cycle": profit_per_cycle,
        "avg_discharge_price": avg_dis_p,
        "avg_charge_price": avg_ch_p,
        "realized_spread": realized_spread,
        "avg_daily_profit": avg_daily_profit,
        "power_mw": power,
        "capacity_mwh": cap,
        "c_rate": config.c_rate,
        "rte": rte,
    }

    # Aylık Kırılım
    daily_df["month"] = pd.to_datetime(daily_df["date"]).dt.month
    monthly_records = []
    month_names = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }

    for m in range(1, 13):
        m_daily = daily_df[daily_df["month"] == m]
        if m_daily.empty:
            continue
        m_hourly = hourly_df[pd.to_datetime(hourly_df["date"]).dt.month == m]

        m_rev = float(m_daily["discharge_revenue"].sum())
        m_cost = float(m_daily["charge_cost"].sum())
        m_gross = float(m_daily["gross_profit"].sum())
        m_deg = float(m_daily["degradation_cost"].sum())
        m_net = float(m_daily["net_profit"].sum())
        m_cycles = float(m_daily["cycles"].sum())
        m_active = int((m_daily["cycles"] > 0).sum())
        m_passed = int((m_daily["cycles"] == 0).sum())
        m_ppc = (m_net / m_cycles) if m_cycles > 0 else 0.0
        m_spread = float(m_daily["ptf_spread"].mean()) if len(m_daily) > 0 else 0.0
        m_ptf = float(m_hourly["ptf_usd"].mean()) if len(m_hourly) > 0 else 0.0

        monthly_records.append({
            "month": m,
            "month_name": month_names.get(m, f"{m}. Ay"),
            "discharge_revenue": m_rev,
            "charge_cost": m_cost,
            "gross_profit": m_gross,
            "degradation_cost": m_deg,
            "net_profit": m_net,
            "cycles": m_cycles,
            "active_days": m_active,
            "passed_days": m_passed,
            "profit_per_cycle": m_ppc,
            "avg_spread": m_spread,
            "avg_ptf": m_ptf,
        })

    monthly_df = pd.DataFrame(monthly_records)
    return hourly_df, daily_df, kpis, monthly_df
