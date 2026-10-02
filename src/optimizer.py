"""
BESS 1C Arbitraj Optimizasyon Motoru
Günün en kârlı şarj ve deşarj saatlerini tespit eder.
İşletmecinin belirlediği gün başlangıç ve gün sonu SoC (%) seviyelerine göre
arbitraj simülasyonunu gerçekleştirir.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class BESSConfig:
    """BESS Sistem ve İşletme Parametreleri"""
    power_mw: float = 1.0           # Nominal Güç (MW)
    c_rate: float = 1.0             # C-Rate (1C -> 1 Saat şarj / 1 Saat deşarj)
    rte: float = 0.85               # Round-Trip Efficiency (Verimlilik, örn: 0.85 = %85)
    soc_start_pct: float = 0.0      # Gün Başlangıcı SoC Seviyesi (%)
    soc_end_pct: float = 0.0        # Gün Sonu Hedef SoC Seviyesi (%)
    degradation_cost: float = 0.0   # Yıpranma Maliyeti ($/MWh deşarj veya $/Cycle kapasite)

    @property
    def capacity_mwh(self) -> float:
        """Kapasite = Güç / C-Rate (MWh)"""
        return self.power_mw / self.c_rate

    @property
    def duration_hours(self) -> float:
        """Deşarj süresi (saat) = 1 / C-Rate"""
        return 1.0 / self.c_rate


def optimize_single_day(
    prices: np.ndarray,
    config: BESSConfig
) -> Dict[str, np.ndarray | float | bool | int | None]:
    """
    1C ve İşletmeci SoC Başlangıç/Bitiş Kurallı Arbitraj Optimizasyonu.
    
    Mantık:
      - Güne soc_start_pct seviyesinde başlanır (soc_start = soc_start_pct/100 * E_max).
      - Batarya en dip saatte tam kapasiteye (%100) şarj edilir:
          Şarj Miktarı (MWh) = delta_ch = E_max - soc_start
      - Batarya en pik saatte gün sonu hedef seviyesine (soc_end_pct) kadar deşarj edilir:
          Depodan Çekilen = delta_dis_storage = E_max - soc_end
          Şebekeye Verilen = delta_dis_grid = delta_dis_storage * RTE
      - Brüt Kâr = (delta_dis_grid * PTF[dis]) - (delta_ch * PTF[ch])
      - Yıpranma Maliyeti = config.degradation_cost * delta_dis_storage
      - Net Kâr = Brüt Kâr - Yıpranma Maliyeti
      - Bu Net Kârı maksimize eden tekil (ch, dis) çifti (ch < dis) seçilir.
      - Net Kâr <= 0 ise batarya gün boyu bekletilir (Pas Geçilir: 0 MW, 0 Cycle, $0 Maliyet, $0 Kâr).
    """
    T = len(prices)
    P_max = config.power_mw
    E_max = config.capacity_mwh
    rte = config.rte

    soc_start = (config.soc_start_pct / 100.0) * E_max
    soc_end = (config.soc_end_pct / 100.0) * E_max

    delta_ch = max(0.0, E_max - soc_start)
    delta_dis_storage = max(0.0, E_max - soc_end)
    delta_dis_grid = delta_dis_storage * rte

    # Döngü gerçekleşirse oluşacak yıpranma maliyeti
    potential_deg_cost = float(config.degradation_cost * delta_dis_storage)

    best_net_profit = 0.0
    best_gross_profit = 0.0
    candidate_pairs = []

    for ch in range(T):
        for dis in range(ch + 1, T):
            cost = delta_ch * prices[ch]
            rev = delta_dis_grid * prices[dis]
            gross = rev - cost
            net = gross - potential_deg_cost
            if net > best_net_profit:
                best_net_profit = net
                best_gross_profit = gross
                candidate_pairs = [(ch, dis)]
            elif abs(net - best_net_profit) < 1e-5 and net > 0:
                candidate_pairs.append((ch, dis))

    best_ch = None
    best_dis = None

    if candidate_pairs and best_net_profit > 0:
        # Eşitlik durumunda akşam pikine (19:00 civarı) en yakın olanı seç
        candidate_pairs.sort(key=lambda pair: (abs(pair[1] - 19), -pair[0]))
        best_ch, best_dis = candidate_pairs[0]

    p_ch = np.zeros(T)
    p_dis = np.zeros(T)
    soc = np.full(T, soc_start)

    if best_net_profit > 0 and best_ch is not None and best_dis is not None:
        p_ch[best_ch] = delta_ch
        p_dis[best_dis] = delta_dis_grid
        
        # SoC profili: Şarj saatine kadar soc_start, şarjdan deşarja kadar %100 (E_max),
        # deşarj sonrası soc_end
        soc[best_ch:best_dis] = E_max
        soc[best_dis:] = soc_end

        charge_cost = float(delta_ch * prices[best_ch])
        discharge_revenue = float(delta_dis_grid * prices[best_dis])
        gross_profit = float(discharge_revenue - charge_cost)
        degradation_cost = float(potential_deg_cost)
        net_profit = float(gross_profit - degradation_cost)
        cycles = float(delta_dis_storage / E_max) if E_max > 0 else 0.0
        discharged_mwh = float(delta_dis_grid)
        charged_mwh = float(delta_ch)
        is_passed = False
        success = True
    else:
        # Net kâr <= 0 ise batarya pas geçer (hiçbir işlem yapmaz, yıpranma oluşmaz)
        charge_cost = 0.0
        discharge_revenue = 0.0
        gross_profit = 0.0
        degradation_cost = 0.0
        net_profit = 0.0
        cycles = 0.0
        discharged_mwh = 0.0
        charged_mwh = 0.0
        is_passed = True
        success = True

    return {
        "success": success,
        "is_passed": is_passed,
        "best_ch": best_ch,
        "best_dis": best_dis,
        "p_ch": p_ch,
        "p_dis": p_dis,
        "soc": soc,
        "charge_cost": charge_cost,
        "discharge_revenue": discharge_revenue,
        "gross_profit": gross_profit,
        "degradation_cost": degradation_cost,
        "net_profit": net_profit,
        "cycles": cycles,
        "discharged_mwh": discharged_mwh,
        "charged_mwh": charged_mwh,
    }


def optimize_year(df: pd.DataFrame, config: BESSConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tüm bir yılın saatlik verilerini gün gün optimize eder.
    """
    hourly_records = []
    daily_records = []

    for d, group in df.groupby("date", sort=True):
        if len(group) != 24:
            continue

        prices = group["ptf_usd"].values
        hours = group["hour"].values
        datetimes = group["datetime"].values
        month = group["month"].iloc[0]
        day = group["day"].iloc[0]

        res = optimize_single_day(prices, config)

        p_ch = res["p_ch"]
        p_dis = res["p_dis"]
        soc = res["soc"]
        cost_arr = np.zeros(24)
        rev_arr = np.zeros(24)
        deg_arr = np.zeros(24)

        if res["best_ch"] is not None:
            cost_arr[res["best_ch"]] = res["charge_cost"]
        if res["best_dis"] is not None:
            rev_arr[res["best_dis"]] = res["discharge_revenue"]
            deg_arr[res["best_dis"]] = res["degradation_cost"]

        prof_arr = rev_arr - cost_arr - deg_arr

        for i in range(24):
            hourly_records.append({
                "datetime": datetimes[i],
                "date": d,
                "month": month,
                "day": day,
                "hour": hours[i],
                "saat_str": f"{hours[i]:02d}:00",
                "ptf_usd": prices[i],
                "p_ch_mw": p_ch[i],
                "p_dis_mw": p_dis[i],
                "soc_mwh": soc[i],
                "soc_pct": (soc[i] / config.capacity_mwh) * 100.0 if config.capacity_mwh > 0 else 0.0,
                "charge_cost": cost_arr[i],
                "discharge_revenue": rev_arr[i],
                "degradation_cost": deg_arr[i],
                "gross_profit": rev_arr[i] - cost_arr[i],
                "net_profit": prof_arr[i],
                "is_charging": (i == res["best_ch"]) if res["best_ch"] is not None else False,
                "is_discharging": (i == res["best_dis"]) if res["best_dis"] is not None else False,
                "is_passed": res["is_passed"],
            })

        daily_records.append({
            "date": d,
            "month": month,
            "ptf_min": float(np.min(prices)),
            "ptf_max": float(np.max(prices)),
            "ptf_avg": float(np.mean(prices)),
            "ptf_spread": float(np.max(prices) - np.min(prices)),
            "charge_cost": res["charge_cost"],
            "discharge_revenue": res["discharge_revenue"],
            "gross_profit": res["gross_profit"],
            "degradation_cost": res["degradation_cost"],
            "net_profit": res["net_profit"],
            "cycles": res["cycles"],
            "charged_mwh": res["charged_mwh"],
            "discharged_mwh": res["discharged_mwh"],
            "profit_per_cycle": (res["net_profit"] / res["cycles"]) if res["cycles"] > 0 else 0.0,
            "best_ch": res["best_ch"],
            "best_dis": res["best_dis"],
            "is_passed": res["is_passed"],
        })

    hourly_df = pd.DataFrame(hourly_records)
    daily_df = pd.DataFrame(daily_records)

    return hourly_df, daily_df
