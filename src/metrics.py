"""
BESS Fizibilite ve KPI Metrik Hesaplayıcı
Yıllık, aylık ve günlük metrikleri, cycle istatistiklerini ve LinkedIn özetini hazırlar.
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_kpis(daily_df: pd.DataFrame, config_info: Dict[str, Any]) -> Dict[str, Any]:
    """Yıllık genel KPI özetini hesaplar."""
    total_revenue = float(daily_df["discharge_revenue"].sum())
    total_cost = float(daily_df["charge_cost"].sum())
    total_degradation_cost = float(daily_df["degradation_cost"].sum()) if "degradation_cost" in daily_df.columns else 0.0
    gross_profit = float(daily_df["gross_profit"].sum()) if "gross_profit" in daily_df.columns else float(total_revenue - total_cost)
    net_profit = float(daily_df["net_profit"].sum())
    total_cycles = float(daily_df["cycles"].sum())
    total_discharged_mwh = float(daily_df["discharged_mwh"].sum())
    total_charged_mwh = float(daily_df["charged_mwh"].sum())

    profit_per_cycle = (net_profit / total_cycles) if total_cycles > 0.01 else 0.0

    # Ağırlıklı ortalama şarj ve deşarj fiyatı
    avg_discharge_price = (total_revenue / total_discharged_mwh) if total_discharged_mwh > 0 else 0.0
    avg_charge_price = (total_cost / total_charged_mwh) if total_charged_mwh > 0 else 0.0
    realized_spread = avg_discharge_price - avg_charge_price

    total_days = len(daily_df)
    active_days = int((daily_df["cycles"] > 0.01).sum())
    passed_days = total_days - active_days

    avg_daily_profit = net_profit / total_days if total_days > 0 else 0.0
    avg_daily_cycles = total_cycles / total_days if total_days > 0 else 0.0

    return {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "total_degradation_cost": total_degradation_cost,
        "net_profit": net_profit,
        "total_cycles": total_cycles,
        "profit_per_cycle": profit_per_cycle,
        "total_discharged_mwh": total_discharged_mwh,
        "total_charged_mwh": total_charged_mwh,
        "avg_discharge_price": avg_discharge_price,
        "avg_charge_price": avg_charge_price,
        "realized_spread": realized_spread,
        "total_days": total_days,
        "active_days": active_days,
        "passed_days": passed_days,
        "avg_daily_profit": avg_daily_profit,
        "avg_daily_cycles": avg_daily_cycles,
        "power_mw": config_info.get("power_mw", 1.0),
        "capacity_mwh": config_info.get("capacity_mwh", 1.0),
        "c_rate": config_info.get("c_rate", 1.0),
        "rte": config_info.get("rte", 0.85),
        "degradation_cost_unit": config_info.get("degradation_cost", 0.0),
        "strategy": config_info.get("strategy", "1_cycle"),
    }


def compute_monthly_breakdown(daily_df: pd.DataFrame, capacity_mwh: float) -> pd.DataFrame:
    """Aylık kırılım tablosunu üretir."""
    month_names = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }

    agg_dict = {
        "discharge_revenue": "sum",
        "charge_cost": "sum",
        "net_profit": "sum",
        "cycles": "sum",
        "discharged_mwh": "sum",
        "charged_mwh": "sum",
        "ptf_spread": "mean",
    }
    if "ptf_avg" in daily_df.columns:
        agg_dict["ptf_avg"] = "mean"
    if "gross_profit" in daily_df.columns:
        agg_dict["gross_profit"] = "sum"
    if "degradation_cost" in daily_df.columns:
        agg_dict["degradation_cost"] = "sum"

    monthly = daily_df.groupby("month").agg(agg_dict).reset_index()

    # Aktif ve pas geçilen gün sayıları
    active_days_per_month = daily_df[daily_df["cycles"] > 0.01].groupby("month")["date"].count()
    total_days_per_month = daily_df.groupby("month")["date"].count()

    monthly["active_days"] = monthly["month"].map(active_days_per_month).fillna(0).astype(int)
    monthly["total_days"] = monthly["month"].map(total_days_per_month).fillna(0).astype(int)
    monthly["passed_days"] = monthly["total_days"] - monthly["active_days"]

    if "gross_profit" not in monthly.columns:
        monthly["gross_profit"] = monthly["discharge_revenue"] - monthly["charge_cost"]
    if "degradation_cost" not in monthly.columns:
        monthly["degradation_cost"] = 0.0

    monthly["month_name"] = monthly["month"].map(month_names)
    monthly["profit_per_cycle"] = np.where(
        monthly["cycles"] > 0.01,
        monthly["net_profit"] / monthly["cycles"],
        0.0
    )
    monthly["avg_spread"] = monthly["ptf_spread"]
    monthly["avg_ptf"] = monthly["ptf_avg"] if "ptf_avg" in monthly.columns else 0.0

    cols = [
        "month", "month_name", "discharge_revenue", "charge_cost",
        "gross_profit", "degradation_cost", "net_profit", "cycles",
        "active_days", "passed_days", "profit_per_cycle", "discharged_mwh", "charged_mwh", "avg_spread", "avg_ptf"
    ]
    return monthly[cols]


def generate_linkedin_summary(year: int, kpis: Dict[str, Any]) -> str:
    """LinkedIn gönderisi için temiz, profesyonel bir özet metni oluşturur."""
    p_mw = kpis["power_mw"]
    cap_mwh = kpis["capacity_mwh"]
    c_rate = kpis["c_rate"]
    rte_pct = kpis["rte"] * 100.0
    deg_unit = kpis.get("degradation_cost_unit", 0.0)
    deg_total = kpis.get("total_degradation_cost", 0.0)
    gross_prof = kpis.get("gross_profit", kpis["net_profit"])
    passed_days = kpis.get("passed_days", 0)

    strat_text = "Günde 2 Döngüye Kadar Arbitraj (Çift Blok)" if kpis.get("strategy") == "2_cycle" else "1C Arbitraj (Günde En Kârlı 1 Şarj / 1 Deşarj)"

    deg_line = ""
    if deg_unit > 0:
        deg_line = f"• 🛠️ Yıpranma Maliyeti Parametresi: ${deg_unit:.1f}/MWh (Toplam: ${deg_total:,.2f})\n"

    summary = f"""⚡ **BESS (Batarya Enerji Depolama) Arbitraj Fizibilite Analizi — {year} Yılı Gerçek PTF Sonuçları**

