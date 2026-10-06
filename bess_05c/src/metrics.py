"""
BESS 0.5C - Metrikler, Karşılaştırma Matrisleri ve Finansal Hesaplamalar
İş mantığını arayüz katmanından (UI) tamamen izole eder.
"""

from typing import Dict, Any, Tuple
import pandas as pd
from src.optimizer_05c import LPStrategy, LP_STRATEGY_METADATA


def build_strategy_comparison_table(
    kpis_10: Dict[str, Any],
    kpis_15: Dict[str, Any]
) -> pd.DataFrame:
    """1.0 Döngü ile 1.5 Döngü senaryolarının başa-baş kıyaslama matrisini üretir."""
    delta_15_vs_10 = kpis_15["net_profit"] - kpis_10["net_profit"]
    pct_15_vs_10 = (delta_15_vs_10 / kpis_10["net_profit"] * 100.0) if kpis_10["net_profit"] > 0 else 0.0

    meta_10 = LP_STRATEGY_METADATA[LPStrategy.LP_1_CYCLE]
    meta_15 = LP_STRATEGY_METADATA[LPStrategy.LP_15_CYCLE]

    return pd.DataFrame([
        {
            "Strateji": meta_10["title"],
            "Kısa Kod": meta_10["short_title"],
            "Karakteristik": meta_10["tag"],
            "Net Kâr ($)": kpis_10["net_profit"],
            "1.0 Döngüye Göre Fark ($)": 0.0,
            "Fark (%)": 0.0,
            "Deşarj Geliri ($)": kpis_10["total_revenue"],
            "Şarj Maliyeti ($)": kpis_10["total_cost"],
            "Yıpranma ($)": kpis_10["total_degradation_cost"],
            "Gerçekleşen Spread ($/MWh)": kpis_10["realized_spread"],
            "Toplam Döngü (EFC)": kpis_10["total_cycles"],
            "Döngü Başı Kâr ($/Cycle)": kpis_10["profit_per_cycle"],
            "Kısmi Güç Saatleri": kpis_10["total_fractional_hours"],
            "Aktif / Pas Gün": f"{kpis_10['active_days']} / {kpis_10['passed_days']}",
        },
        {
            "Strateji": meta_15["title"],
            "Kısa Kod": meta_15["short_title"],
            "Karakteristik": meta_15["tag"],
            "Net Kâr ($)": kpis_15["net_profit"],
            "1.0 Döngüye Göre Fark ($)": delta_15_vs_10,
            "Fark (%)": pct_15_vs_10,
            "Deşarj Geliri ($)": kpis_15["total_revenue"],
            "Şarj Maliyeti ($)": kpis_15["total_cost"],
            "Yıpranma ($)": kpis_15["total_degradation_cost"],
            "Gerçekleşen Spread ($/MWh)": kpis_15["realized_spread"],
            "Toplam Döngü (EFC)": kpis_15["total_cycles"],
            "Döngü Başı Kâr ($/Cycle)": kpis_15["profit_per_cycle"],
            "Kısmi Güç Saatleri": kpis_15["total_fractional_hours"],
            "Aktif / Pas Gün": f"{kpis_15['active_days']} / {kpis_15['passed_days']}",
        }
    ])


def build_yearly_comparison_table(
    kpis_2024: Dict[str, Any],
    kpis_2025: Dict[str, Any]
) -> pd.DataFrame:
    """2024 ve 2025 yıllarının yıllık performans tablosunu üretir."""
    return pd.DataFrame([
        {
            "Yıl": "2024 (Artık Yıl)",
            "Deşarj Geliri ($)": kpis_2024["total_revenue"],
            "Şarj Maliyeti ($)": kpis_2024["total_cost"],
            "Brüt Kâr ($)": kpis_2024["gross_profit"],
            "Yıpranma Maliyeti ($)": kpis_2024["total_degradation_cost"],
            "Net Kâr ($)": kpis_2024["net_profit"],
            "Döngü Sayısı (EFC)": kpis_2024["total_cycles"],
            "Aktif Gün": kpis_2024["active_days"],
            "Pas Geçilen Gün": kpis_2024["passed_days"],
            "Döngü Başı Kâr ($)": kpis_2024["profit_per_cycle"],
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
            "Döngü Sayısı (EFC)": kpis_2025["total_cycles"],
            "Aktif Gün": kpis_2025["active_days"],
            "Pas Geçilen Gün": kpis_2025["passed_days"],
            "Döngü Başı Kâr ($)": kpis_2025["profit_per_cycle"],
            "Ort. Deşarj Fiyatı ($/MWh)": kpis_2025["avg_discharge_price"],
            "Ort. Şarj Fiyatı ($/MWh)": kpis_2025["avg_charge_price"],
            "Gerçekleşen Spread ($/MWh)": kpis_2025["realized_spread"],
        }
    ])
