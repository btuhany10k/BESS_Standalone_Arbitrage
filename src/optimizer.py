"""
BESS 1C Arbitraj Optimizasyon Motoru
Günün en kârlı şarj ve deşarj saatlerini tespit eder.
İşletmecinin belirlediği gün başlangıç ve gün sonu SoC (%) seviyelerine göre
arbitraj simülasyonunu gerçekleştirir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union, Any
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
    strategy: str = "1_cycle"       # "1_cycle" (Tek Blok) veya "2_cycle" (Çift Blok)

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
) -> Dict[str, Any]:
    """
    1C ve İşletmeci SoC Başlangıç/Bitiş Kurallı Arbitraj Optimizasyonu.
    
    1 Döngü (Tek Blok) Mantığı:
      - Güne soc_start_pct seviyesinde başlanır (soc_start = soc_start_pct/100 * E_max).
      - Günün en yüksek net spread'ine sahip (ch1, dis1) çifti bulunur (ch1 < dis1).
      - Net Kâr <= 0 ise batarya gün boyu bekletilir (Pas Geçilir: 0 MW, 0 Cycle, $0 Maliyet, $0 Kâr).
    
    2 Döngü (Çift Blok) Mantığı:
      - 1. döngü (en yüksek kârlı birincil döngü) korunur.
      - 1. döngü saatlerinin kesinlikle dışındaki serbest pencerelerde 2. döngü aranır:
          * Pencere A (Önce): 0 <= ch2 < dis2 < ch1
          * Pencere B (Sonra): dis1 < ch2 < dis2 <= 23
      - 2. döngü sadece Net Kârı > 0 ise devreye alınır; kârsızsa 1 döngüde kalınır.
      - Gün içi olaylar kronolojik sıraya göre 'Şarj 1', 'Deşarj 1', 'Şarj 2', 'Deşarj 2' olarak etiketlenir.
    """
    T = len(prices)
    E_max = config.capacity_mwh
    rte = config.rte
    strategy = getattr(config, "strategy", "1_cycle")

    soc_start = (config.soc_start_pct / 100.0) * E_max
    soc_end = (config.soc_end_pct / 100.0) * E_max

    # --- 1. AŞAMA: BİRİNCİL (EN KÂRLI) DÖNGÜYÜ BUL ---
    delta_ch_1 = max(0.0, E_max - soc_start)
    delta_dis_storage_1 = max(0.0, E_max - soc_end)
    delta_dis_grid_1 = delta_dis_storage_1 * rte
    potential_deg_cost_1 = float(config.degradation_cost * delta_dis_storage_1)

    best_net_1 = 0.0
    best_gross_1 = 0.0
    candidate_pairs_1 = []

    for ch in range(T):
        for dis in range(ch + 1, T):
            cost = delta_ch_1 * prices[ch]
            rev = delta_dis_grid_1 * prices[dis]
            gross = rev - cost
            net = gross - potential_deg_cost_1
            if net > best_net_1:
                best_net_1 = net
                best_gross_1 = gross
                candidate_pairs_1 = [(ch, dis)]
            elif abs(net - best_net_1) < 1e-5 and net > 0:
                candidate_pairs_1.append((ch, dis))

    best_ch_1 = None
    best_dis_1 = None

    if candidate_pairs_1 and best_net_1 > 0:
        # Eşitlik durumunda akşam pikine (19:00 civarı) en yakın olanı seç
        candidate_pairs_1.sort(key=lambda pair: (abs(pair[1] - 19), -pair[0]))
        best_ch_1, best_dis_1 = candidate_pairs_1[0]

    # Eğer 1. döngü kârsızsa tüm gün pas geçilir
    if best_ch_1 is None or best_dis_1 is None or best_net_1 <= 0:
        return {
            "success": True,
            "is_passed": True,
            "cycles_count": 0,
            "best_ch": None,
            "best_dis": None,
            "ch1_hour": None,
            "dis1_hour": None,
            "ch2_hour": None,
            "dis2_hour": None,
            "p_ch": np.zeros(T),
            "p_dis": np.zeros(T),
            "soc": np.full(T, soc_start),
            "charge_cost": 0.0,
            "discharge_revenue": 0.0,
            "gross_profit": 0.0,
            "degradation_cost": 0.0,
            "net_profit": 0.0,
            "cycles": 0.0,
            "discharged_mwh": 0.0,
            "charged_mwh": 0.0,
            "cycle_events": [],
        }

    # 1. döngü metrikleri
    c1_cost = float(delta_ch_1 * prices[best_ch_1])
    c1_rev = float(delta_dis_grid_1 * prices[best_dis_1])
    c1_gross = float(c1_rev - c1_cost)
    c1_deg = float(potential_deg_cost_1)
    c1_net = float(c1_gross - c1_deg)

    # --- 2. AŞAMA: İKİNCİL DÖNGÜ ARAMA (Eğer 2_cycle stratejisi seçildiyse) ---
    has_cycle_2 = False
    chosen_c2 = None

    if strategy == "2_cycle":
        candidate_pairs_2 = []
        best_net_2 = 0.0

        # Pencere A: 1. döngüden önce (0 <= ch2 < dis2 < best_ch_1)
        if best_ch_1 >= 2:
            d_ch_a = max(0.0, E_max - soc_start)
            d_dis_stor_a = max(0.0, E_max - soc_start)
            d_dis_grid_a = d_dis_stor_a * rte
            deg_a = float(config.degradation_cost * d_dis_stor_a)
            for ch in range(0, best_ch_1 - 1):
                for dis in range(ch + 1, best_ch_1):
                    cost = d_ch_a * prices[ch]
                    rev = d_dis_grid_a * prices[dis]
                    gross = rev - cost
                    net = gross - deg_a
                    if net > best_net_2:
                        best_net_2 = net
                        candidate_pairs_2 = [{
                            "ch": ch, "dis": dis, "window": "before",
                            "gross": gross, "net": net, "deg": deg_a,
                            "ch_cost": cost, "dis_rev": rev,
                            "ch_mwh": d_ch_a, "dis_grid_mwh": d_dis_grid_a, "dis_storage_mwh": d_dis_stor_a
                        }]
                    elif abs(net - best_net_2) < 1e-5 and net > 0:
                        candidate_pairs_2.append({
                            "ch": ch, "dis": dis, "window": "before",
                            "gross": gross, "net": net, "deg": deg_a,
                            "ch_cost": cost, "dis_rev": rev,
                            "ch_mwh": d_ch_a, "dis_grid_mwh": d_dis_grid_a, "dis_storage_mwh": d_dis_stor_a
                        })

        # Pencere B: 1. döngüden sonra (best_dis_1 < ch2 < dis2 <= 23)
        if best_dis_1 <= 21:
            d_ch_b = max(0.0, E_max - soc_end)
            d_dis_stor_b = max(0.0, E_max - soc_end)
            d_dis_grid_b = d_dis_stor_b * rte
            deg_b = float(config.degradation_cost * d_dis_stor_b)
            for ch in range(best_dis_1 + 1, 23):
                for dis in range(ch + 1, 24):
                    cost = d_ch_b * prices[ch]
                    rev = d_dis_grid_b * prices[dis]
                    gross = rev - cost
                    net = gross - deg_b
                    if net > best_net_2:
                        best_net_2 = net
                        candidate_pairs_2 = [{
                            "ch": ch, "dis": dis, "window": "after",
                            "gross": gross, "net": net, "deg": deg_b,
                            "ch_cost": cost, "dis_rev": rev,
                            "ch_mwh": d_ch_b, "dis_grid_mwh": d_dis_grid_b, "dis_storage_mwh": d_dis_stor_b
                        }]
                    elif abs(net - best_net_2) < 1e-5 and net > 0:
                        candidate_pairs_2.append({
                            "ch": ch, "dis": dis, "window": "after",
                            "gross": gross, "net": net, "deg": deg_b,
                            "ch_cost": cost, "dis_rev": rev,
                            "ch_mwh": d_ch_b, "dis_grid_mwh": d_dis_grid_b, "dis_storage_mwh": d_dis_stor_b
                        })

        if candidate_pairs_2 and best_net_2 > 0:
            candidate_pairs_2.sort(key=lambda c: (abs(c["dis"] - 19), c["ch"]))
            chosen_c2 = candidate_pairs_2[0]
            has_cycle_2 = True

    # --- 3. AŞAMA: KRONOLOJİK DÜZENLEME VE GÜÇ/SOC PROFİLİ ---
    p_ch = np.zeros(T)
    p_dis = np.zeros(T)
    soc = np.full(T, soc_start)

    cycle_events = []

    if has_cycle_2 and chosen_c2 is not None:
        cycles_count = 2
        if chosen_c2["window"] == "before":
            # 1. Kronolojik Döngü: chosen_c2 (önceki pencere)
            # 2. Kronolojik Döngü: (best_ch_1, best_dis_1)
            ch1_hour = chosen_c2["ch"]
            dis1_hour = chosen_c2["dis"]
            ch2_hour = best_ch_1
            dis2_hour = best_dis_1

            # Güç profilleri
            p_ch[ch1_hour] = chosen_c2["ch_mwh"]
            p_dis[dis1_hour] = chosen_c2["dis_grid_mwh"]
            p_ch[ch2_hour] = delta_ch_1
            p_dis[dis2_hour] = delta_dis_grid_1

            # SoC profili
            soc[ch1_hour:dis1_hour] = E_max
            soc[dis1_hour:ch2_hour] = soc_start
            soc[ch2_hour:dis2_hour] = E_max
            soc[dis2_hour:] = soc_end

            total_charge_cost = chosen_c2["ch_cost"] + c1_cost
            total_discharge_rev = chosen_c2["dis_rev"] + c1_rev
            total_gross = chosen_c2["gross"] + c1_gross
            total_deg = chosen_c2["deg"] + c1_deg
            total_net = chosen_c2["net"] + c1_net
            total_dis_stor = chosen_c2["dis_storage_mwh"] + delta_dis_storage_1
            total_dis_grid = chosen_c2["dis_grid_mwh"] + delta_dis_grid_1
            total_ch_mwh = chosen_c2["ch_mwh"] + delta_ch_1

            cycle_events = [
                {"cycle": 1, "type": "charge", "hour": ch1_hour, "mw": chosen_c2["ch_mwh"], "cost": chosen_c2["ch_cost"]},
                {"cycle": 1, "type": "discharge", "hour": dis1_hour, "mw": chosen_c2["dis_grid_mwh"], "rev": chosen_c2["dis_rev"], "deg": chosen_c2["deg"]},
                {"cycle": 2, "type": "charge", "hour": ch2_hour, "mw": delta_ch_1, "cost": c1_cost},
                {"cycle": 2, "type": "discharge", "hour": dis2_hour, "mw": delta_dis_grid_1, "rev": c1_rev, "deg": c1_deg},
            ]
        else:
            # 1. Kronolojik Döngü: (best_ch_1, best_dis_1)
            # 2. Kronolojik Döngü: chosen_c2 (sonraki pencere)
            ch1_hour = best_ch_1
            dis1_hour = best_dis_1
            ch2_hour = chosen_c2["ch"]
            dis2_hour = chosen_c2["dis"]

            p_ch[ch1_hour] = delta_ch_1
            p_dis[dis1_hour] = delta_dis_grid_1
            p_ch[ch2_hour] = chosen_c2["ch_mwh"]
            p_dis[dis2_hour] = chosen_c2["dis_grid_mwh"]

            # SoC profili
            soc[ch1_hour:dis1_hour] = E_max
            soc[dis1_hour:ch2_hour] = soc_end
            soc[ch2_hour:dis2_hour] = E_max
            soc[dis2_hour:] = soc_end

            total_charge_cost = c1_cost + chosen_c2["ch_cost"]
            total_discharge_rev = c1_rev + chosen_c2["dis_rev"]
            total_gross = c1_gross + chosen_c2["gross"]
            total_deg = c1_deg + chosen_c2["deg"]
            total_net = c1_net + chosen_c2["net"]
            total_dis_stor = delta_dis_storage_1 + chosen_c2["dis_storage_mwh"]
            total_dis_grid = delta_dis_grid_1 + chosen_c2["dis_grid_mwh"]
            total_ch_mwh = delta_ch_1 + chosen_c2["ch_mwh"]

            cycle_events = [
                {"cycle": 1, "type": "charge", "hour": ch1_hour, "mw": delta_ch_1, "cost": c1_cost},
                {"cycle": 1, "type": "discharge", "hour": dis1_hour, "mw": delta_dis_grid_1, "rev": c1_rev, "deg": c1_deg},
                {"cycle": 2, "type": "charge", "hour": ch2_hour, "mw": chosen_c2["ch_mwh"], "cost": chosen_c2["ch_cost"]},
                {"cycle": 2, "type": "discharge", "hour": dis2_hour, "mw": chosen_c2["dis_grid_mwh"], "rev": chosen_c2["dis_rev"], "deg": chosen_c2["deg"]},
            ]
    else:
        # Sadece 1 döngü aktif
        cycles_count = 1
        ch1_hour = best_ch_1
        dis1_hour = best_dis_1
        ch2_hour = None
        dis2_hour = None

        p_ch[ch1_hour] = delta_ch_1
        p_dis[dis1_hour] = delta_dis_grid_1

        soc[ch1_hour:dis1_hour] = E_max
        soc[dis1_hour:] = soc_end

        total_charge_cost = c1_cost
        total_discharge_rev = c1_rev
        total_gross = c1_gross
        total_deg = c1_deg
        total_net = c1_net
        total_dis_stor = delta_dis_storage_1
        total_dis_grid = delta_dis_grid_1
        total_ch_mwh = delta_ch_1

        cycle_events = [
            {"cycle": 1, "type": "charge", "hour": ch1_hour, "mw": delta_ch_1, "cost": c1_cost},
            {"cycle": 1, "type": "discharge", "hour": dis1_hour, "mw": delta_dis_grid_1, "rev": c1_rev, "deg": c1_deg},
        ]

    cycles = float(total_dis_stor / E_max) if E_max > 0 else 0.0

    return {
        "success": True,
        "is_passed": False,
        "cycles_count": cycles_count,
        "best_ch": ch1_hour,
        "best_dis": dis1_hour,
        "ch1_hour": ch1_hour,
        "dis1_hour": dis1_hour,
        "ch2_hour": ch2_hour,
        "dis2_hour": dis2_hour,
        "p_ch": p_ch,
        "p_dis": p_dis,
        "soc": soc,
        "charge_cost": float(total_charge_cost),
        "discharge_revenue": float(total_discharge_rev),
        "gross_profit": float(total_gross),
        "degradation_cost": float(total_deg),
        "net_profit": float(total_net),
        "cycles": cycles,
        "discharged_mwh": float(total_dis_grid),
        "charged_mwh": float(total_ch_mwh),
        "cycle_events": cycle_events,
    }


def optimize_year(df: pd.DataFrame, config: BESSConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tüm bir yılın saatlik verilerini gün gün optimize eder.
    1 Döngü veya 2 Döngü stratejisine göre saatlik ve günlük tabloları üretir.
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
        action_labels = ["Bekleme (Standby)"] * 24 if not res["is_passed"] else ["Pas Geçildi"] * 24
        cycle_nums = [None] * 24

        ch1_h = res["ch1_hour"]
        dis1_h = res["dis1_hour"]
        ch2_h = res["ch2_hour"]
        dis2_h = res["dis2_hour"]

        for ev in res.get("cycle_events", []):
            h = ev["hour"]
            c_num = ev["cycle"]
            cycle_nums[h] = c_num
            if ev["type"] == "charge":
                cost_arr[h] = ev["cost"]
                action_labels[h] = f"Şarj {c_num}"
            elif ev["type"] == "discharge":
                rev_arr[h] = ev["rev"]
                deg_arr[h] = ev["deg"]
                action_labels[h] = f"Deşarj {c_num}"

        prof_arr = rev_arr - cost_arr - deg_arr

        for i in range(24):
            is_charging = (i == ch1_h or (ch2_h is not None and i == ch2_h))
            is_discharging = (i == dis1_h or (dis2_h is not None and i == dis2_h))

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
                "is_charging": is_charging,
                "is_discharging": is_discharging,
                "is_passed": res["is_passed"],
                "action_label": action_labels[i],
                "cycle_num": cycle_nums[i],
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
            "cycles_count": res.get("cycles_count", 0),
            "best_ch": res["best_ch"],
            "best_dis": res["best_dis"],
            "ch1_hour": ch1_h,
            "dis1_hour": dis1_h,
            "ch2_hour": ch2_h,
            "dis2_hour": dis2_h,
            "is_passed": res["is_passed"],
        })

    hourly_df = pd.DataFrame(hourly_records)
    daily_df = pd.DataFrame(daily_records)

    return hourly_df, daily_df

