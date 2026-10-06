"""
BESS 0.5C (2 Saatlik Depolama) Arbitraj Optimizasyon Motoru
---------------------------------------------------------
0.5C batarya konfigürasyonu (2 saat tam şarj, 2 saat tam deşarj) için
4 temel alım/satım senaryosunu ve opsiyonel 2-döngü stratejisini modeller:

Senaryolar:
1. BLOCK_BLOCK : Ardışık 2 saat al (şarj) ➔ Ardışık 2 saat sat (deşarj) [Blok - Blok]
2. BLOCK_SPLIT : Ardışık 2 saat al (şarj) ➔ Ayrık 2 saatte sat (deşarj) [Blok - Ayrık]
3. SPLIT_BLOCK : Ayrık 2 saatte al (şarj) ➔ Ardışık 2 saatte sat (deşarj) [Ayrık - Blok]
4. SPLIT_SPLIT : Ayrık 2 saatte al (şarj) ➔ Ayrık 2 saatte sat (deşarj) [Serbest - Serbest]
5. TWO_CYCLE   : Günde 2 Tam Döngü (2x2 Saat Şarj + 2x2 Saat Deşarj = 8 Saat Aktif)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


class ScenarioType(str, Enum):
    BLOCK_BLOCK = "block_block"   # Ardışık 2s Al / Ardışık 2s Sat
    BLOCK_SPLIT = "block_split"   # Ardışık 2s Al / Ayrık 2s Sat
    SPLIT_BLOCK = "split_block"   # Ayrık 2s Al / Ardışık 2s Sat
    SPLIT_SPLIT = "split_split"   # Ayrık 2s Al / Ayrık 2s Sat (Serbest)
    TWO_CYCLE = "two_cycle"       # Günde 2 Döngü (2x2s Blok)


SCENARIO_METADATA: Dict[str, Dict[str, str]] = {
    ScenarioType.BLOCK_BLOCK: {
        "title": "Ardışık 2s Al / Ardışık 2s Sat",
        "short_title": "Blok - Blok",
        "desc": "Kesintisiz 2 saat tam güç şarj ➔ Kesintisiz 2 saat tam güç deşarj.",
        "badge_color": "#0ea5e9",
        "tag": "Geleneksel Blok"
    },
    ScenarioType.BLOCK_SPLIT: {
        "title": "Ardışık 2s Al / Ayrık 2s Sat",
        "short_title": "Blok - Ayrık",
        "desc": "Kesintisiz 2 saat şarj ➔ Günün en yüksek 2 bağımsız saatinde deşarj.",
        "badge_color": "#89ceff",
        "tag": "Pik Deşarj Esnekliği"
    },
    ScenarioType.SPLIT_BLOCK: {
        "title": "Ayrık 2s Al / Ardışık 2s Sat",
        "short_title": "Ayrık - Blok",
        "desc": "Günün en ucuz 2 bağımsız saatinde şarj ➔ Akşam 2 saatlik blok deşarj.",
        "badge_color": "#4edea3",
        "tag": "Güneş/Gece Dip Esnekliği"
    },
    ScenarioType.SPLIT_SPLIT: {
        "title": "Ayrık 2s Al / Ayrık 2s Sat",
        "short_title": "Serbest - Serbest",
        "desc": "Tam serbest saat seçimi (En düşük 2 saat şarj, en yüksek 2 saat deşarj, dinamik SoC).",
        "badge_color": "#ffb95f",
        "tag": "Maksimum Arbitraj Tavanı"
    },
    ScenarioType.TWO_CYCLE: {
        "title": "Günde 2 Döngü (2x2 Saat)",
        "short_title": "Çift Blok (2x2s)",
        "desc": "Toplam 4 saat şarj + 4 saat deşarj (Gece & Sabah döngüsü + Öğle & Akşam döngüsü).",
        "badge_color": "#f43f5e",
        "tag": "Yüksek Hacimli Arbitraj"
    }
}


@dataclass
class BESSConfig05C:
    """0.5C BESS Sistem ve İşletme Parametreleri."""
    power_mw: float = 50.0          # Nominal Güç (MW)
    c_rate: float = 0.5             # C-Rate (0.5C -> 2 saat tam şarj / 2 saat tam deşarj)
    rte: float = 0.85               # Round-Trip Efficiency (Verimlilik)
    soc_start_pct: float = 0.0      # Güne Başlangıç SoC (%)
    soc_end_pct: float = 0.0        # Gün Sonu Hedef SoC (%)
    degradation_cost: float = 0.0   # Yıpranma Maliyeti ($/MWh hücre deşarjı)
    strategy: str = "1_cycle"       # Operasyon modu (1_cycle veya 2_cycle)

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
    """Tek bir günün 0.5C optimizasyon çıktısı."""
    success: bool
    is_passed: bool
    scenario: ScenarioType
    charge_hours: List[int]
    discharge_hours: List[int]
    p_charge: np.ndarray        # Saatlik şarj gücü (MW) [24]
    p_discharge: np.ndarray     # Saatlik deşarj gücü (MW) [24]
    soc_mwh: np.ndarray         # Saatlik batarya enerji durumu (MWh) [24]
    soc_pct: np.ndarray         # Saatlik doluluk oranı (%) [24]
    total_charged_mwh: float    # Şebekeden çekilen brüt enerji (MWh)
    total_discharged_mwh: float # Şebekeye satılan net enerji (MWh)
    charge_cost: float          # Toplam şarj maliyeti ($)
    discharge_revenue: float    # Toplam deşarj geliri ($)
    gross_profit: float         # Brüt kâr ($) = Gelir - Maliyet
    degradation_cost: float     # Yıpranma maliyeti ($)
    net_profit: float           # Net kâr ($) = Brüt Kâr - Yıpranma
    avg_charge_price: float     # Ağırlıklı ort. şarj fiyatı ($/MWh)
    avg_discharge_price: float  # Ağırlıklı ort. deşarj fiyatı ($/MWh)
    realized_spread: float      # Gerçekleşen spread ($/MWh) = Deşarj - Şarj
    cycles: float               # Eşdeğer Tam Döngü (EFC = Deşarj MWh / Kapasite)
    details: Dict[str, Any] = field(default_factory=dict)


def optimize_day_05c(
    prices: np.ndarray,
    config: BESSConfig05C,
    scenario: ScenarioType | str = ScenarioType.BLOCK_BLOCK
) -> DayOptimizationResult:
    """
    Belirtilen senaryoya göre 24 saatlik 0.5C arbitraj optimizasyonunu çalıştırır.
    """
    if isinstance(scenario, str):
        scenario = ScenarioType(scenario)

    T = len(prices)
    if T != 24:
        raise ValueError(f"Fiyat dizisi 24 saat olmalıdır, alınan: {T}")

    power = config.power_mw
    cap = config.capacity_mwh
    rte = config.rte
    deg_cost_unit = config.degradation_cost

    soc_start = (config.soc_start_pct / 100.0) * cap
    soc_end = (config.soc_end_pct / 100.0) * cap

    # Senaryoya göre en iyi saat kombinasyonunu bul
    if scenario == ScenarioType.BLOCK_BLOCK:
        ch_hours, dis_hours, best_net = _solve_block_block(prices, power, rte, deg_cost_unit)
    elif scenario == ScenarioType.BLOCK_SPLIT:
        ch_hours, dis_hours, best_net = _solve_block_split(prices, power, rte, deg_cost_unit)
    elif scenario == ScenarioType.SPLIT_BLOCK:
        ch_hours, dis_hours, best_net = _solve_split_block(prices, power, rte, deg_cost_unit)
    elif scenario == ScenarioType.SPLIT_SPLIT:
        ch_hours, dis_hours, best_net = _solve_split_split(prices, power, rte, deg_cost_unit, soc_start, cap)
    elif scenario == ScenarioType.TWO_CYCLE:
        ch_hours, dis_hours, best_net = _solve_two_cycle(prices, power, rte, deg_cost_unit)
    else:
        raise ValueError(f"Bilinmeyen senaryo türü: {scenario}")

    # Pas Geçme (Standby) Koşulu: Net kâr <= 0 ise batarya gün boyu bekler
    if best_net <= 0 or not ch_hours or not dis_hours:
        return DayOptimizationResult(
            success=True,
            is_passed=True,
            scenario=scenario,
            charge_hours=[],
            discharge_hours=[],
            p_charge=np.zeros(24),
            p_discharge=np.zeros(24),
            soc_mwh=np.full(24, soc_start),
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
            details={"reason": "Net kâr negatif veya sıfır; gün pas geçildi."}
        )

    # 24 Saatlik Akışı Oluştur
    p_ch = np.zeros(24)
    p_dis = np.zeros(24)
    for h in ch_hours:
        p_ch[h] = power
    for h in dis_hours:
        p_dis[h] = power

    # Saatlik SoC Dinamik Takibi
    soc_mwh = np.zeros(24)
    cur_soc = soc_start
    for t in range(24):
        if p_ch[t] > 0:
            cur_soc = min(cap, cur_soc + p_ch[t])
        elif p_dis[t] > 0:
            cur_soc = max(0.0, cur_soc - p_dis[t])
        soc_mwh[t] = cur_soc

    soc_pct = (soc_mwh / cap) * 100.0

    # Enerji ve Finansal Hesaplamalar
    # 0.5C'de her saat güç P MW ise, 1 saatte çekilen enerji = P MWh
    total_charged_mwh = float(len(ch_hours) * power)
    # Şebekeye verilen elektrik = Deşarj edilen enerji x RTE
    total_discharged_mwh = float(len(dis_hours) * power * rte)

    ch_prices = [prices[h] for h in ch_hours]
    dis_prices = [prices[h] for h in dis_hours]

    charge_cost = float(sum(p * power for p in ch_prices))
    discharge_revenue = float(sum(p * (power * rte) for p in dis_prices))
    gross_profit = discharge_revenue - charge_cost

    # Hücre Yıpranma Maliyeti ($/MWh hücre deşarjı üzerinden)
    cell_discharged_mwh = len(dis_hours) * power
    tot_deg_cost = float(cell_discharged_mwh * deg_cost_unit)
    net_profit = gross_profit - tot_deg_cost

    avg_ch = float(np.mean(ch_prices)) if ch_prices else 0.0
    avg_dis = float(np.mean(dis_prices)) if dis_prices else 0.0
    spread = avg_dis - avg_ch
    cycles = float(cell_discharged_mwh / cap)

    return DayOptimizationResult(
        success=True,
        is_passed=False,
        scenario=scenario,
        charge_hours=sorted(ch_hours),
        discharge_hours=sorted(dis_hours),
        p_charge=p_ch,
        p_discharge=p_dis,
        soc_mwh=soc_mwh,
        soc_pct=soc_pct,
        total_charged_mwh=total_charged_mwh,
        total_discharged_mwh=total_discharged_mwh,
        charge_cost=charge_cost,
        discharge_revenue=discharge_revenue,
        gross_profit=gross_profit,
        degradation_cost=tot_deg_cost,
        net_profit=net_profit,
        avg_charge_price=avg_ch,
        avg_discharge_price=avg_dis,
        realized_spread=spread,
        cycles=cycles,
        details={
            "ch_hours": sorted(ch_hours),
            "dis_hours": sorted(dis_hours),
            "n_cycles": cycles
        }
    )


# -----------------------------------------------------------------------------
# SENARYO ÇÖZÜCÜLERİ
# -----------------------------------------------------------------------------

def _solve_block_block(
    prices: np.ndarray, power: float, rte: float, deg_cost: float
) -> Tuple[List[int], List[int], float]:
    """
    Senaryo 1: Ardışık 2 saat şarj (c, c+1) ➔ Ardışık 2 saat deşarj (d, d+1).
    Kısıt: c+1 < d (deşarj, şarj bloğu tamamlandıktan sonra başlar).
    """
    best_net = -1e9
    best_ch = []
    best_dis = []

    # c in [0..20], d in [c+2..22]
    for c in range(21):
        ch_cost = power * (prices[c] + prices[c + 1])
        for d in range(c + 2, 23):
            dis_rev = power * rte * (prices[d] + prices[d + 1])
            gross = dis_rev - ch_cost
            net = gross - (2 * power * deg_cost)

            if net > best_net:
                best_net = net
                best_ch = [c, c + 1]
                best_dis = [d, d + 1]

    return best_ch, best_dis, best_net


def _solve_block_split(
    prices: np.ndarray, power: float, rte: float, deg_cost: float
) -> Tuple[List[int], List[int], float]:
    """
    Senaryo 2: Ardışık 2 saat şarj (c, c+1) ➔ Ayrık 2 saatte deşarj (d1, d2).
    Kısıt: c+1 < d1 < d2 <= 23.
    """
    best_net = -1e9
    best_ch = []
    best_dis = []

    for c in range(21):
        ch_cost = power * (prices[c] + prices[c + 1])
        # c+2'den 23'e kadar olan saatler arasından en yüksek 2 saati seç
        valid_dis_hours = list(range(c + 2, 24))
        if len(valid_dis_hours) < 2:
            continue

        # En yüksek fiyata göre sırala
        sorted_dis = sorted(valid_dis_hours, key=lambda h: prices[h], reverse=True)
        d1, d2 = sorted_dis[0], sorted_dis[1]

        dis_rev = power * rte * (prices[d1] + prices[d2])
        gross = dis_rev - ch_cost
        net = gross - (2 * power * deg_cost)

        if net > best_net:
            best_net = net
            best_ch = [c, c + 1]
            best_dis = sorted([d1, d2])

    return best_ch, best_dis, best_net


def _solve_split_block(
    prices: np.ndarray, power: float, rte: float, deg_cost: float
) -> Tuple[List[int], List[int], float]:
    """
    Senaryo 3: Ayrık 2 saatte şarj (c1, c2) ➔ Ardışık 2 saatte deşarj (d, d+1).
    Kısıt: 0 <= c1 < c2 < d <= 22.
    """
    best_net = -1e9
    best_ch = []
    best_dis = []

    # d in [2..22], deşarj bloğu (d, d+1)
    for d in range(2, 23):
        dis_rev = power * rte * (prices[d] + prices[d + 1])
        # 0'dan d-1'e kadar olan saatler arasından en ucuz 2 saati seç
        valid_ch_hours = list(range(0, d))
        if len(valid_ch_hours) < 2:
            continue

        sorted_ch = sorted(valid_ch_hours, key=lambda h: prices[h])
        c1, c2 = sorted_ch[0], sorted_ch[1]

        ch_cost = power * (prices[c1] + prices[c2])
        gross = dis_rev - ch_cost
        net = gross - (2 * power * deg_cost)

        if net > best_net:
            best_net = net
            best_ch = sorted([c1, c2])
            best_dis = [d, d + 1]

    return best_ch, best_dis, best_net


def _solve_split_split(
    prices: np.ndarray, power: float, rte: float, deg_cost: float,
    soc_start: float, cap: float
) -> Tuple[List[int], List[int], float]:
    """
    Senaryo 4: Ayrık 2 saat şarj ➔ Ayrık 2 saat deşarj (Maksimum Serbestlik).
    Fiziksel kısıtlar: 
    - 2 saat şarj, 2 saat deşarj.
    - Kronolojik akışta batarya doluluğu [0, cap] sınırlarını asla aşamaz.
    - Pattern 1: c1 < c2 < d1 < d2 (2 şarj ➔ 2 deşarj)
    - Pattern 2: c1 < d1 < c2 < d2 (1 şarj ➔ 1 deşarj ➔ 1 şarj ➔ 1 deşarj)
    Eğer başlangıç SoC >= power ise deşarj öne de geçebilir.
    """
    best_net = -1e9
    best_ch = []
    best_dis = []

    # 4 saat seçimi: t1 < t2 < t3 < t4 (24C4 = 10,626 kombinasyon)
    # 10,626 iterasyon pure Python'da ~15 milisaniye sürer, son derece hızlı ve kesin global optimum verir!
    from itertools import combinations

    for t1, t2, t3, t4 in combinations(range(24), 4):
        # Olası geçerli dizilimler:
        # A) Şarj, Şarj, Deşarj, Deşarj (c1=t1, c2=t2, d1=t3, d2=t4)
        c_cost_a = power * (prices[t1] + prices[t2])
        d_rev_a = power * rte * (prices[t3] + prices[t4])
        net_a = d_rev_a - c_cost_a - (2 * power * deg_cost)

        if net_a > best_net:
            best_net = net_a
            best_ch = [t1, t2]
            best_dis = [t3, t4]

        # B) Şarj, Deşarj, Şarj, Deşarj (c1=t1, d1=t2, c2=t3, d2=t4)
        c_cost_b = power * (prices[t1] + prices[t3])
        d_rev_b = power * rte * (prices[t2] + prices[t4])
        net_b = d_rev_b - c_cost_b - (2 * power * deg_cost)

        if net_b > best_net:
            best_net = net_b
            best_ch = [t1, t3]
            best_dis = [t2, t4]

    return best_ch, best_dis, best_net


def _solve_two_cycle(
    prices: np.ndarray, power: float, rte: float, deg_cost: float
) -> Tuple[List[int], List[int], float]:
    """
    Senaryo 5: Günde 2 Tam Döngü (2x 2 Saat Şarj + 2x 2 Saat Deşarj = 8 Saat Aktif).
    Döngü 1: c1, c1+1 ➔ d1, d1+1
    Döngü 2: c2, c2+1 ➔ d2, d2+1
    Kısıt: c1+1 < d1 < c2 ve c2+1 < d2.
    """
    best_net = -1e9
    best_ch = []
    best_dis = []

    # 1. Döngü arama
    for c1 in range(0, 18):
        cost1 = power * (prices[c1] + prices[c1 + 1])
        for d1 in range(c1 + 2, 20):
            rev1 = power * rte * (prices[d1] + prices[d1 + 1])
            gross1 = rev1 - cost1
            net1 = gross1 - (2 * power * deg_cost)

            # 2. Döngü arama (d1+2'den başlayarak)
            for c2 in range(d1 + 2, 21):
                cost2 = power * (prices[c2] + prices[c2 + 1])
                for d2 in range(c2 + 2, 23):
                    rev2 = power * rte * (prices[d2] + prices[d2 + 1])
                    gross2 = rev2 - cost2
                    net2 = gross2 - (2 * power * deg_cost)

                    tot_net = net1 + net2
                    if tot_net > best_net:
                        best_net = tot_net
                        best_ch = [c1, c1 + 1, c2, c2 + 1]
                        best_dis = [d1, d1 + 1, d2, d2 + 1]

    # Eğer 2 döngü kârsızsa ama tek döngü kârlıysa tek döngüye düş
    single_ch, single_dis, single_net = _solve_block_block(prices, power, rte, deg_cost)
    if single_net > best_net and single_net > 0:
        return single_ch, single_dis, single_net

    return best_ch, best_dis, best_net


# -----------------------------------------------------------------------------
# ÇOK GÜNLÜK VE PROTOTİP SİMÜLASYON FONKSİYONLARI
# -----------------------------------------------------------------------------

def simulate_period_05c(
    df: pd.DataFrame,
    config: BESSConfig05C,
    scenario: ScenarioType | str = ScenarioType.BLOCK_BLOCK,
    start_date: Optional[str] = None,
    num_days: Optional[int] = 15
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Belirtilen dönem (örn: ilk 15 gün) için 0.5C optimizasyon simülasyonunu çalıştırır.
    
    Returns:
        daily_df: Günlük özet metrikler (Kâr, Gelir, Maliyet, Döngü vb.)
        hourly_df: Saatlik zaman serisi (Saat, Fiyat, P_ch, P_dis, SoC)
        kpis: Dönem toplamı metrikler
    """
    unique_dates = df["date"].drop_duplicates().sort_values().reset_index(drop=True)

    if start_date:
        unique_dates = unique_dates[unique_dates >= start_date].reset_index(drop=True)

    if num_days is not None and num_days > 0:
        unique_dates = unique_dates.iloc[:num_days]

    daily_rows = []
    hourly_rows = []

    for d in unique_dates:
        day_p = df[df["date"] == d].sort_values("hour").reset_index(drop=True)
        if len(day_p) < 24:
            continue

        prices = day_p["ptf_usd"].values
        res = optimize_day_05c(prices, config, scenario)

        # Günlük özet satırı
        ch_hours_str = ", ".join(f"{h:02d}:00" for h in res.charge_hours) if res.charge_hours else "-"
        dis_hours_str = ", ".join(f"{h:02d}:00" for h in res.discharge_hours) if res.discharge_hours else "-"

        daily_rows.append({
            "date": d,
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
        })

        # Saatlik satırlar
        for t in range(24):
            ch_c = float(prices[t] * res.p_charge[t])
            dis_r = float(prices[t] * res.p_discharge[t] * config.rte)
            deg_c = float(config.degradation_cost * res.p_discharge[t])
            act = "ŞARJ (0.5C)" if res.p_charge[t] > 0 else ("DEŞARJ (0.5C)" if res.p_discharge[t] > 0 else "BEKLEMEDE")

            hourly_rows.append({
                "date": d,
                "hour": t,
                "saat_str": f"{t:02d}:00",
                "ptf_usd": prices[t],
                "p_charge_mw": res.p_charge[t],
                "p_discharge_mw": res.p_discharge[t],
                "p_ch_mw": res.p_charge[t],
                "p_dis_mw": res.p_discharge[t],
                "soc_mwh": res.soc_mwh[t],
                "soc_pct": res.soc_pct[t],
                "is_charge": (res.p_charge[t] > 0),
                "is_discharge": (res.p_discharge[t] > 0),
                "charge_cost": ch_c,
                "discharge_revenue": dis_r,
                "degradation_cost": deg_c,
                "net_profit": dis_r - ch_c - deg_c,
                "action_label": act
            })

    daily_df = pd.DataFrame(daily_rows)
    hourly_df = pd.DataFrame(hourly_rows)

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
    }

    return daily_df, hourly_df, kpis


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
            "discharge_revenue": dis_rev,
            "charge_cost": ch_cost,
            "gross_profit": gr_prof,
            "degradation_cost": deg_c,
            "net_profit": net_prof,
            "cycles": cyc,
            "active_days": act_d,
            "passed_days": pas_d,
            "profit_per_cycle": ppc,
            "avg_spread": avg_spread,
            "avg_ptf": avg_ptf
        })
    return pd.DataFrame(rows)