📌 **Sistem Konfigürasyonu:**
• Batarya Gücü: {p_mw:,.1f} MW
• Depolama Kapasitesi: {cap_mwh:,.1f} MWh ({c_rate:.1f}C)
• Çevrim Verimliliği (RTE): %{rte_pct:.0f}
• Operasyon Stratejisi: {strat_text}
{deg_line}
📊 **{year} Yılı Yıllık Arbitraj Performansı:**
• 🟢 Toplam Deşarj Geliri: ${kpis['total_revenue']:,.2f}
• 🔴 Toplam Şarj Maliyeti: ${kpis['total_cost']:,.2f}
• 📈 Brüt Arbitraj Kârı: ${gross_prof:,.2f}
• 🛠️ Toplam Yıpranma Maliyeti: ${deg_total:,.2f}
• 💰 **Net Arbitraj Kârı:** **${kpis['net_profit']:,.2f}**
• 🔋 Toplam Yapılan Cycle: {kpis['total_cycles']:,.1f} Cycle
• 💎 **Cycle Başı Net Kâr:** **${kpis['profit_per_cycle']:,.2f} / Cycle**
• 📈 Ağırlıklı Ort. Deşarj Fiyatı: ${kpis['avg_discharge_price']:,.2f} / MWh
• 📉 Ağırlıklı Ort. Şarj Fiyatı: ${kpis['avg_charge_price']:,.2f} / MWh
• 🎯 Gerçekleşen Net Fiyat Spreadi: ${kpis['realized_spread']:,.2f} / MWh
• ⏱️ Aktif Çalışılan Gün: {kpis['active_days']} / {kpis['total_days']} gün
• 🛡️ Kârsız Olduğu İçin Pas Geçilen Gün: {passed_days} gün

💡 **Çıkarım:**
Fiyat spreadinin şarj ve yıpranma maliyetini karşılamadığı negatif günlerde batarya pas geçilerek (çalıştırılmayarak) sermaye korunmuş, kârlı günlerde arbitraj döngüsü ile cycle başına ortalama ${kpis['profit_per_cycle']:.2f} net kâr elde edilmiştir.

#BESS #EnerjiDepolama #PTF #EPİAŞ #Arbitraj #YenilenebilirEnerji #BatteryStorage #EnergyArbitrage
"""
    return summary
