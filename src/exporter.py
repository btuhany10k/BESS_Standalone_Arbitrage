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
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Analiz Yili', 'Deger': str(year), 'Birim': 'Yil'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Nominal Guc', 'Deger': f'{config.power_mw:.1f}', 'Birim': 'MW'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Depolama Kapasitesi', 'Deger': f'{config.capacity_mwh:.1f}', 'Birim': 'MWh'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'C-Rate', 'Deger': f'{config.c_rate:.1f}C (1 Saat)', 'Birim': 'C'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Cevrim Verimliligi (RTE)', 'Deger': f'%{config.rte * 100:.0f}', 'Birim': '%'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Gune Baslangic SoC', 'Deger': f'%{config.soc_start_pct:.0f}', 'Birim': '%'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Gun Sonu Hedef SoC', 'Deger': f'%{config.soc_end_pct:.0f}', 'Birim': '%'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Yıpranma Maliyeti', 'Deger': f'${config.degradation_cost:.2f}', 'Birim': '$/MWh'},
        {'Kategori': 'Sistem Parametresi', 'Parametre': 'Operasyon Stratejisi', 'Deger': '1C Arbitraj', 'Birim': '-'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Toplam Desarj Geliri', 'Deger': round(kpis['total_revenue'], 2), 'Birim': '$'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Toplam Sarj Maliyeti', 'Deger': round(kpis['total_cost'], 2), 'Birim': '$'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Brut Arbitraj Kari', 'Deger': round(kpis.get('gross_profit', kpis['total_revenue'] - kpis['total_cost']), 2), 'Birim': '$'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Toplam Yipranma Maliyeti', 'Deger': round(kpis.get('total_degradation_cost', 0.0), 2), 'Birim': '$'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Net Arbitraj Kari', 'Deger': round(kpis['net_profit'], 2), 'Birim': '$'},
        {'Kategori': 'Finansal Sonuclar', 'Parametre': 'Gunluk Ortalama Net Kar', 'Deger': round(kpis['avg_daily_profit'], 2), 'Birim': '$/Gun'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Toplam Yapilan Cycle', 'Deger': round(kpis['total_cycles'], 1), 'Birim': 'Cycle (EFC)'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Cycle Basina Net Kar', 'Deger': round(kpis['profit_per_cycle'], 2), 'Birim': '$/Cycle'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Aktif Calisilan Gun Sayisi', 'Deger': kpis['active_days'], 'Birim': 'Gun'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Pas Gecilen Gun Sayisi', 'Deger': kpis.get('passed_days', 0), 'Birim': 'Gun'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Toplam Desarj Edilen Enerji', 'Deger': round(kpis['total_discharged_mwh'], 2), 'Birim': 'MWh'},
        {'Kategori': 'Operasyonel Metrikler', 'Parametre': 'Toplam Sarj Edilen Enerji', 'Deger': round(kpis['total_charged_mwh'], 2), 'Birim': 'MWh'},
        {'Kategori': 'Piyasa & Fiyat Metrikleri', 'Parametre': 'Agirlikli Ort. Desarj Satisi', 'Deger': round(kpis['avg_discharge_price'], 2), 'Birim': '$/MWh'},
        {'Kategori': 'Piyasa & Fiyat Metrikleri', 'Parametre': 'Agirlikli Ort. Sarj Alisi', 'Deger': round(kpis['avg_charge_price'], 2), 'Birim': '$/MWh'},
        {'Kategori': 'Piyasa & Fiyat Metrikleri', 'Parametre': 'Yil Boyu Ort. Fiyat Makasi (Alis-Satis Farki)', 'Deger': round(kpis['realized_spread'], 2), 'Birim': '$/MWh'},
    ]
    df_kpis = pd.DataFrame(kpi_records)

    hourly_clean = hourly_df.copy()
    def get_action_label(row):
        if row.get('is_charging', False):
            return 'Sarj'
        elif row.get('is_discharging', False):
            return 'Desarj'
        elif row.get('is_passed', False):
            return 'Pas Gecildi'
        return 'Bekleme (Standby)'

    hourly_clean['Islem Durumu'] = hourly_clean.apply(get_action_label, axis=1)
    if pd.api.types.is_datetime64_any_dtype(hourly_clean['date']):
        hourly_clean['Tarih'] = hourly_clean['date'].dt.strftime('%Y-%m-%d')
    else:
        hourly_clean['Tarih'] = hourly_clean['date'].astype(str)

    hourly_clean['PTF ($/MWh)'] = hourly_clean['ptf_usd'].round(2)
    hourly_clean['Sarj Gucu (MW)'] = hourly_clean['p_ch_mw'].round(2)
    hourly_clean['Desarj Gucu (MW)'] = hourly_clean['p_dis_mw'].round(2)
    hourly_clean['Batarya SoC (MWh)'] = hourly_clean['soc_mwh'].round(2)
    hourly_clean['Batarya SoC (%)'] = hourly_clean['soc_pct'].round(1)
    hourly_clean['Sarj Maliyeti ($)'] = hourly_clean['charge_cost'].round(2)
    hourly_clean['Desarj Geliri ($)'] = hourly_clean['discharge_revenue'].round(2)
    hourly_clean['Yipranma Maliyeti ($)'] = hourly_clean['degradation_cost'].round(2)
    hourly_clean['Net Kar ($)'] = hourly_clean['net_profit'].round(2)

    hourly_export = hourly_clean[[
        'Tarih', 'saat_str', 'PTF ($/MWh)', 'Sarj Gucu (MW)', 'Desarj Gucu (MW)',
        'Batarya SoC (MWh)', 'Batarya SoC (%)', 'Sarj Maliyeti ($)', 'Desarj Geliri ($)',
        'Yipranma Maliyeti ($)', 'Net Kar ($)', 'Islem Durumu'
    ]].copy()
    hourly_export.rename(columns={'saat_str': 'Saat'}, inplace=True)

    daily_clean = daily_df.copy()
    if pd.api.types.is_datetime64_any_dtype(daily_clean['date']):
        daily_clean['Tarih'] = daily_clean['date'].dt.strftime('%Y-%m-%d')
    else:
        daily_clean['Tarih'] = daily_clean['date'].astype(str)

    daily_clean['Sarj Saati'] = daily_clean['best_ch'].apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['Desarj Saati'] = daily_clean['best_dis'].apply(
        lambda x: f'{int(x):02d}:00' if pd.notna(x) and x is not None else '-'
    )
    daily_clean['Operasyon Durumu'] = daily_clean['is_passed'].apply(
        lambda x: 'Pas Gecildi' if x else 'Aktif Dongu'
    )

    daily_clean['Min PTF ($/MWh)'] = daily_clean['ptf_min'].round(2)
    daily_clean['Max PTF ($/MWh)'] = daily_clean['ptf_max'].round(2)
    daily_clean['Ort. PTF ($/MWh)'] = daily_clean['ptf_avg'].round(2)
    daily_clean['Gunluk Spread ($/MWh)'] = daily_clean['ptf_spread'].round(2)
    daily_clean['Sarj Enerjisi (MWh)'] = daily_clean['charged_mwh'].round(2)
    daily_clean['Desarj Enerjisi (MWh)'] = daily_clean['discharged_mwh'].round(2)
    daily_clean['Sarj Maliyeti ($)'] = daily_clean['charge_cost'].round(2)
    daily_clean['Desarj Geliri ($)'] = daily_clean['discharge_revenue'].round(2)
    daily_clean['Brut Kar ($)'] = daily_clean['gross_profit'].round(2)
    daily_clean['Yipranma Maliyeti ($)'] = daily_clean['degradation_cost'].round(2)
    daily_clean['Net Kar ($)'] = daily_clean['net_profit'].round(2)
    daily_clean['Cycle (EFC)'] = daily_clean['cycles'].round(2)
    daily_clean['Cycle Basina Kar ($/Cycle)'] = daily_clean['profit_per_cycle'].round(2)

    daily_export = daily_clean[[
        'Tarih', 'month', 'Min PTF ($/MWh)', 'Max PTF ($/MWh)', 'Ort. PTF ($/MWh)', 'Gunluk Spread ($/MWh)',
        'Sarj Saati', 'Desarj Saati', 'Sarj Enerjisi (MWh)', 'Desarj Enerjisi (MWh)',
        'Sarj Maliyeti ($)', 'Desarj Geliri ($)', 'Brut Kar ($)', 'Yipranma Maliyeti ($)',
        'Net Kar ($)', 'Cycle (EFC)', 'Cycle Basina Kar ($/Cycle)', 'Operasyon Durumu'
    ]].copy()
    daily_export.rename(columns={'month': 'Ay No'}, inplace=True)

    monthly_clean = monthly_df.copy()
    monthly_clean['Desarj Geliri ($)'] = monthly_clean['discharge_revenue'].round(2)
    monthly_clean['Sarj Maliyeti ($)'] = monthly_clean['charge_cost'].round(2)
    monthly_clean['Brut Arbitraj Kari ($)'] = monthly_clean['gross_profit'].round(2)
    monthly_clean['Yipranma Maliyeti ($)'] = monthly_clean['degradation_cost'].round(2)
    monthly_clean['Net Arbitraj Kari ($)'] = monthly_clean['net_profit'].round(2)
    monthly_clean['Toplam Cycle (EFC)'] = monthly_clean['cycles'].round(1)
    monthly_clean['Aktif Gun Sayisi'] = monthly_clean['active_days']
    monthly_clean['Pas Gecilen Gun Sayisi'] = monthly_clean['passed_days']
    monthly_clean['Cycle Basi Net Kar ($/Cycle)'] = monthly_clean['profit_per_cycle'].round(2)
    monthly_clean['Desarj Enerjisi (MWh)'] = monthly_clean['discharged_mwh'].round(2)
    monthly_clean['Sarj Enerjisi (MWh)'] = monthly_clean['charged_mwh'].round(2)
    monthly_clean['Ortalama Gunluk Spread ($/MWh)'] = monthly_clean['avg_spread'].round(2)
    if 'avg_ptf' in monthly_clean.columns:
        monthly_clean['Ortalama PTF ($/MWh)'] = monthly_clean['avg_ptf'].round(2)
        cols_m = [
            'month_name', 'Desarj Geliri ($)', 'Sarj Maliyeti ($)', 'Brut Arbitraj Kari ($)', 'Yipranma Maliyeti ($)',
            'Net Arbitraj Kari ($)', 'Toplam Cycle (EFC)', 'Aktif Gun Sayisi', 'Pas Gecilen Gun Sayisi',
            'Cycle Basi Net Kar ($/Cycle)', 'Desarj Enerjisi (MWh)', 'Sarj Enerjisi (MWh)', 'Ortalama Gunluk Spread ($/MWh)',
            'Ortalama PTF ($/MWh)'
        ]
    else:
        cols_m = [
            'month_name', 'Desarj Geliri ($)', 'Sarj Maliyeti ($)', 'Brut Arbitraj Kari ($)', 'Yipranma Maliyeti ($)',
            'Net Arbitraj Kari ($)', 'Toplam Cycle (EFC)', 'Aktif Gun Sayisi', 'Pas Gecilen Gun Sayisi',
            'Cycle Basi Net Kar ($/Cycle)', 'Desarj Enerjisi (MWh)', 'Sarj Enerjisi (MWh)', 'Ortalama Gunluk Spread ($/MWh)'
        ]

    monthly_export = monthly_clean[cols_m].copy()
    monthly_export.rename(columns={'month_name': 'Ay'}, inplace=True)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_kpis.to_excel(writer, sheet_name='Ozet ve Parametreler', index=False)
        monthly_export.to_excel(writer, sheet_name='Aylik Kirilim', index=False)
        daily_export.to_excel(writer, sheet_name='Gunluk Ozet (365 Gun)', index=False)
        hourly_export.to_excel(writer, sheet_name='8760 Saatlik Detay', index=False)
        if comp_df is not None and not comp_df.empty:
            comp_df.to_excel(writer, sheet_name='2024 vs 2025 Kiyaslama', index=False)

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
