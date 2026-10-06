"""
BESS 0.5C - Plotly Görselleştirme Modülü
Tüm grafik bileşenlerini izole ederek arayüz kodunu temiz ve modüler tutar.
"""

from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_daily_dispatch_chart(
    day_df: pd.DataFrame,
    power_mw: float,
    capacity_mwh: float,
    date_label: str
) -> go.Figure:
    """Tek bir gün için 3 satırlı senkronize güç, fiyat ve SoC grafiğini üretir."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "1. EPİAŞ Piyasa Takas Fiyatı (PTF - $/MWh)",
            "2. Batarya Sürekli Şarj / Deşarj Güç Modülasyonu (MW)",
            "3. Batarya Şarj Seviyesi (State of Charge - SoC % ve MWh)"
        ),
        row_heights=[0.32, 0.40, 0.28]
    )

    # 1. Satır: PTF Fiyat Eğrisi ve Şarj / Deşarj Noktaları
    fig.add_trace(
        go.Scatter(
            x=day_df["hour"],
            y=day_df["ptf_usd"],
            mode="lines",
            name="PTF Fiyatı ($/MWh)",
            line=dict(color="#94a3b8", width=2.4, shape="spline", smoothing=0.3),
            hovertemplate="Saat %{x:02d}:00<br>PTF: <b>$%{y:.2f}/MWh</b><extra></extra>",
        ),
        row=1, col=1
    )

    p_ch_vals = day_df["p_charge"] if "p_charge" in day_df.columns else day_df["p_charge_mw"]
    p_dis_vals = day_df["p_discharge"] if "p_discharge" in day_df.columns else day_df["p_discharge_mw"]

    # 1. Satır: Belirgin Yuvarlak Şarj Noktaları (Mavi Daire)
    ch_mask = p_ch_vals > 0.05
    if ch_mask.any():
        ch_h = day_df.loc[ch_mask, "hour"]
        ch_p = day_df.loc[ch_mask, "ptf_usd"]
        ch_mw = p_ch_vals[ch_mask]
        fig.add_trace(
            go.Scatter(
                x=ch_h,
                y=ch_p,
                mode="markers+text",
                name="Şarj Noktaları",
                marker=dict(
                    color="#38bdf8",
                    size=14,
                    symbol="circle",
                    line=dict(color="#ffffff", width=2.2)
                ),
                text=[f"{p:.0f}MW" for p in ch_mw],
                textposition="bottom center",
                textfont=dict(size=10, color="#38bdf8", family="Inter, sans-serif"),
                hovertemplate="<b>ŞARJ NOKTASI</b><br>Saat: %{x:02d}:00<br>Fiyat: <b>$%{y:.2f}/MWh</b><br>Şarj Gücü: <b>%{customdata:.1f} MW</b><extra></extra>",
                customdata=ch_mw
            ),
            row=1, col=1
        )

    # 1. Satır: Belirgin Yuvarlak Deşarj Noktaları (Yeşil Daire)
    dis_mask = p_dis_vals > 0.05
    if dis_mask.any():
        dis_h = day_df.loc[dis_mask, "hour"]
        dis_p = day_df.loc[dis_mask, "ptf_usd"]
        dis_mw = p_dis_vals[dis_mask]
        fig.add_trace(
            go.Scatter(
                x=dis_h,
                y=dis_p,
                mode="markers+text",
                name="Deşarj Noktaları",
                marker=dict(
                    color="#4edea3",
                    size=14,
                    symbol="circle",
                    line=dict(color="#ffffff", width=2.2)
                ),
                text=[f"{p:.0f}MW" for p in dis_mw],
                textposition="top center",
                textfont=dict(size=10, color="#4edea3", family="Inter, sans-serif"),
                hovertemplate="<b>DEŞARJ NOKTASI</b><br>Saat: %{x:02d}:00<br>Fiyat: <b>$%{y:.2f}/MWh</b><br>Deşarj Gücü: <b>%{customdata:.1f} MW</b><extra></extra>",
                customdata=dis_mw
            ),
            row=1, col=1
        )

    # 2. Satır: Şarj (Mavi) ve Deşarj (Yeşil) Barları
    fig.add_trace(
        go.Bar(
            x=day_df["hour"],
            y=p_ch_vals,
            name="Şarj Gücü (MW)",
            marker=dict(color="rgba(56, 189, 248, 0.75)", line=dict(color="#38bdf8", width=1.5)),
            hovertemplate="Saat %{x:02d}:00<br>Şarj Gücü: <b>%{y:.1f} MW</b><extra></extra>",
            offsetgroup=1
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(
            x=day_df["hour"],
            y=p_dis_vals,
            name="Deşarj Gücü (MW)",
            marker=dict(color="rgba(78, 222, 163, 0.75)", line=dict(color="#4edea3", width=1.5)),
            hovertemplate="Saat %{x:02d}:00<br>Deşarj Gücü: <b>%{y:.1f} MW</b><extra></extra>",
            offsetgroup=2
        ),
        row=2, col=1
    )

    # 3. Satır: SoC Yüzdesi ve MWh Seviyesi Eğrisi
    soc_pct = (day_df["soc_mwh"] / capacity_mwh * 100.0) if capacity_mwh > 0 else 0
    fig.add_trace(
        go.Scatter(
            x=day_df["hour"],
            y=soc_pct,
            mode="lines",
            name="SoC (%)",
            fill="tozeroy",
            fillcolor="rgba(14, 165, 233, 0.14)",
            line=dict(color="#ffb95f", width=2.4, shape="hv"),
            hovertemplate="Saat %{x:02d}:00<br>SoC: <b>%{y:.1f}%</b> (%{customdata:.1f} MWh)<extra></extra>",
            customdata=day_df["soc_mwh"]
        ),
        row=3, col=1
    )

    # 3. Satır: SoC üzerinde Şarj ve Deşarj Yuvarlak Noktaları
    if ch_mask.any():
        fig.add_trace(
            go.Scatter(
                x=ch_h,
                y=soc_pct[ch_mask],
                mode="markers",
                name="SoC (Şarj)",
                marker=dict(
                    color="#38bdf8",
                    size=10,
                    symbol="circle",
                    line=dict(color="#ffffff", width=1.8)
                ),
                hovertemplate="Saat %{x:02d}:00 (Şarj)<br>SoC: <b>%{y:.1f}%</b><extra></extra>",
                showlegend=False
            ),
            row=3, col=1
        )
    if dis_mask.any():
        fig.add_trace(
            go.Scatter(
                x=dis_h,
                y=soc_pct[dis_mask],
                mode="markers",
                name="SoC (Deşarj)",
                marker=dict(
                    color="#4edea3",
                    size=10,
                    symbol="circle",
                    line=dict(color="#ffffff", width=1.8)
                ),
                hovertemplate="Saat %{x:02d}:00 (Deşarj)<br>SoC: <b>%{y:.1f}%</b><extra></extra>",
                showlegend=False
            ),
            row=3, col=1
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=660,
        margin=dict(l=15, r=15, t=40, b=15),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11)
        ),
        hovermode="x unified"
    )

    for r in [1, 2, 3]:
        fig.update_xaxes(
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickmode="linear",
            tick0=0,
            dtick=1,
            tickformat="%02d:00",
            row=r, col=1
        )
        fig.update_yaxes(gridcolor="rgba(255, 255, 255, 0.05)", row=r, col=1)

    fig.update_yaxes(title_text="$/MWh", row=1, col=1)
    fig.update_yaxes(title_text="Güç (MW)", range=[0, power_mw * 1.15], row=2, col=1)
    fig.update_yaxes(title_text="SoC (%)", range=[0, 105], row=3, col=1)
    fig.update_xaxes(title_text=f"Saat (24 Saatlik Ufuk - {date_label})", row=3, col=1)

    return fig


def build_cumulative_profit_chart(daily_df: pd.DataFrame) -> go.Figure:
    """Kümülatif net kâr eğrisini üretir."""
    fig = go.Figure()
    cum_y = daily_df["cum_net_profit"] if "cum_net_profit" in daily_df.columns else daily_df["net_profit"].cumsum()
    fig.add_trace(
        go.Scatter(
            x=daily_df["date"],
            y=cum_y,
            mode="lines+markers",
            name="Kümülatif Net Kâr ($)",
            fill="tozeroy",
            fillcolor="rgba(78, 222, 163, 0.15)",
            line=dict(color="#4edea3", width=2.8, shape="spline", smoothing=0.3),
            marker=dict(size=7, color="#4edea3", line=dict(color="#ffffff", width=1.5)),
            hovertemplate="%{x}<br>Kümülatif Kâr: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=320,
        margin=dict(l=15, r=15, t=15, b=15),
        yaxis=dict(title="Kümülatif Kâr ($)", gridcolor="rgba(255, 255, 255, 0.06)", tickprefix="$"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
    )
    return fig


def build_daily_cycles_bar_chart(daily_df: pd.DataFrame) -> go.Figure:
    """Günlük EFC döngü dağılımı çubuk grafiğini üretir."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily_df["date"],
            y=daily_df["cycles"],
            name="Günlük Döngü (EFC)",
            marker_color="rgba(56, 189, 248, 0.8)",
            hovertemplate="%{x}<br>Döngü: <b>%{y:.2f} EFC</b><extra></extra>"
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=320,
        margin=dict(l=15, r=15, t=15, b=15),
        yaxis=dict(title="Eşdeğer Döngü (EFC)", gridcolor="rgba(255, 255, 255, 0.06)", range=[0, 2.0]),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
    )
    return fig


