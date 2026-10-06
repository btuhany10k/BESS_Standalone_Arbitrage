"""
BESS 0.5C (2 Saatlik Depolama) Sürekli Doğrusal Programlama (LP) & Kısmi Güç Modülasyonu Motoru
-----------------------------------------------------------------------------------------------
Bu motor, 0.5C (50 MW / 100 MWh) batarya sistemi için:
1. Sürekli Değişken Güç Modülasyonu (Continuous Fractional Power: 0.0 - 50.0 MW arası her değer)
2. Doğrusal Programlama (Linear Programming - SciPy HiGHS Solver)
3. Dinamik Çevrim Kısıtları (1.0 EFC, 1.5 EFC, 2.0 EFC, Kısıtsız / Serbest)
4. Opsiyonel Rampa Hızı Kısıtları (MW/Saat)
ile matematiksel olarak tam global optimum arbitraj çözümünü üretir.

NOT: Daha önce geliştirilen 4 temel blok/ayrık senaryo modeli,
`bess_05c/src/optimizer_05c_scenarios_backup.py` dosyasında güvenle saklanmaktadır.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy.optimize import linprog


class LPStrategy(str, Enum):
    LP_1_CYCLE = "lp_1_cycle"         # 1.0 Çevrim Kısıtlı LP (Koruyucu / Pil Ömrü Odaklı)
    LP_15_CYCLE = "lp_15_cycle"       # 1.5 Çevrim Kısmi Modülasyon (Fırsatçı Ara Pik)
    LP_2_CYCLE = "lp_2_cycle"         # 2.0 Çevrim Çift Çevrim LP (Yüksek Hacim)
    LP_UNCONSTRAINED = "lp_free"      # Kısıtsız Serbest LP (Maksimum Kâr Tavanı)


LP_STRATEGY_METADATA: Dict[str, Dict[str, Any]] = {
    LPStrategy.LP_1_CYCLE: {
        "title": "1.0 Döngü Senaryosu",
        "short_title": "Senaryo (1.0 EFC)",
        "desc": "Günde en fazla 1 tam eşdeğer dolum ve boşalım (100 MWh). Hücre ömrünü korur.",
        "max_cycles": 1.0,
        "badge_color": "#0ea5e9",
        "tag": "Koruyucu 1 Döngü"
    },
    LPStrategy.LP_15_CYCLE: {
        "title": "1.5 Döngü Kısmi Modülasyon Senaryosu",
        "short_title": "Senaryo (1.5 EFC)",
        "desc": "Günde 1.5 eşdeğer döngü (150 MWh deşarj). Kısmi güç ve ara piklerden yararlanır.",
        "max_cycles": 1.5,
        "badge_color": "#89ceff",
        "tag": "Fırsatçı 1.5 Döngü"
    },
    LPStrategy.LP_2_CYCLE: {
        "title": "2.0 Döngü Çift Döngü Senaryosu",
        "short_title": "Senaryo (2.0 EFC)",
        "desc": "Günde 2 tam döngü (200 MWh deşarj). Gece ve öğle dip şarjları, sabah ve akşam pik satışları.",
        "max_cycles": 2.0,
        "badge_color": "#4edea3",
        "tag": "Yüksek Hacimli 2 Döngü"
    },
    LPStrategy.LP_UNCONSTRAINED: {
        "title": "Kısıtsız Serbest Senaryo (Kâr Tavanı)",
        "short_title": "Senaryo (Kısıtsız)",
        "desc": "Döngü sınırı olmaksızın spread oluşan tüm saatlerde sürekli güç modülasyonu ile kâr tavanı.",
        "max_cycles": None,
        "badge_color": "#ffb95f",
        "tag": "Maksimum Kâr Tavanı"
    }
}


@dataclass
class BESSConfig05C:
    """0.5C BESS Sistem ve LP İşletme Parametreleri."""
    power_mw: float = 50.0          # Nominal Güç (MW)
    c_rate: float = 0.5             # C-Rate (0.5C -> 2 saat tam şarj / 2 saat tam deşarj)
    rte: float = 0.85               # Round-Trip Efficiency (Verimlilik)
    soc_start_pct: float = 0.0      # Güne Başlangıç SoC (%)
    soc_end_pct: float = 0.0        # Gün Sonu Hedef SoC (%)
    soc_min_pct: Optional[float] = None  # Minimum Güvenlik SoC Rezervi (DoD Tabanı, None ise min(start, end) kullanılır)
    soc_max_pct: float = 100.0      # Maksimum Güvenlik SoC Tavanı (%)
    degradation_cost: float = 0.0   # Yıpranma Maliyeti ($/MWh hücre deşarjı)
    strategy: str = "lp_1_cycle"    # LP Çevrim Stratejisi
    max_daily_cycles: Optional[float] = 1.0  # Günlük maks EFC sınırı (None = serbest)
    ramp_limit_mw: Optional[float] = None    # Rampa Hızı Kısıtı (MW/Saat, None = sınırsız)

    @property
    def duration_hours(self) -> float:
        """Tam dolum/boşalım süresi (saat). 0.5C için 2.0 saattir."""
        return 1.0 / self.c_rate

    @property
    def capacity_mwh(self) -> float:
        """Enerji Kapasitesi (MWh) = Güç x Süre (örn: 50 MW x 2h = 100 MWh)."""
        return self.power_mw * self.duration_hours


@dataclass
class DayOptimizationResult:
    """Tek bir günün 0.5C LP optimizasyon çıktısı."""
    success: bool
    is_passed: bool
    strategy: str
    p_charge: np.ndarray        # Saatlik sürekli şarj gücü (MW) [24]
    p_discharge: np.ndarray     # Saatlik sürekli deşarj gücü (MW) [24]
    soc_mwh: np.ndarray         # Saatlik batarya enerji seviyesi (MWh) [24]
    soc_pct: np.ndarray         # Saatlik batarya doluluk oranı (%) [24]
    total_charged_mwh: float    # Şebekeden çekilen brüt elektrik (MWh)
    total_discharged_mwh: float # Şebekeye satılan net elektrik (MWh)
    charge_cost: float          # Toplam şarj maliyeti ($)
    discharge_revenue: float    # Toplam deşarj geliri ($)
    gross_profit: float         # Brüt kâr ($) = Gelir - Maliyet
    degradation_cost: float     # Yıpranma amortismanı ($)
    net_profit: float           # Net arbitraj kârı ($) = Brüt - Yıpranma
    avg_charge_price: float     # Ağırlıklı ortalama alış fiyatı ($/MWh)
    avg_discharge_price: float  # Ağırlıklı ortalama satış fiyatı ($/MWh)
    realized_spread: float      # Gerçekleşen spread ($/MWh)
    cycles: float               # Eşdeğer Tam Çevrim (EFC)
    fractional_hours_count: int # Kısmi güçte çalışılan saat sayısı (0 < P < P_max)
    active_hours_count: int     # Şarj veya deşarj yapılan toplam saat sayısı
    details: Dict[str, Any] = field(default_factory=dict)


def optimize_day_05c(
    prices: np.ndarray,
    config: BESSConfig05C,
    strategy: Optional[str] = None
) -> DayOptimizationResult:
    """
    SciPy HiGHS Çözücüsü ile 24 saatlik Sürekli Doğrusal Programlama (LP) optimizasyonunu çalıştırır.
    Her saat için p_charge ve p_discharge [0, P_max] sürekli aralığında modüle edilir.
    """
    strat_key = strategy or config.strategy
    if strat_key not in LP_STRATEGY_METADATA:
        strat_key = LPStrategy.LP_1_CYCLE

    meta = LP_STRATEGY_METADATA[strat_key]
    max_cycles = meta["max_cycles"]

    if isinstance(prices, pd.DataFrame):
        if "ptf_usd" in prices.columns:
            prices = prices["ptf_usd"].values
        else:
            prices = prices.iloc[:, 0].values
    elif isinstance(prices, pd.Series):
        prices = prices.values
    prices = np.asarray(prices, dtype=float)

    P_max = float(config.power_mw)
    E_max = float(config.capacity_mwh)
    rte = float(config.rte)
    deg_unit = float(config.degradation_cost)
    ramp_limit = config.ramp_limit_mw

    min_soc_pct = config.soc_min_pct if config.soc_min_pct is not None else min(config.soc_start_pct, config.soc_end_pct)
    max_soc_pct = config.soc_max_pct if config.soc_max_pct is not None else 100.0

    E_min = (float(min_soc_pct) / 100.0) * E_max
    E_max_bound = (float(max_soc_pct) / 100.0) * E_max

    E_start = np.clip((config.soc_start_pct / 100.0) * E_max, E_min, E_max_bound)
    E_end = np.clip((config.soc_end_pct / 100.0) * E_max, E_min, E_max_bound)

    T = len(prices)
    if T != 24:
        raise ValueError(f"Fiyat dizisi 24 saat olmalıdır, alınan: {T}")

    # =========================================================================
    # LP MODEL KURULUMU (SciPy linprog formatı)
    # Değişken Vektörü (72 Değişken):
    # x = [p_ch_0..p_ch_23 (24), p_dis_0..p_dis_23 (24), E_0..E_23 (24)]
    # =========================================================================

    # Amaç Fonksiyonu Katsayıları (Minimize c^T x)
    # Maximize: sum_t [ p_dis_t * (prices_t * rte - deg_unit) - p_ch_t * prices_t ]
    # Minimize: sum_t [ p_ch_t * prices_t - p_dis_t * (prices_t * rte - deg_unit) ]
    c = np.zeros(72)
    for t in range(24):
        c[t] = prices[t]                              # p_ch_t maliyeti (+)
        c[24 + t] = -(prices[t] * rte - deg_unit)      # p_dis_t net getirisi (-)
        c[48 + t] = 0.0                                # E_t doğrudan amaçta yok

    # Değişken Sınırları (Bounds)
    bounds = []
    for _ in range(24):
        bounds.append((0.0, P_max))  # p_ch in [0, P_max]
    for _ in range(24):
        bounds.append((0.0, P_max))  # p_dis in [0, P_max]
    for _ in range(24):
        bounds.append((E_min, E_max_bound))  # E in [E_min, E_max_bound] (DoD Taban Rezerv ve Güvenlik Tavanı)

    # Eşitlik Kısıtları (A_eq x = b_eq) - Enerji Denge Denklemleri
    # E_0 - p_ch_0 + p_dis_0 = E_start
    # E_t - E_{t-1} - p_ch_t + p_dis_t = 0 (t = 1..23)
    # E_23 = E_end (Gün sonu hedef doluluk)
    A_eq = np.zeros((25, 72))
    b_eq = np.zeros(25)

    A_eq[0, 48] = 1.0   # E_0
    A_eq[0, 0] = -1.0   # -p_ch_0
    A_eq[0, 24] = 1.0   # +p_dis_0
    b_eq[0] = E_start

    for t in range(1, 24):
        A_eq[t, 48 + t] = 1.0       # E_t
        A_eq[t, 48 + t - 1] = -1.0   # -E_{t-1}
        A_eq[t, t] = -1.0           # -p_ch_t
        A_eq[t, 24 + t] = 1.0       # +p_dis_t
        b_eq[t] = 0.0

    A_eq[24, 71] = 1.0  # E_23 = E_end
    b_eq[24] = E_end

    # Eşitsizlik Kısıtları (A_ub x <= b_ub)
    ub_rows = []
    ub_vals = []

    # 1. Çevrim Kısıtı: sum(p_dis) <= max_cycles * E_max
    if max_cycles is not None and max_cycles > 0:
        row_cyc = np.zeros(72)
        row_cyc[24:48] = 1.0
        ub_rows.append(row_cyc)
        ub_vals.append(max_cycles * E_max)

    # 2. Rampa Hızı Kısıtları (Opsiyonel): -R <= P_t - P_{t-1} <= R
    if ramp_limit is not None and ramp_limit > 0 and ramp_limit < P_max:
        R = float(ramp_limit)
        for t in range(1, 24):
            # p_ch rampa yukarı: p_ch_t - p_ch_{t-1} <= R
            r_up_ch = np.zeros(72)
            r_up_ch[t] = 1.0; r_up_ch[t - 1] = -1.0
            ub_rows.append(r_up_ch); ub_vals.append(R)

            # p_ch rampa aşağı: -p_ch_t + p_ch_{t-1} <= R
            r_dn_ch = np.zeros(72)
            r_dn_ch[t] = -1.0; r_dn_ch[t - 1] = 1.0
            ub_rows.append(r_dn_ch); ub_vals.append(R)

            # p_dis rampa yukarı: p_dis_t - p_dis_{t-1} <= R
            r_up_dis = np.zeros(72)
            r_up_dis[24 + t] = 1.0; r_up_dis[24 + t - 1] = -1.0
            ub_rows.append(r_up_dis); ub_vals.append(R)

            # p_dis rampa aşağı: -p_dis_t + p_dis_{t-1} <= R
            r_dn_dis = np.zeros(72)
            r_dn_dis[24 + t] = -1.0; r_dn_dis[24 + t - 1] = 1.0
            ub_rows.append(r_dn_dis); ub_vals.append(R)

    if ub_rows:
        A_ub = np.array(ub_rows)
        b_ub = np.array(ub_vals)
    else:
        A_ub = None
        b_ub = None

    # HiGHS Çözücüsü ile Çöz
    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs"
    )

    if not res.success or (-res.fun) <= 1e-4:
        # Pas geçme / bekleme durumu
        return DayOptimizationResult(
            success=res.success,
            is_passed=True,
            strategy=strat_key,
            p_charge=np.zeros(24),
            p_discharge=np.zeros(24),
            soc_mwh=np.full(24, E_start),
            soc_pct=np.full(24, config.soc_start_pct),
            total_charged_mwh=0.0,
            total_discharged_mwh=0.0,
            charge_cost=0.0,
            discharge_revenue=0.0,
            gross_profit=0.0,
            degradation_cost=0.0,
            net_profit=0.0,
            avg_charge_price=0.0,
            avg_discharge_price=0.0,
            realized_spread=0.0,
            cycles=0.0,
            fractional_hours_count=0,
            active_hours_count=0,
            details={"status": "Pas Geçildi (Pozitif kâr oluşmadı)"}
        )

    # Optimum Vektör Çıkarımı
    p_ch = np.maximum(0.0, res.x[:24])
    p_dis = np.maximum(0.0, res.x[24:48])
    E_soc = np.maximum(0.0, np.minimum(E_max, res.x[48:72]))

    # Sayısal gürültü temizliği (< 0.05 MW sıfır kabul edilir)
    p_ch[p_ch < 0.05] = 0.0
    p_dis[p_dis < 0.05] = 0.0

    # Kısmi güç saatlerinin tespiti (0.05 MW < P < P_max - 0.05 MW)
    frac_ch = (p_ch > 0.05) & (p_ch < P_max - 0.05)
    frac_dis = (p_dis > 0.05) & (p_dis < P_max - 0.05)
    fractional_hours_count = int(np.sum(frac_ch) + np.sum(frac_dis))
    active_hours_count = int(np.sum(p_ch > 0.05) + np.sum(p_dis > 0.05))

    # Enerji ve Finansal Hesaplamalar
    total_charged_mwh = float(np.sum(p_ch))
    cell_discharged_mwh = float(np.sum(p_dis))
    total_discharged_mwh = float(cell_discharged_mwh * rte)

    charge_cost = float(np.sum(prices * p_ch))
    discharge_revenue = float(np.sum(prices * p_dis * rte))
    gross_profit = discharge_revenue - charge_cost
    degradation_cost = float(cell_discharged_mwh * deg_unit)
    net_profit = gross_profit - degradation_cost

    avg_ch = float(charge_cost / total_charged_mwh) if total_charged_mwh > 0 else 0.0
    avg_dis = float(discharge_revenue / total_discharged_mwh) if total_discharged_mwh > 0 else 0.0
    spread = avg_dis - avg_ch
    cycles = float(cell_discharged_mwh / E_max)
    soc_pct = (E_soc / E_max) * 100.0

    return DayOptimizationResult(
        success=True,
        is_passed=False,
        strategy=strat_key,
        p_charge=p_ch,
        p_discharge=p_dis,
        soc_mwh=E_soc,
        soc_pct=soc_pct,
        total_charged_mwh=total_charged_mwh,
        total_discharged_mwh=total_discharged_mwh,
        charge_cost=charge_cost,
        discharge_revenue=discharge_revenue,
        gross_profit=gross_profit,
        degradation_cost=degradation_cost,
        net_profit=net_profit,
        avg_charge_price=avg_ch,
        avg_discharge_price=avg_dis,
        realized_spread=spread,
        cycles=cycles,
        fractional_hours_count=fractional_hours_count,
        active_hours_count=active_hours_count,
        details={
            "status": "Optimal LP",
            "active_hours": active_hours_count,
            "fractional_hours": fractional_hours_count
        }
    )


def simulate_period_05c(
    df: pd.DataFrame,
    config: BESSConfig05C,
    strategy: Optional[str] = None,
    num_days: Optional[int] = 15
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Belirtilen dönem (örn. 15 gün veya 365 gün) için LP optimizasyonunu çalıştırır.
    """
    strat = strategy or config.strategy
    dates = sorted(df["date"].unique())
    if num_days is not None and num_days > 0:
        dates = dates[:num_days]

    daily_rows = []
    hourly_rows = []

    for idx, d in enumerate(dates):
        day_p = df[df["date"] == d].sort_values("hour")
        prices = day_p["ptf_usd"].values

        res = optimize_day_05c(prices, config, strategy=strat)

        # Şarj ve deşarj saat metinleri
        ch_hours = [t for t in range(24) if res.p_charge[t] > 0.05]
        dis_hours = [t for t in range(24) if res.p_discharge[t] > 0.05]

        ch_hours_str = ", ".join(f"{h:02d}:00 ({res.p_charge[h]:.0f}MW)" for h in ch_hours) if ch_hours else "Pas (0 MW)"
        dis_hours_str = ", ".join(f"{h:02d}:00 ({res.p_discharge[h]:.0f}MW)" for h in dis_hours) if dis_hours else "Pas (0 MW)"

        daily_rows.append({
            "date": pd.to_datetime(d),
            "day_index": idx + 1,
            "status": "PAS GEÇİLDİ" if res.is_passed else "AKTİF",
            "is_passed": res.is_passed,
            "net_profit": res.net_profit,
            "gross_profit": res.gross_profit,
            "revenue": res.discharge_revenue,
            "total_revenue": res.discharge_revenue,
            "discharge_revenue": res.discharge_revenue,
            "cost": res.charge_cost,
            "total_cost": res.charge_cost,
            "charge_cost": res.charge_cost,
            "degradation": res.degradation_cost,
            "degradation_cost": res.degradation_cost,
            "spread": res.realized_spread,
            "ptf_spread": res.realized_spread,
            "cycles": res.cycles,
            "charge_hours": ch_hours_str,
            "discharge_hours": dis_hours_str,
            "avg_ch_price": res.avg_charge_price,
            "avg_dis_price": res.avg_discharge_price,
            "charged_mwh": res.total_charged_mwh,
            "discharged_mwh": res.total_discharged_mwh,
            "fractional_hours": res.fractional_hours_count,
            "active_hours": res.active_hours_count,
        })

        # Saatlik satırlar
        for t in range(24):
            pch = res.p_charge[t]
            pdis = res.p_discharge[t]
            ch_c = float(prices[t] * pch)
            dis_r = float(prices[t] * pdis * config.rte)
            deg_c = float(config.degradation_cost * pdis)
            is_frac = (0.05 < pch < config.power_mw - 0.05) or (0.05 < pdis < config.power_mw - 0.05)

            if pch > 0.05:
                act = f"ŞARJ ({pch:.1f} MW)"
            elif pdis > 0.05:
                act = f"DEŞARJ ({pdis:.1f} MW)"
            else:
                act = "BEKLEMEDE"

            hourly_rows.append({
                "date": pd.to_datetime(d),
                "hour": t,
                "saat_str": f"{t:02d}:00",
                "ptf_usd": prices[t],
                "p_charge": pch,
                "p_discharge": pdis,
                "p_charge_mw": pch,
                "p_discharge_mw": pdis,
                "p_ch_mw": pch,
                "p_dis_mw": pdis,
                "p_net": pdis - pch,
                "p_net_mw": pdis - pch,
                "soc_mwh": res.soc_mwh[t],
                "soc_pct": res.soc_pct[t],
                "is_charge": (pch > 0.05),
                "is_discharge": (pdis > 0.05),
                "is_fractional": is_frac,
                "charge_cost": ch_c,
                "discharge_revenue": dis_r,
                "degradation_cost": deg_c,
                "net_profit": dis_r - ch_c - deg_c,
                "action_label": act
            })

    daily_df = pd.DataFrame(daily_rows)
    hourly_df = pd.DataFrame(hourly_rows)

    if not daily_df.empty:
        daily_df["cum_net_profit"] = daily_df["net_profit"].cumsum()
        daily_df["cum_gross_profit"] = daily_df["gross_profit"].cumsum()
        daily_df["cum_revenue"] = daily_df["revenue"].cumsum()
        daily_df["cum_cost"] = daily_df["cost"].cumsum()
        daily_df["cum_cycles"] = daily_df["cycles"].cumsum()
        daily_df["date_str"] = pd.to_datetime(daily_df["date"]).dt.strftime("%d.%m.%Y")
        daily_df["day_name"] = pd.to_datetime(daily_df["date"]).dt.day_name()

    # Toplam KPI hesaplamaları
    tot_days = len(daily_df)
    active_days = int((daily_df["status"] == "AKTİF").sum()) if tot_days > 0 else 0
    passed_days = tot_days - active_days

    net_profit = float(daily_df["net_profit"].sum()) if tot_days > 0 else 0.0
    gross_profit = float(daily_df["gross_profit"].sum()) if tot_days > 0 else 0.0
    revenue = float(daily_df["revenue"].sum()) if tot_days > 0 else 0.0
    cost = float(daily_df["cost"].sum()) if tot_days > 0 else 0.0
    deg = float(daily_df["degradation"].sum()) if tot_days > 0 else 0.0
    cycles = float(daily_df["cycles"].sum()) if tot_days > 0 else 0.0
    tot_frac_hours = int(daily_df["fractional_hours"].sum()) if tot_days > 0 else 0

    avg_daily_profit = (net_profit / tot_days) if tot_days > 0 else 0.0
    profit_per_cycle = (net_profit / cycles) if cycles > 0 else 0.0

    active_mask = daily_df["status"] == "AKTİF"
    avg_spread = float(daily_df.loc[active_mask, "spread"].mean()) if active_days > 0 else 0.0
    avg_dis_p = float(daily_df.loc[active_mask, "avg_dis_price"].mean()) if active_days > 0 else 0.0
    avg_ch_p = float(daily_df.loc[active_mask, "avg_ch_price"].mean()) if active_days > 0 else 0.0

    kpis = {
        "period_days": tot_days,
        "active_days": active_days,
        "passed_days": passed_days,
        "net_profit": net_profit,
        "gross_profit": gross_profit,
        "total_revenue": revenue,
        "total_cost": cost,
        "total_degradation_cost": deg,
        "total_cycles": cycles,
        "avg_daily_profit": avg_daily_profit,
        "profit_per_cycle": profit_per_cycle,
        "realized_spread": avg_spread,
        "avg_discharge_price": avg_dis_p,
        "avg_charge_price": avg_ch_p,
        "total_fractional_hours": tot_frac_hours,
    }

    return daily_df, hourly_df, kpis


