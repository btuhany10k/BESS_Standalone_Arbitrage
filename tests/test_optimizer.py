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


def test_two_cycle_synthetic_after_window():
    """2. döngünün 1. döngüden SONRA yer aldığı çift pik senaryosu."""
    prices = np.full(24, 40.0)
    # 1. Döngü (en yüksek spread): 03:00 şarj (10 $), 11:00 deşarj (100 $)
    prices[3] = 10.0
    prices[11] = 100.0
    # 2. Döngü (öğleden sonra): 14:00 şarj (20 $), 20:00 deşarj (80 $)
    prices[14] = 20.0
    prices[20] = 80.0

    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=0.0, strategy="2_cycle")
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["is_passed"] is False
    assert res["cycles_count"] == 2
    assert res["ch1_hour"] == 3
    assert res["dis1_hour"] == 11
    assert res["ch2_hour"] == 14
    assert res["dis2_hour"] == 20
    # Kronolojik sıra: 3 < 11 < 14 < 20
    assert res["ch1_hour"] < res["dis1_hour"] < res["ch2_hour"] < res["dis2_hour"]
    # 1. döngü net = 0.85*100 - 10 = 75
    # 2. döngü net = 0.85*80 - 20 = 48
    # Toplam net = 75 + 48 = 123
    assert abs(res["net_profit"] - 123.0) < 1e-4
    assert abs(res["cycles"] - 2.0) < 1e-4


def test_two_cycle_synthetic_before_window():
    """2. döngünün 1. döngüden ÖNCE yer aldığı çift pik senaryosu ve kronolojik etiketleme."""
    prices = np.full(24, 40.0)
    # 1. Döngü (akşam en yüksek spread): 13:00 şarj (10 $), 20:00 deşarj (100 $) -> Net = 75
    prices[13] = 10.0
    prices[20] = 100.0
    # 2. Döngü (sabah): 02:00 şarj (15 $), 08:00 deşarj (75 $) -> Net = 0.85*75 - 15 = 48.75
    prices[2] = 15.0
    prices[8] = 75.0

    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=0.0, strategy="2_cycle")
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["cycles_count"] == 2
    # Kronolojik sıralama kuralı: Günün ilk olayı Şarj 1 / Deşarj 1 olmalı
    assert res["ch1_hour"] == 2
    assert res["dis1_hour"] == 8
    assert res["ch2_hour"] == 13
    assert res["dis2_hour"] == 20
    assert res["ch1_hour"] < res["dis1_hour"] < res["ch2_hour"] < res["dis2_hour"]
    assert abs(res["net_profit"] - (75.0 + 48.75)) < 1e-4
    assert abs(res["cycles"] - 2.0) < 1e-4


def test_two_cycle_skip_when_second_cycle_unprofitable():
    """2. döngü yıpranma maliyetini kurtarmadığında sadece 1. döngünün yapılması testi."""
    prices = np.full(24, 50.0)
    # 1. Döngü: 03:00 (10 $), 19:00 (100 $) -> Brüt = 75, Net = 75 - 15 = 60 > 0
    prices[3] = 10.0
    prices[19] = 100.0
    # Potansiyel 2. aralık (21:00-23:00): 21:00 (50 $), 23:00 (60 $) -> Brüt = 0.85*60 - 50 = 1 $ < Yıpranma (15 $)
    prices[21] = 50.0
    prices[23] = 60.0

    config = BESSConfig(power_mw=1.0, c_rate=1.0, rte=0.85, degradation_cost=15.0, strategy="2_cycle")
    res = optimize_single_day(prices, config)

    assert res["success"] is True
    assert res["is_passed"] is False
    assert res["cycles_count"] == 1
    assert res["ch1_hour"] == 3
    assert res["dis1_hour"] == 19
    assert res["ch2_hour"] is None
    assert res["dis2_hour"] is None
    assert abs(res["net_profit"] - 60.0) < 1e-4
    assert abs(res["cycles"] - 1.0) < 1e-4


if __name__ == "__main__":
    test_single_day_synthetic()
    test_degradation_cost_skip_when_unprofitable()
    test_degradation_cost_deduction_when_profitable()
    test_no_negative_days_in_metrics()
    test_two_cycle_synthetic_after_window()
    test_two_cycle_synthetic_before_window()
    test_two_cycle_skip_when_second_cycle_unprofitable()
    print("Tüm birim testleri (1C, 2C, Yıpranma Maliyeti & Kronolojik Kurallar) başarıyla geçti!")