def build_monthly_financial_chart(monthly_df: pd.DataFrame) -> go.Figure:
    """Aylık Net Kâr, Deşarj Geliri ve Şarj Maliyeti karşılaştırma çubuğunu üretir."""
    rev_col = "revenue" if "revenue" in monthly_df.columns else "discharge_revenue"
    cost_col = "cost" if "cost" in monthly_df.columns else "charge_cost"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly_df["month_name"],
            y=monthly_df["net_profit"],
            name="Net Kâr ($)",
            marker_color="#4edea3",
            hovertemplate="%{x}<br>Net Kâr: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly_df["month_name"],
            y=monthly_df[rev_col],
            name="Deşarj Geliri ($)",
            marker_color="#38bdf8",
            hovertemplate="%{x}<br>Deşarj Geliri: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly_df["month_name"],
            y=monthly_df[cost_col],
            name="Şarj Maliyeti ($)",
            marker_color="#f43f5e",
            hovertemplate="%{x}<br>Şarj Maliyeti: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=330,
        margin=dict(l=15, r=15, t=25, b=15),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Tutar ($)", gridcolor="rgba(255, 255, 255, 0.06)", tickprefix="$"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
    )
    return fig


def build_monthly_cycles_chart(monthly_df: pd.DataFrame) -> go.Figure:
    """Aylık toplam döngü (EFC) grafiğini üretir."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly_df["month_name"],
            y=monthly_df["cycles"],
            name="Aylık EFC",
            marker_color="#ffb95f",
            hovertemplate="%{x}<br>Döngü: <b>%{y:.1f} EFC</b><extra></extra>"
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=330,
        margin=dict(l=15, r=15, t=25, b=15),
        yaxis=dict(title="Döngü Sayısı (EFC)", gridcolor="rgba(255, 255, 255, 0.06)"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
    )
    return fig


def build_strategy_comparison_barchart(
    comp_lp_df: pd.DataFrame,
    degradation_cost: float
) -> go.Figure:
    """1.0 vs 1.5 Döngü senaryolarının finansal bileşenler çubuk grafiğini üretir."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comp_lp_df["Kısa Kod"],
            y=comp_lp_df["Net Kâr ($)"],
            name="Net Kâr ($)",
            marker_color="#4edea3",
            text=[f"${v:,.0f}" for v in comp_lp_df["Net Kâr ($)"]],
            textposition="outside",
            textfont=dict(color="#4edea3", size=11, family="JetBrains Mono"),
            hovertemplate="<b>%{x}</b><br>Net Kâr: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=comp_lp_df["Kısa Kod"],
            y=comp_lp_df["Deşarj Geliri ($)"],
            name="Deşarj Geliri ($)",
            marker_color="#38bdf8",
            hovertemplate="<b>%{x}</b><br>Deşarj Geliri: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=comp_lp_df["Kısa Kod"],
            y=comp_lp_df["Şarj Maliyeti ($)"],
            name="Şarj Maliyeti ($)",
            marker_color="#f43f5e",
            hovertemplate="<b>%{x}</b><br>Şarj Maliyeti: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    if degradation_cost > 0:
        fig.add_trace(
            go.Bar(
                x=comp_lp_df["Kısa Kod"],
                y=comp_lp_df["Yıpranma ($)"],
                name="Yıpranma Maliyeti ($)",
                marker_color="#ffb95f",
                hovertemplate="<b>%{x}</b><br>Yıpranma: <b>$%{y:,.2f}</b><extra></extra>"
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=360,
        margin=dict(l=15, r=15, t=25, b=15),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Tutar ($)", gridcolor="rgba(255, 255, 255, 0.06)", tickprefix="$"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)")
    )
    return fig