def compare_all_lp_strategies_05c(
    df: pd.DataFrame,
    config: BESSConfig05C,
    num_days: int = 15
) -> pd.DataFrame:
    """
    Tüm LP modülasyon stratejilerini (1.0 EFC, 1.5 EFC, 2.0 EFC, Kısıtsız LP) 
    aynı veri seti üzerinde karşılaştırır.
    """
    strategies = [
        LPStrategy.LP_1_CYCLE,
        LPStrategy.LP_15_CYCLE
    ]

    rows = []
    base_profit = None

    for strat in strategies:
        meta = LP_STRATEGY_METADATA[strat]
        _, _, kpis = simulate_period_05c(df, config, strategy=strat, num_days=num_days)

        if base_profit is None:
            base_profit = kpis["net_profit"]

        delta_vs_base = kpis["net_profit"] - base_profit
        pct_vs_base = (delta_vs_base / base_profit * 100.0) if base_profit > 0 else 0.0

        rows.append({
            "Strateji": meta["title"],
            "Kısa Kod": meta["short_title"],
            "Karakteristik": meta["tag"],
            "Net Kâr ($)": kpis["net_profit"],
            "1.0 Döngüye Göre Fark ($)": delta_vs_base,
            "Fark (%)": pct_vs_base,
            "Deşarj Geliri ($)": kpis["total_revenue"],
            "Şarj Maliyeti ($)": kpis["total_cost"],
            "Yıpranma ($)": kpis["total_degradation_cost"],
            "Gerçekleşen Spread ($/MWh)": kpis["realized_spread"],
            "Toplam Döngü (EFC)": kpis["total_cycles"],
            "Döngü Başı Kâr ($/Cycle)": kpis["profit_per_cycle"],
            "Kısmi Güç Saatleri": kpis["total_fractional_hours"],
            "Aktif / Pas Gün": f"{kpis['active_days']} / {kpis['passed_days']}",
        })

    return pd.DataFrame(rows)


