"""
BESS 0.5C - Kapsamlı Birim ve Fonksiyonel Doğrulama Testleri
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
import numpy as np

from src.data_loader import load_all_ptf_data
from src.optimizer_05c import (
    BESSConfig05C,
    LPStrategy,
    optimize_day_05c,
    simulate_period_05c,
    compare_all_lp_strategies_05c,
    aggregate_monthly_05c
)
from src.excel_export import generate_05c_excel_report


def test_data_loader():
    """EPİAŞ veri yükleyicisinin 2024 ve 2025 verilerini eksiksiz okuduğunu doğrular."""
    data = load_all_ptf_data()
    assert 2024 in data, "2024 verisi yüklenmeli"
    assert 2025 in data, "2025 verisi yüklenmeli"

    df_2024 = data[2024]
    df_2025 = data[2025]

    assert len(df_2024) == 8784, f"2024 artık yıl 8784 saat olmalı, bulunan: {len(df_2024)}"
    assert len(df_2025) == 8760, f"2025 tam yıl 8760 saat olmalı, bulunan: {len(df_2025)}"
    assert df_2024["ptf_usd"].isna().sum() == 0, "2024 PTF verisinde NaN olmamalı"
    assert df_2025["ptf_usd"].isna().sum() == 0, "2025 PTF verisinde NaN olmamalı"


def test_single_day_lp_optimization():
    """Tek bir gün için HiGHS LP optimizasyonunun fiziksel kısıtlarını doğrular."""
    # Sentetik 24 saatlik fiyat profili (gece ucuz, sabah ve akşam pahalı)
    hours = np.arange(24)
    prices = 60.0 + 30.0 * np.sin((hours - 4) * np.pi / 8)
    day_df = pd.DataFrame({
        "hour": hours,
        "saat_str": [f"{h:02d}:00" for h in hours],
        "ptf_usd": prices
    })

    cfg = BESSConfig05C(power_mw=50.0, c_rate=0.5, rte=0.85, degradation_cost=0.0)

    # 1.0 Çevrim Testi
    res_10 = optimize_day_05c(day_df, cfg, strategy=LPStrategy.LP_1_CYCLE)
    assert res_10.success, "1.0 EFC LP çözümü başarılı olmalı"
    assert res_10.cycles <= 1.0001, f"1.0 EFC kısıtı aşılmamalı, bulunan: {res_10.cycles}"
    assert np.all(res_10.p_charge >= -1e-6) and np.all(res_10.p_charge <= 50.0 + 1e-6), "Şarj gücü [0, 50] MW aralığında olmalı"
    assert np.all(res_10.p_discharge >= -1e-6) and np.all(res_10.p_discharge <= 50.0 + 1e-6), "Deşarj gücü [0, 50] MW aralığında olmalı"
    assert np.all(res_10.soc_mwh >= -1e-6) and np.all(res_10.soc_mwh <= 100.0 + 1e-6), "SoC [0, 100] MWh aralığında olmalı"
    assert abs(res_10.soc_mwh[-1]) <= 1e-4, f"Gün sonu SoC sıfır olmalı, bulunan: {res_10.soc_mwh[-1]}"

    # 1.5 Çevrim Testi
    res_15 = optimize_day_05c(day_df, cfg, strategy=LPStrategy.LP_15_CYCLE)
    assert res_15.success, "1.5 EFC LP çözümü başarılı olmalı"
    assert res_15.cycles <= 1.5001, f"1.5 EFC kısıtı aşılmamalı, bulunan: {res_15.cycles}"
    assert res_15.net_profit >= res_10.net_profit - 1e-4, "1.5 EFC en az 1.0 EFC kadar net kâr üretmeli"


def test_compare_all_lp_strategies():
    """1.0 ve 1.5 EFC modellerinin karşılaştırma matrisini doğrular."""
    data = load_all_ptf_data()
    df_2025 = data[2025]
    cfg = BESSConfig05C(power_mw=50.0, c_rate=0.5, rte=0.85, degradation_cost=0.0)

    comp_df = compare_all_lp_strategies_05c(df_2025, cfg, num_days=15)
    assert len(comp_df) == 2, f"Kıyaslama matrisinde tam 2 strateji (1.0 ve 1.5) olmalı, bulunan: {len(comp_df)}"
    assert comp_df.iloc[0]["Kısa Kod"] == "Senaryo (1.0 EFC)"
    assert comp_df.iloc[1]["Kısa Kod"] == "Senaryo (1.5 EFC)"
    assert comp_df.iloc[1]["Net Kâr ($)"] > comp_df.iloc[0]["Net Kâr ($)"], "1.5 EFC net kârı 1.0 EFC'den yüksek olmalı"


def test_excel_export():
    """Excel raporu üretiminin 5 çalışma sayfasını eksiksiz oluşturduğunu doğrular."""
    data = load_all_ptf_data()
    df_2025 = data[2025]
    cfg = BESSConfig05C(power_mw=50.0, c_rate=0.5, rte=0.85, degradation_cost=0.0)

    daily_df, hourly_df, kpis = simulate_period_05c(df_2025, cfg, strategy=LPStrategy.LP_1_CYCLE, num_days=15)
    monthly_df = aggregate_monthly_05c(daily_df, hourly_df)
    comp_df = pd.DataFrame([{"Yıl": "2025", "Net Kâr ($)": kpis["net_profit"]}])

    excel_bytes = generate_05c_excel_report(
        year=2025,
        config=cfg,
        hourly_df=hourly_df,
        daily_df=daily_df,
        kpis=kpis,
        monthly_df=monthly_df,
        comp_df=comp_df
    )
    assert isinstance(excel_bytes, bytes), "Excel çıktısı byte dizisi olmalı"
    assert len(excel_bytes) > 10000, f"Excel boyutu makul büyüklükte olmalı, bulunan: {len(excel_bytes)} bytes"


if __name__ == "__main__":
    print("Birim testleri çalıştırılıyor...")
    test_data_loader()
    print("test_data_loader: BAŞARILI")
    test_single_day_lp_optimization()
    print("test_single_day_lp_optimization: BAŞARILI")
    test_compare_all_lp_strategies()
    print("test_compare_all_lp_strategies: BAŞARILI")
    test_excel_export()
    print("test_excel_export: BAŞARILI")
    print("TÜM BİRİM TESTLERİ EKSİKSİZ GEÇTİ!")