def build_yearly_comparison_chart(comp_df: pd.DataFrame) -> go.Figure:
    """2024 ve 2025 yılları için yıllık karşılaştırma çubuğunu üretir."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comp_df["Yıl"],
            y=comp_df["Net Kâr ($)"],
            name="Net Kâr ($)",
            marker_color="#4edea3",
            text=[f"${v:,.0f}" for v in comp_df["Net Kâr ($)"]],
            textposition="outside",
            textfont=dict(color="#4edea3", size=12, family="JetBrains Mono"),
            hovertemplate="<b>%{x}</b><br>Net Kâr: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=comp_df["Yıl"],
            y=comp_df["Deşarj Geliri ($)"],
            name="Deşarj Geliri ($)",
            marker_color="#38bdf8",
            hovertemplate="<b>%{x}</b><br>Deşarj: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            x=comp_df["Yıl"],
            y=comp_df["Şarj Maliyeti ($)"],
            name="Şarj Maliyeti ($)",
            marker_color="#f43f5e",
            hovertemplate="<b>%{x}</b><br>Şarj: <b>$%{y:,.2f}</b><extra></extra>"
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(24, 28, 36, 0.5)",
        plot_bgcolor="rgba(15, 19, 28, 0.6)",
        font=dict(color="#dfe2ee", family="Inter, sans-serif", size=11),
        height=360,
        margin=dict(l=15, r=15, t=25, b=15),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Tutar ($)", gridcolor="rgba(255, 255, 255, 0.06)", tickprefix="$")
    )
    return fig