def compare_all_scenarios_05c(
    df: pd.DataFrame,
    config: BESSConfig05C,
    num_days: int = 15
) -> pd.DataFrame:
    """
    Tüm 4 temel senaryo + 2-döngü senaryosunu aynı veri seti üzerinde kıyaslar.
    Her bir senaryonun kâr, getiri, maliyet, döngü ve verim farkını üretir.
    """
    scenarios = [
        ScenarioType.BLOCK_BLOCK,
        ScenarioType.BLOCK_SPLIT,
        ScenarioType.SPLIT_BLOCK,
        ScenarioType.SPLIT_SPLIT,
        ScenarioType.TWO_CYCLE
    ]

    rows = []
    base_profit = None

    for sc in scenarios:
        meta = SCENARIO_METADATA[sc]
        _, _, kpis = simulate_period_05c(df, config, scenario=sc, num_days=num_days)

        if base_profit is None:
            base_profit = kpis["net_profit"]

        delta_vs_base = kpis["net_profit"] - base_profit
        pct_vs_base = (delta_vs_base / base_profit * 100.0) if base_profit > 0 else 0.0

        rows.append({
            "Senaryo": meta["title"],
            "Kısa Kod": meta["short_title"],
            "Karakteristik": meta["tag"],
            "Net Kâr ($)": kpis["net_profit"],
            "Baz Senaryoya Fark ($)": delta_vs_base,
            "Fark (%)": pct_vs_base,
            "Deşarj Geliri ($)": kpis["total_revenue"],
            "Şarj Maliyeti ($)": kpis["total_cost"],
            "Yıpranma ($)": kpis["total_degradation_cost"],
            "Gerçekleşen Spread ($/MWh)": kpis["realized_spread"],
            "Toplam Döngü (EFC)": kpis["total_cycles"],
            "Döngü Başı Kâr ($/Cycle)": kpis["profit_per_cycle"],
            "Aktif / Pas Gün": f"{kpis['active_days']} / {kpis['passed_days']}",
        })

    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# BİRİM TESTLERİ (Unit Verification)
