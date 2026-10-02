"""
Doğrulama ve Birim Testleri: BESS Tam Blok Optimizasyonu, Yıpranma Maliyeti ve Metrikler
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from src.optimizer import BESSConfig, optimize_single_day, optimize_year
from src.metrics import compute_kpis, compute_monthly_breakdown


def test_single_day_synthetic():
    """Sentetik 24 saatlik veride Tam Blok 1C doğruluğu testi."""
    # 24 saatlik sentetik fiyat eğrisi:
    # 03:00'te 10 $/MWh, 19:00'da 100 $/MWh, diğer saatler 50 $/MWh
    prices = np.full(24, 50.0)
    prices[3] = 10.0
    prices[19] = 100.0

    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=0.0)
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["is_passed"] is False
    assert res["best_ch"] == 3
    assert res["best_dis"] == 19
    # Şarj 1 MWh, deşarj 0.85 MWh
    # Brüt kâr = (0.85 * 100) - (1.0 * 10) = 85 - 10 = 75
    assert abs(res["gross_profit"] - 75.0) < 1e-4
    assert abs(res["net_profit"] - 75.0) < 1e-4
    assert abs(res["cycles"] - 1.0) < 1e-4


def test_degradation_cost_skip_when_unprofitable():
    """Yıpranma maliyeti brüt kârı aştığında günün pas geçilmesi testi."""
    # 03:00'te 40 $/MWh, 19:00'da 60 $/MWh
    # Brüt kâr = (0.85 * 60) - (1.0 * 40) = 51 - 40 = 11 $/MWh
    prices = np.full(24, 50.0)
    prices[3] = 40.0
    prices[19] = 60.0

    # Yıpranma maliyeti = 15 $/MWh > 11 $/MWh -> Net kâr negatif olacağı için pas geçilmeli!
    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=15.0)
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["is_passed"] is True
    assert res["best_ch"] is None
    assert res["best_dis"] is None
    assert res["net_profit"] == 0.0
    assert res["gross_profit"] == 0.0
    assert res["degradation_cost"] == 0.0
    assert res["cycles"] == 0.0
    assert np.all(res["p_ch"] == 0.0)
    assert np.all(res["p_dis"] == 0.0)


def test_degradation_cost_deduction_when_profitable():
    """Yıpranma maliyeti brüt kârdan düşülüp net kârın pozitif kalması testi."""
    # 03:00'te 20 $/MWh, 19:00'da 100 $/MWh
    # Brüt kâr = (0.85 * 100) - (1.0 * 20) = 85 - 20 = 65 $/MWh
    prices = np.full(24, 50.0)
    prices[3] = 20.0
    prices[19] = 100.0

    # Yıpranma maliyeti = 20 $/MWh
    # Net kâr = 65 - 20 = 45 $/MWh
    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=20.0)
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["is_passed"] is False
    assert res["best_ch"] == 3
    assert res["best_dis"] == 19
    assert abs(res["gross_profit"] - 65.0) < 1e-4
    assert abs(res["degradation_cost"] - 20.0) < 1e-4
    assert abs(res["net_profit"] - 45.0) < 1e-4
    assert abs(res["cycles"] - 1.0) < 1e-4


def test_no_negative_days_in_metrics():
    """Yıllık veya aylık hesaplamalarda negatif günlerin asla kârı düşürmediği testi."""
    dates = pd.date_range("2024-01-01", periods=48, freq="h")
    # Gün 1: Kârlı (Spread = 80)
    # Gün 2: Kârsız (Spread = 5, yıpranma = 15)
    prices = np.full(48, 50.0)
    prices[3] = 10.0   # Gün 1 şarj
    prices[19] = 90.0  # Gün 1 deşarj -> Brüt = 0.85*90 - 10 = 66.5, Net = 66.5 - 15 = 51.5
    prices[24 + 3] = 48.0 # Gün 2 şarj
    prices[24 + 19] = 52.0 # Gün 2 deşarj -> Brüt = 0.85*52 - 48 = -3.8 <= 0 -> Pas!

    df = pd.DataFrame({
        "datetime": dates,
        "date": dates.normalize(),
        "month": dates.month,
        "day": dates.day,
        "hour": dates.hour,
        "ptf_usd": prices,
    })

    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=15.0)
    hourly_df, daily_df = optimize_year(df, config)
    kpis = compute_kpis(daily_df, {"power_mw": 1.0, "capacity_mwh": 1.0, "degradation_cost": 15.0})

    assert len(daily_df) == 2
    assert not daily_df.iloc[0]["is_passed"]
    assert daily_df.iloc[0]["net_profit"] > 0
    assert daily_df.iloc[1]["is_passed"]
    assert daily_df.iloc[1]["net_profit"] == 0.0

    # Net kâr sadece gün 1'in net kârına eşit olmalı, gün 2 negatiflik getirmemeli
    assert abs(kpis["net_profit"] - daily_df.iloc[0]["net_profit"]) < 1e-4
    assert kpis["active_days"] == 1
    assert kpis["passed_days"] == 1


if __name__ == "__main__":
    test_single_day_synthetic()
    test_degradation_cost_skip_when_unprofitable()
    test_degradation_cost_deduction_when_profitable()
    test_no_negative_days_in_metrics()
    print("Tüm birim testleri (Yıpranma Maliyeti & Pas Geçme) başarıyla geçti!")