def aggregate_monthly_05c(daily_df: pd.DataFrame, hourly_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Günlük optimizasyon çıktısını 12 aylık özet tabloya dönüştürür."""
    months_tr = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
        5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
        9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month

    rows = []
    for m in sorted(df["month"].unique()):
        m_daily = df[df["month"] == m]
        dis_rev = float(m_daily["discharge_revenue"].sum())
        ch_cost = float(m_daily["charge_cost"].sum())
        gr_prof = float(m_daily["gross_profit"].sum())
        deg_c = float(m_daily["degradation_cost"].sum())
        net_prof = float(m_daily["net_profit"].sum())
        cyc = float(m_daily["cycles"].sum())
        act_d = int((~m_daily["is_passed"]).sum())
        pas_d = int(m_daily["is_passed"].sum())
        ppc = (net_prof / cyc) if cyc > 0 else 0.0

        act_mask = ~m_daily["is_passed"]
        avg_spread = float(m_daily.loc[act_mask, "ptf_spread"].mean()) if act_d > 0 else float(m_daily["ptf_spread"].mean())

        if hourly_df is not None and not hourly_df.empty:
            h_df = hourly_df.copy()
            h_df["date"] = pd.to_datetime(h_df["date"])
            m_hourly = h_df[h_df["date"].dt.month == m]
            avg_ptf = float(m_hourly["ptf_usd"].mean()) if not m_hourly.empty else 0.0
        else:
            avg_ptf = 0.0

        rows.append({
            "month": m,
            "month_name": months_tr.get(m, f"{m}. Ay"),
            "revenue": dis_rev,
            "discharge_revenue": dis_rev,
            "cost": ch_cost,
            "charge_cost": ch_cost,
            "gross_profit": gr_prof,
            "degradation_cost": deg_c,
            "net_profit": net_prof,
            "cycles": cyc,
            "active_days": act_d,
            "passed_days": pas_d,
            "profit_per_cycle": ppc,
            "realized_spread": avg_spread,
            "avg_spread": avg_spread,
            "avg_ptf": avg_ptf
        })
    return pd.DataFrame(rows)