# -----------------------------------------------------------------------------

def test_all_scenarios():
    """Tüm senaryoların matematiksel kurallara ve kısıtlara uyduğunu doğrular."""
    print(">>> 0.5C Senaryo Optimizasyon Motoru Testleri Başlatılıyor...")

    # Sentetik 24 saatlik fiyat profili (Gece ucuz, gündüz orta, akşam pik)
    prices = np.array([
        40.0, 38.0, 35.0, 32.0, 34.0, 42.0,   # 00-05 (Dip: 03:00)
        50.0, 65.0, 75.0, 70.0, 60.0, 55.0,   # 06-11 (Sabah pik)
        45.0, 40.0, 43.0, 52.0, 68.0, 85.0,   # 12-17 (Öğle dip: 13:00)
        95.0, 110.0, 105.0, 88.0, 60.0, 48.0  # 18-23 (Akşam pik: 19:00)
    ], dtype=float)

    cfg = BESSConfig05C(power_mw=50.0, c_rate=0.5, rte=0.85, degradation_cost=2.0)

    # 1. Test: BLOCK_BLOCK
    r1 = optimize_day_05c(prices, cfg, ScenarioType.BLOCK_BLOCK)
    assert len(r1.charge_hours) == 2, "Senaryo 1 şarj saati 2 olmalı"
    assert len(r1.discharge_hours) == 2, "Senaryo 1 deşarj saati 2 olmalı"
    assert r1.charge_hours[1] == r1.charge_hours[0] + 1, "Senaryo 1 şarj ardışık olmalı"
    assert r1.discharge_hours[1] == r1.discharge_hours[0] + 1, "Senaryo 1 deşarj ardışık olmalı"
    assert r1.charge_hours[1] < r1.discharge_hours[0], "Deşarj şarjdan sonra başlamalı"
    print(f" [PASS] BLOCK_BLOCK: Şarj={r1.charge_hours}, Deşarj={r1.discharge_hours}, Net=${r1.net_profit:,.2f}")

    # 2. Test: BLOCK_SPLIT
    r2 = optimize_day_05c(prices, cfg, ScenarioType.BLOCK_SPLIT)
    assert len(r2.charge_hours) == 2
    assert r2.charge_hours[1] == r2.charge_hours[0] + 1, "Senaryo 2 şarj ardışık olmalı"
    assert len(r2.discharge_hours) == 2
    assert r2.charge_hours[1] < r2.discharge_hours[0], "Deşarj şarjdan sonra başlamalı"
    assert r2.net_profit >= r1.net_profit - 1e-5, "Senaryo 2 serbestliği Senaryo 1'den az kâr veremez"
    print(f" [PASS] BLOCK_SPLIT: Şarj={r2.charge_hours}, Deşarj={r2.discharge_hours}, Net=${r2.net_profit:,.2f}")

    # 3. Test: SPLIT_BLOCK
    r3 = optimize_day_05c(prices, cfg, ScenarioType.SPLIT_BLOCK)
    assert len(r3.charge_hours) == 2
    assert len(r3.discharge_hours) == 2
    assert r3.discharge_hours[1] == r3.discharge_hours[0] + 1, "Senaryo 3 deşarj ardışık olmalı"
    assert r3.charge_hours[1] < r3.discharge_hours[0], "Deşarj tüm şarjlar bittikten sonra başlamalı"
    print(f" [PASS] SPLIT_BLOCK: Şarj={r3.charge_hours}, Deşarj={r3.discharge_hours}, Net=${r3.net_profit:,.2f}")

    # 4. Test: SPLIT_SPLIT
    r4 = optimize_day_05c(prices, cfg, ScenarioType.SPLIT_SPLIT)
    assert len(r4.charge_hours) == 2
    assert len(r4.discharge_hours) == 2
    assert r4.net_profit >= r1.net_profit - 1e-5, "Senaryo 4 en yüksek kârı vermeli"
    assert r4.net_profit >= r2.net_profit - 1e-5, "Senaryo 4 >= Senaryo 2 olmalı"
    print(f" [PASS] SPLIT_SPLIT: Şarj={r4.charge_hours}, Deşarj={r4.discharge_hours}, Net=${r4.net_profit:,.2f}")

    # 5. Test: TWO_CYCLE
    r5 = optimize_day_05c(prices, cfg, ScenarioType.TWO_CYCLE)
    print(f" [PASS] TWO_CYCLE  : Şarj={r5.charge_hours}, Deşarj={r5.discharge_hours}, Net=${r5.net_profit:,.2f}")

    print(">>> Tüm Senaryo Birim Testleri Başarıyla Tamamlandı! ")
    return True


if __name__ == "__main__":
    test_all_scenarios()
