import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import time
from src.optimizer_05c import simulate_period_05c, compare_all_lp_strategies_05c, BESSConfig05C, LPStrategy
from src.data_loader import load_all_ptf_data


def test_full_year_optimization():
    data = load_all_ptf_data()
    print("Veri Kümeleri Yüklendi:")
    for yr, df in data.items():
        print(f"  {yr}: {len(df)} saat, {df['date'].nunique()} gün")

    cfg = BESSConfig05C(power_mw=50.0, rte=0.85, degradation_cost=0.0)

    for year in [2024, 2025]:
        df_yr = data.get(year)
        assert df_yr is not None, f"{year} verisi bulunamadı!"
        print(f"\n==========================================")
        print(f"YIL {year} LP TÜM YIL ÇÖZÜMÜ BAŞLIYOR...")
        print(f"==========================================")

        t0 = time.time()
        d_10, h_10, kpis_10 = simulate_period_05c(df_yr, cfg, strategy=LPStrategy.LP_1_CYCLE, num_days=None)
        t_10 = time.time() - t0

        t1 = time.time()
        d_15, h_15, kpis_15 = simulate_period_05c(df_yr, cfg, strategy=LPStrategy.LP_15_CYCLE, num_days=None)
        t_15 = time.time() - t1

        delta_profit = kpis_15["net_profit"] - kpis_10["net_profit"]
        pct_profit = (delta_profit / kpis_10["net_profit"]) * 100.0 if kpis_10["net_profit"] > 0 else 0.0

        print(f"[1.0 EFC] Net Kâr: ${kpis_10['net_profit']:,.2f} | Çevrim: {kpis_10['total_cycles']:.1f} EFC | Çözüm Süresi: {t_10:.2f}s")
        print(f"[1.5 EFC] Net Kâr: ${kpis_15['net_profit']:,.2f} | Çevrim: {kpis_15['total_cycles']:.1f} EFC | Çözüm Süresi: {t_15:.2f}s")
        print(f"[FARK] Net Kâr Artışı: +${delta_profit:,.2f} (+%{pct_profit:.2f}) | Ek Döngü: +{kpis_15['total_cycles'] - kpis_10['total_cycles']:.1f} EFC")

        assert kpis_10["net_profit"] > 0, "1.0 EFC net kâr pozitif olmalıdır"
        assert kpis_15["net_profit"] >= kpis_10["net_profit"], "1.5 EFC en az 1.0 EFC kadar kâr üretmelidir"
        assert len(d_10) == df_yr["date"].nunique(), f"Gün sayısı eşleşmeli: {len(d_10)}"

    print("\nTÜM YIL DOĞRULAMA TESTLERİ BAŞARIYLA TAMAMLANDI!")


if __name__ == "__main__":
    test_full_year_optimization()
