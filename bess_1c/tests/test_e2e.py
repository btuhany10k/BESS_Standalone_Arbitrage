"""
Uçtan Uca (E2E) Kapsamlı Test Paketi
Tüm seçenekleri, hesaplamaları, sınır durumlarını ve Excel çıktısını test eder.
"""

import io
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import openpyxl

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.data_loader import load_all_ptf_data
from src.optimizer import BESSConfig, optimize_single_day, optimize_year
from src.metrics import compute_kpis, compute_monthly_breakdown, generate_linkedin_summary
from src.exporter import generate_bess_excel_report


def run_e2e_tests():
    print("=" * 60)
    print("🧪 BAŞLIYOR: Uçtan Uca (E2E) Kapsamlı Testler")
    print("=" * 60)

    # 1. VERİ BÜTÜNLÜĞÜ TESTLERİ
    print("\n--- 1. Veri Bütünlüğü Testi ---")
    data = load_all_ptf_data(root_dir)
    assert 2024 in data, "2024 verisi bulunamadı!"
    assert 2025 in data, "2025 verisi bulunamadı!"

    df_2024 = data[2024]
    df_2025 = data[2025]

    # 2024 artık yıl: 366 gün * 24 = 8784 saat
    assert len(df_2024) == 8784, f"2024 satır sayısı hatalı: {len(df_2024)} (beklenen: 8784)"
    assert df_2024["ptf_usd"].isna().sum() == 0, "2024'te NaN PTF değeri var!"

    # 2025 standart yıl: 365 gün * 24 = 8760 saat
    assert len(df_2025) == 8760, f"2025 satır sayısı hatalı: {len(df_2025)} (beklenen: 8760)"
    assert df_2025["ptf_usd"].isna().sum() == 0, "2025'te NaN PTF değeri var!"
    print("  ✅ 2024 (8,784 saat / 366 gün) ve 2025 (8,760 saat / 365 gün) veri setleri eksiksiz.")

    # 2. OPTİMİZASYON VE SINIR DURUM TESTLERİ
    print("\n--- 2. Optimizasyon & Sınır Durumları Testi ---")
    test_configs = [
        # (Ad, Power, C-Rate, RTE, SoC_start, SoC_end, DegCost, Strategy)
        ("Standart 1 MW", 1.0, 1.0, 0.85, 0.0, 0.0, 0.0, "1_cycle"),
        ("Maksimum Güç 150 MW", 150.0, 1.0, 0.85, 0.0, 0.0, 0.0, "1_cycle"),
        ("Minimum Güç 0.5 MW", 0.5, 1.0, 0.85, 0.0, 0.0, 0.0, "1_cycle"),
        ("Düşük RTE %70", 1.0, 1.0, 0.70, 0.0, 0.0, 0.0, "1_cycle"),
        ("Yüksek RTE %98", 1.0, 1.0, 0.98, 0.0, 0.0, 0.0, "1_cycle"),
        ("SoC Giriş %20 - Çıkış %20", 10.0, 1.0, 0.85, 20.0, 20.0, 0.0, "1_cycle"),
        ("SoC Giriş %10 - Çıkış %90", 10.0, 1.0, 0.85, 10.0, 90.0, 0.0, "1_cycle"),
        ("Orta Yıpranma Maliyeti $15/MWh", 1.0, 1.0, 0.85, 0.0, 0.0, 15.0, "1_cycle"),
        ("Yüksek Yıpranma Maliyeti $50/MWh", 1.0, 1.0, 0.85, 0.0, 0.0, 50.0, "1_cycle"),
        ("Aşırı Yıpranma (Tüm Günler Pas: $1000/MWh)", 1.0, 1.0, 0.85, 0.0, 0.0, 1000.0, "1_cycle"),
        ("2-Cycle Standart 1 MW", 1.0, 1.0, 0.85, 0.0, 0.0, 0.0, "2_cycle"),
        ("2-Cycle Orta Yıpranma $15/MWh", 1.0, 1.0, 0.85, 0.0, 0.0, 15.0, "2_cycle"),
        ("2-Cycle SoC %10 - %10 ($5 Deg)", 5.0, 1.0, 0.85, 10.0, 10.0, 5.0, "2_cycle"),
    ]

    for name, p_mw, c_r, rte, s_start, s_end, deg, strat in test_configs:
        cfg = BESSConfig(
            power_mw=p_mw,
            c_rate=c_r,
            rte=rte,
            soc_start_pct=s_start,
            soc_end_pct=s_end,
            degradation_cost=deg,
            strategy=strat,
        )
        hourly_df, daily_df = optimize_year(df_2025, cfg)
        kpis = compute_kpis(daily_df, {"power_mw": p_mw, "capacity_mwh": cfg.capacity_mwh, "rte": rte, "c_rate": c_r, "degradation_cost": deg, "strategy": strat})
        monthly_df = compute_monthly_breakdown(daily_df, cfg.capacity_mwh)

        # Doğrulama 1: Net kâr asla negatif olamaz
        assert (daily_df["net_profit"] >= -1e-6).all(), f"[{name}] Negatif net kâr içeren gün var!"

        # Doğrulama 2: Pas geçilen günlerde net_profit, gross_profit, degradation_cost, cycles = 0
        passed_mask = daily_df["is_passed"]
        if passed_mask.any():
            assert (daily_df.loc[passed_mask, "net_profit"] == 0.0).all(), f"[{name}] Pas geçilen gün kârı sıfır değil!"
            assert (daily_df.loc[passed_mask, "gross_profit"] == 0.0).all(), f"[{name}] Pas geçilen gün brüt kârı sıfır değil!"
            assert (daily_df.loc[passed_mask, "degradation_cost"] == 0.0).all(), f"[{name}] Pas geçilen gün yıpranması sıfır değil!"
            assert (daily_df.loc[passed_mask, "cycles"] == 0.0).all(), f"[{name}] Pas geçilen gün döngüsü sıfır değil!"

        # Doğrulama 3: Aktif günlerde net kâr > 0 ve kronolojik kural
        active_mask = ~daily_df["is_passed"]
        if active_mask.any():
            assert (daily_df.loc[active_mask, "net_profit"] > 0).all(), f"[{name}] Aktif gün kârı <= 0!"
            # 1. Döngü kronolojisi
            assert (daily_df.loc[active_mask, "ch1_hour"] < daily_df.loc[active_mask, "dis1_hour"]).all(), f"[{name}] 1. Şarj saati deşarj saatinden önce değil!"
            # 2. Döngü aktif olan günlerde kronoloji: ch1 < dis1 < ch2 < dis2
            two_cycle_mask = active_mask & (daily_df["cycles_count"] == 2)
            if two_cycle_mask.any():
                two_days = daily_df.loc[two_cycle_mask]
                assert (two_days["ch1_hour"] < two_days["dis1_hour"]).all()
                assert (two_days["dis1_hour"] < two_days["ch2_hour"]).all()
                assert (two_days["ch2_hour"] < two_days["dis2_hour"]).all()

        # Doğrulama 4: Aylık toplamlar ile Yıllık KPI toplamları tam uyuşmalı
        assert abs(monthly_df["net_profit"].sum() - kpis["net_profit"]) < 1e-4, f"[{name}] Aylık Net Kâr toplamı yıllık KPI ile uyuşmuyor!"
        assert abs(monthly_df["gross_profit"].sum() - kpis["gross_profit"]) < 1e-4, f"[{name}] Aylık Brüt Kâr toplamı yıllık KPI ile uyuşmuyor!"
        assert abs(monthly_df["degradation_cost"].sum() - kpis["total_degradation_cost"]) < 1e-4, f"[{name}] Aylık Yıpranma toplamı yıllık KPI ile uyuşmuyor!"
        assert abs(monthly_df["cycles"].sum() - kpis["total_cycles"]) < 1e-4, f"[{name}] Aylık Cycle toplamı yıllık KPI ile uyuşmuyor!"
        assert monthly_df["active_days"].sum() == kpis["active_days"], f"[{name}] Aylık aktif gün toplamı uyuşmuyor!"
        assert monthly_df["passed_days"].sum() == kpis["passed_days"], f"[{name}] Aylık pas gün toplamı uyuşmuyor!"

        # Doğrulama 5: LinkedIn metni üretimi hatasız olmalı (özellikle 0 cycle / tüm günler pas durumunda)
        summary = generate_linkedin_summary(2025, kpis)
        assert len(summary) > 50, f"[{name}] LinkedIn özeti oluşturulamadı!"
        assert "NaN" not in summary, f"[{name}] LinkedIn özetinde NaN var!"

        print(f"  ✅ Senaryo: '{name}' başarıyla doğrulandı. (Aktif: {kpis['active_days']}, Pas: {kpis['passed_days']}, Net Kâr: ${kpis['net_profit']:,.2f})")


    # 3. EXCEL RAPORLAMA TESTİ
    print("\n--- 3. Excel Raporlama & Şablon Testi ---")
    cfg_sample = BESSConfig(power_mw=5.0, c_rate=1.0, rte=0.85, soc_start_pct=10.0, soc_end_pct=10.0, degradation_cost=10.0)
    h_df, d_df = optimize_year(df_2025, cfg_sample)
    kpis_2025 = compute_kpis(d_df, {"power_mw": 5.0, "capacity_mwh": 5.0, "rte": 0.85, "c_rate": 1.0, "degradation_cost": 10.0})
    m_df = compute_monthly_breakdown(d_df, 5.0)

    # 2024 kıyaslama verisi
    _, d_df_24 = optimize_year(df_2024, cfg_sample)
    kpis_2024 = compute_kpis(d_df_24, {"power_mw": 5.0, "capacity_mwh": 5.0, "rte": 0.85, "c_rate": 1.0, "degradation_cost": 10.0})

    comp_df = pd.DataFrame([
        {
            "Yıl": "2024",
            "Deşarj Geliri ($)": kpis_2024["total_revenue"],
            "Şarj Maliyeti ($)": kpis_2024["total_cost"],
            "Brüt Kâr ($)": kpis_2024["gross_profit"],
            "Yıpranma Maliyeti ($)": kpis_2024["total_degradation_cost"],
            "Net Kâr ($)": kpis_2024["net_profit"],
            "Toplam Cycle": kpis_2024["total_cycles"],
            "Aktif Gün": kpis_2024["active_days"],
            "Pas Geçilen Gün": kpis_2024["passed_days"],
            "Ortalama Fiyat Makası ($/MWh)": kpis_2024["realized_spread"],
        },
        {
            "Yıl": "2025",
            "Deşarj Geliri ($)": kpis_2025["total_revenue"],
            "Şarj Maliyeti ($)": kpis_2025["total_cost"],
            "Brüt Kâr ($)": kpis_2025["gross_profit"],
            "Yıpranma Maliyeti ($)": kpis_2025["total_degradation_cost"],
            "Net Kâr ($)": kpis_2025["net_profit"],
            "Toplam Cycle": kpis_2025["total_cycles"],
            "Aktif Gün": kpis_2025["active_days"],
            "Pas Geçilen Gün": kpis_2025["passed_days"],
            "Ortalama Fiyat Makası ($/MWh)": kpis_2025["realized_spread"],
        }
    ])

    excel_bytes = generate_bess_excel_report(2025, cfg_sample, h_df, d_df, kpis_2025, m_df, comp_df)
    assert len(excel_bytes) > 10000, "Excel dosyası boyutu beklenenden küçük!"

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
    expected_sheets = ['Ozet ve Parametreler', 'Aylik Kirilim', 'Gunluk Ozet (365 Gun)', '8760 Saatlik Detay', '2024 vs 2025 Kiyaslama']
    assert wb.sheetnames == expected_sheets, f"Sayfa isimleri uyuşmuyor: {wb.sheetnames}"

    # 8760 saatlik sayfanın satır sayısı (başlık + 8760 = 8761 satır)
    ws_hourly = wb['8760 Saatlik Detay']
    assert ws_hourly.max_row == 8761, f"Saatlik detay satır sayısı hatalı: {ws_hourly.max_row} (beklenen: 8761)"

    # Günlük özet satır sayısı (başlık + 365 = 366 satır)
    ws_daily = wb['Gunluk Ozet (365 Gun)']
    assert ws_daily.max_row == 366, f"Günlük özet satır sayısı hatalı: {ws_daily.max_row} (beklenen: 366)"

    # Aylık kırılım satır sayısı (başlık + 12 = 13 satır)
    ws_monthly = wb['Aylik Kirilim']
    assert ws_monthly.max_row == 13, f"Aylık kırılım satır sayısı hatalı: {ws_monthly.max_row} (beklenen: 13)"

    print("  ✅ Excel dosyası başarıyla üretildi ve 5 sayfası tam satır sayısıyla doğrulandı.")

    # 4. 2024 ARTIK YIL İÇİN EXCEL TESTİ
    print("\n--- 4. 2024 Artık Yıl (8,784 saat / 366 gün) Excel Testi ---")
    h_df_24, d_df_24 = optimize_year(df_2024, cfg_sample)
    m_df_24 = compute_monthly_breakdown(d_df_24, 5.0)
    excel_2024_bytes = generate_bess_excel_report(2024, cfg_sample, h_df_24, d_df_24, kpis_2024, m_df_24, comp_df)
    wb_24 = openpyxl.load_workbook(io.BytesIO(excel_2024_bytes), data_only=True)
    ws_hourly_24 = wb_24['8760 Saatlik Detay']
    assert ws_hourly_24.max_row == 8785, f"2024 saatlik detay satır sayısı: {ws_hourly_24.max_row} (beklenen: 8785)"
    ws_daily_24 = wb_24['Gunluk Ozet (365 Gun)']
    assert ws_daily_24.max_row == 367, f"2024 günlük özet satır sayısı: {ws_daily_24.max_row} (beklenen: 367)"
    print("  ✅ 2024 Artık Yıl Excel çıktısı 8,784 saat ve 366 gün ile başarıyla doğrulandı.")

    print("\n" + "=" * 60)
    print("🎉 TÜM UÇTAN UCA TESTLER BAŞARIYLA GEÇTİ!")
    print("=" * 60)


if __name__ == "__main__":
    run_e2e_tests()
