"""
BESS Feasibility and KPI Metrics Calculator
Computes annual, monthly, and daily metrics, cycling statistics, and executive summaries.
"""
from __future__ import annotations

from typing import Dict, Any, Union
import numpy as np
import pandas as pd


def compute_kpis(daily_df: pd.DataFrame, config_info: Dict[str, Any]) -> Dict[str, Any]:
    """Computes overall annual KPI summary."""
    total_revenue = float(daily_df["discharge_revenue"].sum())
    total_cost = float(daily_df["charge_cost"].sum())
    total_degradation_cost = float(daily_df["degradation_cost"].sum()) if "degradation_cost" in daily_df.columns else 0.0
    gross_profit = float(daily_df["gross_profit"].sum()) if "gross_profit" in daily_df.columns else float(total_revenue - total_cost)
    net_profit = float(daily_df["net_profit"].sum())
    total_cycles = float(daily_df["cycles"].sum())
    total_discharged_mwh = float(daily_df["discharged_mwh"].sum())
    total_charged_mwh = float(daily_df["charged_mwh"].sum())

    profit_per_cycle = (net_profit / total_cycles) if total_cycles > 0.01 else 0.0

    # Volume-weighted average charge and discharge prices
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
    """Computes monthly financial and operational breakdown table."""
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
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
    """Generates a clean, professional executive summary formatted for reports and executive sharing."""
    p_mw = kpis["power_mw"]
    cap_mwh = kpis["capacity_mwh"]
    c_rate = kpis["c_rate"]
    rte_pct = kpis["rte"] * 100.0
    deg_unit = kpis.get("degradation_cost_unit", 0.0)
    deg_total = kpis.get("total_degradation_cost", 0.0)
    gross_prof = kpis.get("gross_profit", kpis["net_profit"])
    passed_days = kpis.get("passed_days", 0)

    strat_text = "Up to 2 Cycles per Day (Dual Block)" if kpis.get("strategy") == "2_cycle" else "1C Arbitrage (Single Block / 1 Cycle per Day)"

    deg_line = ""
    if deg_unit > 0:
        deg_line = f"• 🛠️ Battery Degradation Cost: ${deg_unit:.1f}/MWh (Total: ${deg_total:,.2f})\n"

    summary = f"""⚡ **BESS (Battery Energy Storage System) Arbitrage Feasibility Analysis — {year} Real Market Results**

📌 **System Configuration:**
• Battery Power: {p_mw:,.1f} MW
• Storage Capacity: {cap_mwh:,.1f} MWh ({c_rate:.1f}C)
• Round-Trip Efficiency (RTE): %{rte_pct:.0f}
• Operational Strategy: {strat_text}
{deg_line}
📊 **{year} Annual Arbitrage Performance:**
• 🟢 Total Discharge Revenue: ${kpis['total_revenue']:,.2f}
• 🔴 Total Charge Cost: ${kpis['total_cost']:,.2f}
• 📈 Gross Arbitrage Profit: ${gross_prof:,.2f}
• 🛠️ Total Degradation Cost: ${deg_total:,.2f}
• 💰 **Net Arbitrage Profit:** **${kpis['net_profit']:,.2f}**
• 🔋 Total Equivalent Full Cycles (EFC): {kpis['total_cycles']:,.1f} Cycles
• 💎 **Net Profit per Cycle:** **${kpis['profit_per_cycle']:,.2f} / Cycle**
• 📈 Volume-Weighted Avg. Discharge Price: ${kpis['avg_discharge_price']:,.2f} / MWh
• 📉 Volume-Weighted Avg. Charge Price: ${kpis['avg_charge_price']:,.2f} / MWh
• 🎯 Annual Realized Price Spread: ${kpis['realized_spread']:,.2f} / MWh
• ⏱️ Active Operational Days: {kpis['active_days']} / {kpis['total_days']} days
• 🛡️ Standby Days (Unprofitable / Preserved): {passed_days} days

💡 **Key Takeaway:**
On negative-margin days where price spread does not clear charging efficiency losses and degradation costs, the battery remains on standby to protect capital and cell longevity. On profitable days, disciplined cycling achieves an average net profit of ${kpis['profit_per_cycle']:.2f} per equivalent full cycle.

#BESS #BatteryStorage #EnergyArbitrage #DayAheadMarket #CleanEnergy #PowerMarkets #EnergyEconomics
"""
    return summary
