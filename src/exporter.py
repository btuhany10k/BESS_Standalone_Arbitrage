"""
BESS 1C Arbitrage - Comprehensive Excel Report Generator
"""
from __future__ import annotations

import io
from typing import Dict, Any, Optional
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.optimizer import BESSConfig


def generate_bess_excel_report(
    year: int,
    config: BESSConfig,
    hourly_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    kpis: Dict[str, Any],
    monthly_df: pd.DataFrame,
    comp_df: Optional[pd.DataFrame] = None
) -> bytes:
    output = io.BytesIO()

    kpi_records = [
        {'Category': 'System Parameter', 'Parameter': 'Analysis Year', 'Value': str(year), 'Unit': 'Year'},
        {'Category': 'System Parameter', 'Parameter': 'Nominal Power', 'Value': f'{config.power_mw:.1f}', 'Unit': 'MW'},
        {'Category': 'System Parameter', 'Parameter': 'Storage Capacity', 'Value': f'{config.capacity_mwh:.1f}', 'Unit': 'MWh'},
        {'Category': 'System Parameter', 'Parameter': 'C-Rate', 'Value': f'{config.c_rate:.1f}C (1-Hour Duration)', 'Unit': 'C'},
        {'Category': 'System Parameter', 'Parameter': 'Round-Trip Efficiency (RTE)', 'Value': f'{config.rte * 100:.0f}%', 'Unit': '%'},
        {'Category': 'System Parameter', 'Parameter': 'Day-Start Initial SoC', 'Value': f'{config.soc_start_pct:.0f}%', 'Unit': '%'},
        {'Category': 'System Parameter', 'Parameter': 'Day-End Target SoC', 'Value': f'{config.soc_end_pct:.0f}%', 'Unit': '%'},
        {'Category': 'System Parameter', 'Parameter': 'Battery Degradation Cost', 'Value': f'${config.degradation_cost:.2f}', 'Unit': '$/MWh'},
        {'Category': 'System Parameter', 'Parameter': 'Operational Strategy', 'Value': 'Up to 2 Cycles per Day (Dual Block)' if getattr(config, 'strategy', '1_cycle') == '2_cycle' else '1C Arbitrage (Single Block / 1 Cycle per Day)', 'Unit': '-'},
        {'Category': 'Financial Results', 'Parameter': 'Total Discharge Revenue', 'Value': round(kpis['total_revenue'], 2), 'Unit': '$'},
        {'Category': 'Financial Results', 'Parameter': 'Total Charge Cost', 'Value': round(kpis['total_cost'], 2), 'Unit': '$'},
        {'Category': 'Financial Results', 'Parameter': 'Gross Arbitrage Profit', 'Value': round(kpis.get('gross_profit', kpis['total_revenue'] - kpis['total_cost']), 2), 'Unit': '$'},
        {'Category': 'Financial Results', 'Parameter': 'Total Degradation Cost', 'Value': round(kpis.get('total_degradation_cost', 0.0), 2), 'Unit': '$'},
        {'Category': 'Financial Results', 'Parameter': 'Net Arbitrage Profit', 'Value': round(kpis['net_profit'], 2), 'Unit': '$'},
        {'Category': 'Financial Results', 'Parameter': 'Average Daily Net Profit', 'Value': round(kpis['avg_daily_profit'], 2), 'Unit': '$/Day'},
        {'Category': 'Operational Metrics', 'Parameter': 'Total Equivalent Full Cycles', 'Value': round(kpis['total_cycles'], 1), 'Unit': 'Cycles (EFC)'},
        {'Category': 'Operational Metrics', 'Parameter': 'Net Profit per Cycle', 'Value': round(kpis['profit_per_cycle'], 2), 'Unit': '$/Cycle'},
        {'Category': 'Operational Metrics', 'Parameter': 'Active Operational Days', 'Value': kpis['active_days'], 'Unit': 'Days'},
        {'Category': 'Operational Metrics', 'Parameter': 'Standby Days (Unprofitable)', 'Value': kpis.get('passed_days', 0), 'Unit': 'Days'},
        {'Category': 'Operational Metrics', 'Parameter': 'Total Discharged Energy', 'Value': round(kpis['total_discharged_mwh'], 2), 'Unit': 'MWh'},
        {'Category': 'Operational Metrics', 'Parameter': 'Total Charged Energy', 'Value': round(kpis['total_charged_mwh'], 2), 'Unit': 'MWh'},
        {'Category': 'Market & Price Metrics', 'Parameter': 'Volume-Weighted Avg. Discharge Price', 'Value': round(kpis['avg_discharge_price'], 2), 'Unit': '$/MWh'},
        {'Category': 'Market & Price Metrics', 'Parameter': 'Volume-Weighted Avg. Charge Price', 'Value': round(kpis['avg_charge_price'], 2), 'Unit': '$/MWh'},
        {'Category': 'Market & Price Metrics', 'Parameter': 'Annual Realized Price Spread (Sale - Purchase)', 'Value': round(kpis['realized_spread'], 2), 'Unit': '$/MWh'},
    ]
    df_kpis = pd.DataFrame(kpi_records)

    hourly_clean = hourly_df.copy()
    def get_action_label(row):
        label = row.get('action_label')
        if label:
            label_map = {
                'Şarj': 'Charge', 'Sarj': 'Charge',
                'Deşarj': 'Discharge', 'Desarj': 'Discharge',
                'Şarj 1': 'Charge 1', 'Sarj 1': 'Charge 1',
                'Deşarj 1': 'Discharge 1', 'Desarj 1': 'Discharge 1',
                'Şarj 2': 'Charge 2', 'Sarj 2': 'Charge 2',
                'Deşarj 2': 'Discharge 2', 'Desarj 2': 'Discharge 2',
                'Pas Geçildi': 'Standby (Unprofitable)', 'Pas Gecildi': 'Standby (Unprofitable)',
                'Bekleme (Standby)': 'Standby (Idle)', 'Bekleme': 'Standby (Idle)'
            }
            return label_map.get(label, label)
        if row.get('is_charging', False):
            return 'Charge'
        elif row.get('is_discharging', False):
            return 'Discharge'
        elif row.get('is_passed', False):
            return 'Standby (Unprofitable)'
        return 'Standby (Idle)'

    hourly_clean['Operation Status'] = hourly_clean.apply(get_action_label, axis=1)
    if pd.api.types.is_datetime64_any_dtype(hourly_clean['date']):
        hourly_clean['Date'] = hourly_clean['date'].dt.strftime('%Y-%m-%d')
    else:
        hourly_clean['Date'] = hourly_clean['date'].astype(str)

    hourly_clean['Day-Ahead Price ($/MWh)'] = hourly_clean['ptf_usd'].round(2)
    hourly_clean['Charge Power (MW)'] = hourly_clean['p_ch_mw'].round(2)
    hourly_clean['Discharge Power (MW)'] = hourly_clean['p_dis_mw'].round(2)
    hourly_clean['Battery SoC (MWh)'] = hourly_clean['soc_mwh'].round(2)
    hourly_clean['Battery SoC (%)'] = hourly_clean['soc_pct'].round(1)
    hourly_clean['Charge Cost ($)'] = hourly_clean['charge_cost'].round(2)
    hourly_clean['Discharge Revenue ($)'] = hourly_clean['discharge_revenue'].round(2)
    hourly_clean['Degradation Cost ($)'] = hourly_clean['degradation_cost'].round(2)
    hourly_clean['Net Profit ($)'] = hourly_clean['net_profit'].round(2)

    hourly_export = hourly_clean[[
        'Date', 'saat_str', 'Day-Ahead Price ($/MWh)', 'Charge Power (MW)', 'Discharge Power (MW)',
        'Battery SoC (MWh)', 'Battery SoC (%)', 'Charge Cost ($)', 'Discharge Revenue ($)',
        'Degradation Cost ($)', 'Net Profit ($)', 'Operation Status'
    ]].copy()
    hourly_export.rename(columns={'saat_str': 'Hour'}, inplace=True)

    daily_clean = daily_df.copy()
    if pd.api.types.is_datetime64_any_dtype(daily_clean['date']):
        daily_clean['Date'] = daily_clean['date'].dt.strftime('%Y-%m-%d')
    else:
        daily_clean['Date'] = daily_clean['date'].astype(str)

    ch1_col = daily_clean['ch1_hour'] if 'ch1_hour' in daily_clean.columns else daily_clean['best_ch']
    dis1_col = daily_clean['dis1_hour'] if 'dis1_hour' in daily_clean.columns else daily_clean['best_dis']
    ch2_col = daily_clean['ch2_hour'] if 'ch2_hour' in daily_clean.columns else pd.Series([None] * len(daily_clean))
    dis2_col = daily_clean['dis2_hour'] if 'dis2_hour' in daily_clean.columns else pd.Series([None] * len(daily_clean))

    daily_clean['1st Charge Hour'] = ch1_col.apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['1st Discharge Hour'] = dis1_col.apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['2nd Charge Hour'] = ch2_col.apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['2nd Discharge Hour'] = dis2_col.apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['Operational Status'] = daily_clean['is_passed'].apply(
        lambda x: 'Standby (Skipped)' if x else 'Active Dispatch'
    )

    daily_clean['Min Price ($/MWh)'] = daily_clean['ptf_min'].round(2)
    daily_clean['Max Price ($/MWh)'] = daily_clean['ptf_max'].round(2)
    daily_clean['Avg Price ($/MWh)'] = daily_clean['ptf_avg'].round(2)
    daily_clean['Daily Price Spread ($/MWh)'] = daily_clean['ptf_spread'].round(2)
    daily_clean['Charged Energy (MWh)'] = daily_clean['charged_mwh'].round(2)
    daily_clean['Discharged Energy (MWh)'] = daily_clean['discharged_mwh'].round(2)
    daily_clean['Charge Cost ($)'] = daily_clean['charge_cost'].round(2)
    daily_clean['Discharge Revenue ($)'] = daily_clean['discharge_revenue'].round(2)
    daily_clean['Gross Profit ($)'] = daily_clean['gross_profit'].round(2)
    daily_clean['Degradation Cost ($)'] = daily_clean['degradation_cost'].round(2)
    daily_clean['Net Profit ($)'] = daily_clean['net_profit'].round(2)
    daily_clean['Cycles (EFC)'] = daily_clean['cycles'].round(2)
    daily_clean['Profit per Cycle ($/Cycle)'] = daily_clean['profit_per_cycle'].round(2)

    daily_export = daily_clean[[
        'Date', 'month', 'Min Price ($/MWh)', 'Max Price ($/MWh)', 'Avg Price ($/MWh)', 'Daily Price Spread ($/MWh)',
        '1st Charge Hour', '1st Discharge Hour', '2nd Charge Hour', '2nd Discharge Hour',
        'Charged Energy (MWh)', 'Discharged Energy (MWh)',
        'Charge Cost ($)', 'Discharge Revenue ($)', 'Gross Profit ($)', 'Degradation Cost ($)',
        'Net Profit ($)', 'Cycles (EFC)', 'Profit per Cycle ($/Cycle)', 'Operational Status'
    ]].copy()
    daily_export.rename(columns={'month': 'Month No'}, inplace=True)

    month_names_en = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }

    monthly_clean = monthly_df.copy()
    monthly_clean['Month No'] = monthly_clean['month']
    monthly_clean['Month'] = monthly_clean['month'].map(month_names_en)
    monthly_clean['Discharge Revenue ($)'] = monthly_clean['discharge_revenue'].round(2)
    monthly_clean['Charge Cost ($)'] = monthly_clean['charge_cost'].round(2)
    monthly_clean['Gross Arbitrage Profit ($)'] = monthly_clean['gross_profit'].round(2)
    monthly_clean['Degradation Cost ($)'] = monthly_clean['degradation_cost'].round(2)
    monthly_clean['Net Arbitrage Profit ($)'] = monthly_clean['net_profit'].round(2)
    monthly_clean['Total Cycles (EFC)'] = monthly_clean['cycles'].round(1)
    monthly_clean['Active Days'] = monthly_clean['active_days']
    monthly_clean['Standby Days'] = monthly_clean['passed_days']
    monthly_clean['Net Profit per Cycle ($/Cycle)'] = monthly_clean['profit_per_cycle'].round(2)
    monthly_clean['Discharged Energy (MWh)'] = monthly_clean['discharged_mwh'].round(2)
    monthly_clean['Charged Energy (MWh)'] = monthly_clean['charged_mwh'].round(2)
    monthly_clean['Avg Daily Spread ($/MWh)'] = monthly_clean['avg_spread'].round(2)
    if 'avg_ptf' in monthly_clean.columns:
        monthly_clean['Avg Market Price ($/MWh)'] = monthly_clean['avg_ptf'].round(2)
        cols_m = [
            'Month No', 'Month', 'Discharge Revenue ($)', 'Charge Cost ($)', 'Gross Arbitrage Profit ($)', 'Degradation Cost ($)',
            'Net Arbitrage Profit ($)', 'Total Cycles (EFC)', 'Active Days', 'Standby Days',
            'Net Profit per Cycle ($/Cycle)', 'Discharged Energy (MWh)', 'Charged Energy (MWh)', 'Avg Daily Spread ($/MWh)',
            'Avg Market Price ($/MWh)'
        ]
    else:
        cols_m = [
            'Month No', 'Month', 'Discharge Revenue ($)', 'Charge Cost ($)', 'Gross Arbitrage Profit ($)', 'Degradation Cost ($)',
            'Net Arbitrage Profit ($)', 'Total Cycles (EFC)', 'Active Days', 'Standby Days',
            'Net Profit per Cycle ($/Cycle)', 'Discharged Energy (MWh)', 'Charged Energy (MWh)', 'Avg Daily Spread ($/MWh)'
        ]

    monthly_export = monthly_clean[cols_m].copy()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_kpis.to_excel(writer, sheet_name='Summary & Parameters', index=False)
        monthly_export.to_excel(writer, sheet_name='Monthly Breakdown', index=False)
        daily_export.to_excel(writer, sheet_name='Daily Summary (365 Days)', index=False)
        hourly_export.to_excel(writer, sheet_name='Hourly Dispatch (8760 Hours)', index=False)
        if comp_df is not None and not comp_df.empty:
            comp_export = comp_df.copy()
            rename_map = {
                "Yıl": "Year",
                "Deşarj Geliri ($)": "Discharge Revenue ($)",
                "Şarj Maliyeti ($)": "Charge Cost ($)",
                "Brüt Kâr ($)": "Gross Profit ($)",
                "Yıpranma Maliyeti ($)": "Degradation Cost ($)",
                "Net Kâr ($)": "Net Profit ($)",
                "Döngü Sayısı (EFC)": "Total Cycles (EFC)",
                "Cycle Sayısı": "Total Cycles (EFC)",
                "Aktif Gün": "Active Days",
                "Pas Geçilen Gün": "Standby Days",
                "Döngü Başı Net Kâr ($/Döngü)": "Net Profit per Cycle ($/Cycle)",
                "Cycle Başı Kâr ($)": "Net Profit per Cycle ($/Cycle)",
                "Ort. Deşarj Fiyatı ($/MWh)": "Avg. Discharge Price ($/MWh)",
                "Ort. Şarj Fiyatı ($/MWh)": "Avg. Charge Price ($/MWh)",
                "Gerçekleşen Spread ($/MWh)": "Realized Spread ($/MWh)",
            }
            comp_export.rename(columns=rename_map, inplace=True)
            comp_export.to_excel(writer, sheet_name='2024 vs 2025 Comparison', index=False)

        header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        align_center = Alignment(horizontal='center', vertical='center')

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            ws.views.sheetView[0].showGridLines = True

            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = align_center

            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val = cell.value
                    if val is not None:
                        val_str = str(val)
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 13)

    return output.getvalue()
