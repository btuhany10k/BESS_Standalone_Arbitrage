"""
BESS 0.5C - Cupertino & Material 3 HTML Arayüz Kartları
HTML ve CSS görsel şablonlarını Python kodundan izole eder.
"""

from typing import Dict, Any
import pandas as pd
from src.styles import ICONS, make_icon_badge, clean_html


def render_header_banner(
    selected_year: int,
    power_mw: float,
    capacity_mwh: float,
    rte: float,
    soc_start_pct: float,
    soc_end_pct: float,
    strat_pill: str,
    degradation_cost: float,
    scope_pill: str
) -> str:
    """Sayfa tepe başlığını ve teknik sistem özet rozetlerini üretir."""
    return clean_html(f"""
    <div class="cupertino-header">
        <div class="cupertino-header-row">
            <div class="cupertino-title">
                {make_icon_badge(ICONS['battery'], color="#38bdf8", bg="rgba(14, 165, 233, 0.16)", border="rgba(14, 165, 233, 0.35)", size=36)}
                <span>Standalone BESS Arbitraj Stratejisi</span>
                <span class="cupertino-spec-pill">0.5C / 2-SAAT DEPOLAMA</span>
                <span class="cupertino-spec-pill" style="border-color: rgba(56, 189, 248, 0.4); color: #38bdf8; background: rgba(14, 165, 233, 0.12);">SÜREKLİ GÜÇ MODÜLASYONU</span>
                <span class="cupertino-spec-pill" style="border-color: rgba(78, 222, 163, 0.4); color: #4edea3; background: rgba(78, 222, 163, 0.12);">{scope_pill}</span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <span class="cupertino-live-dot">
                    <span class="pulse-dot"></span>
                    <span>OPTİMUM SENARYO ÇÖZÜMÜ</span>
                </span>
            </div>
        </div>
        <div class="cupertino-sub-bar">
            <span>EPİAŞ {selected_year} Saatlik PTF ($/MWh)</span>
            <span class="cupertino-sub-tag">{power_mw:.0f} MW / {capacity_mwh:.0f} MWh</span>
            <span class="cupertino-sub-tag">RTE: %{rte*100:.0f}</span>
            <span class="cupertino-sub-tag">SoC: %{soc_start_pct:.0f} ➔ %{soc_end_pct:.0f}</span>
            <span class="cupertino-sub-tag" style="color: #38bdf8; font-weight: 600;">{strat_pill}</span>
            <span class="cupertino-sub-tag">Yıpranma: ${degradation_cost:.1f}/MWh</span>
        </div>
    </div>
    """)


def render_kpi_cards(
    kpis: Dict[str, Any],
    power_mw: float,
    degradation_cost: float
) -> str:
    """Apple-style 4 sütunlu Bento KPI metrik kartlarını üretir."""
    if degradation_cost > 0:
        deg_color = "amber"
        deg_text = f"${kpis['total_degradation_cost']:,.2f}"
        deg_sub = f"${degradation_cost:.1f}/MWh"
    else:
        deg_color = "emerald"
        deg_text = "Dahil Edilmedi"
        deg_sub = "Sıfır Aşınma Varsayımı"

    kpi_items = [
        # 1. Satır: Hero (2 Sütun) + Spread (1 Sütun) + Kısmi Güç Modülasyonu (1 Sütun)
        f"""
        <div class="cupertino-card hero-kpi" style="grid-column: span 2;">
            <div class="card-top">
                <div class="card-label"><span style="color: var(--accent-emerald);">{ICONS['dollar']}</span> Net Arbitraj Kârı</div>
                <span style="font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600; background: rgba(78, 222, 163, 0.15); color: var(--accent-emerald); border: 1px solid rgba(78, 222, 163, 0.35); padding: 0.15rem 0.5rem; border-radius: 9999px;">
                    Optimum Getiri
                </span>
            </div>
            <div class="card-metric emerald">${kpis['net_profit']:,.2f}</div>
            <div class="card-foot">
                <span style="color: var(--text-secondary);">Brüt: <span class="val-mono">${kpis['gross_profit']:,.2f}</span></span>
                <span style="color: var(--text-secondary);">Günlük Ort: <span class="val-mono" style="color: var(--accent-emerald);">${kpis['avg_daily_profit']:,.2f}</span></span>
            </div>
        </div>
        """,
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['trending']} Gerçekleşen Spread</div>
                <div class="card-icon" style="color: var(--accent-amber);">{ICONS['sliders']}</div>
            </div>
            <div class="card-metric amber">${kpis['realized_spread']:,.1f} <span style="font-size: 0.82rem; color: var(--text-muted); font-weight: 500;">/MWh</span></div>
            <div class="card-foot">
                <span>Fiyat Makası:</span>
                <span class="val-mono">Deşarj - Şarj</span>
            </div>
        </div>
        """,
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['refresh']} Döngü Başı Kâr</div>
                <div class="card-icon" style="color: var(--accent-sky);">{ICONS['chart']}</div>
            </div>
            <div class="card-metric sky">${kpis['profit_per_cycle']:,.2f} <span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 500;">/EFC</span></div>
            <div class="card-foot">
                <span>Döngü Getirisi:</span>
                <span class="val-mono">1 Döngü Başına Net Kâr</span>
            </div>
        </div>
        """,

        # 2. Satır: Deşarj (1) + Şarj (1) + Yıpranma (1) + Eşdeğer Döngü (1)
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['zap']} Deşarj Geliri</div>
                <div class="card-icon" style="color: var(--accent-emerald);">{ICONS['north_east']}</div>
            </div>
            <div class="card-metric emerald">${kpis['total_revenue']:,.2f}</div>
            <div class="card-foot">
                <span>Ort. Deşarj:</span>
                <span class="val-mono">${kpis['avg_discharge_price']:.1f}/MWh</span>
            </div>
        </div>
        """,
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['battery']} Şarj Maliyeti</div>
                <div class="card-icon" style="color: var(--accent-rose);">{ICONS['south_west']}</div>
            </div>
            <div class="card-metric rose">${kpis['total_cost']:,.2f}</div>
            <div class="card-foot">
                <span>Ort. Şarj:</span>
                <span class="val-mono">${kpis['avg_charge_price']:.1f}/MWh</span>
            </div>
        </div>
        """,
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['shield']} Yıpranma Amortismanı</div>
                <div class="card-icon">{ICONS['sliders']}</div>
            </div>
            <div class="card-metric {deg_color}">{deg_text}</div>
            <div class="card-foot">
                <span>Birim Maliyet:</span>
                <span class="val-mono">{deg_sub}</span>
            </div>
        </div>
        """,
        f"""
        <div class="cupertino-card">
            <div class="card-top">
                <div class="card-label">{ICONS['refresh']} Toplam Eşdeğer Döngü</div>
                <div class="card-icon" style="color: var(--accent-sky);">{ICONS['chart']}</div>
            </div>
            <div class="card-metric sky">{kpis['total_cycles']:,.1f} <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">EFC</span></div>
            <div class="card-foot">
                <span>Operasyon:</span>
                <span class="val-mono">{kpis['active_days']} aktif / {kpis['passed_days']} pas</span>
            </div>
        </div>
        """
    ]

    cards_html = "\n".join(clean_html(card) for card in kpi_items)
    return f"""<div class="cupertino-bento-grid" style="margin-bottom: 1.5rem;">{cards_html}</div>"""


def render_strategy_comparison_cards(
    row_10: pd.Series,
    row_15: pd.Series,
    delta_15: float,
    pct_15: float,
    delta_efc: float
) -> Tuple[str, str, str]:
    """Tab 3 için 3 ana karşılaştırma KPI kartı HTML'ini döndürür."""
    card1 = clean_html(f"""
    <div class="cupertino-card">
        <div class="card-top">
            <div class="card-label">1.0 Döngü Senaryosu (Koruyucu Mod)</div>
            <div class="card-icon" style="color: var(--accent-sky);">{ICONS['shield']}</div>
        </div>
        <div class="card-metric sky">${row_10['Net Kâr ($)']:,.2f}</div>
        <div class="card-foot">
            <span>Toplam Döngü:</span>
            <span class="val-mono" style="color: #38bdf8;">{row_10['Toplam Döngü (EFC)']:.1f} EFC</span>
        </div>
        <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
            Döngü Başı Kâr: <b style="color: #dfe2ee;">${row_10['Döngü Başı Kâr ($/Cycle)']:,.2f}</b> | Pil Garantisi Azami Koruma
        </div>
    </div>
    """)

    card2 = clean_html(f"""
    <div class="cupertino-card">
        <div class="card-top">
            <div class="card-label">1.5 Döngü Kısmi Modülasyon Senaryosu (Fırsatçı Mod)</div>
            <div class="card-icon" style="color: var(--accent-emerald);">{ICONS['zap']}</div>
        </div>
        <div class="card-metric emerald">${row_15['Net Kâr ($)']:,.2f}</div>
        <div class="card-foot">
            <span>Toplam Döngü:</span>
            <span class="val-mono" style="color: #4edea3;">{row_15['Toplam Döngü (EFC)']:.1f} EFC</span>
        </div>
        <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
            Döngü Başı Kâr: <b style="color: #dfe2ee;">${row_15['Döngü Başı Kâr ($/Cycle)']:,.2f}</b> | Sabah Ara Piki & Duck Curve
        </div>
    </div>
    """)

    card3 = clean_html(f"""
    <div class="cupertino-card">
        <div class="card-top">
            <div class="card-label">1.5 Döngünün Sağladığı Net Katma Değer</div>
            <div class="card-icon" style="color: var(--accent-emerald);">{ICONS['trending']}</div>
        </div>
        <div class="card-metric emerald">+${delta_15:,.2f}</div>
        <div class="card-foot">
            <span>Net Kâr Artışı:</span>
            <span class="val-mono" style="color: #4edea3;">+%{pct_15:.2f}</span>
        </div>
        <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.4rem; font-family: var(--font-mono);">
            Ek Aşınma: <b style="color: #dfe2ee;">+{delta_efc:.1f} EFC</b> | Net Gelir Çarpanı: <b style="color: #4edea3;">1.27x</b>
        </div>
    </div>
    """)

    return card1, card2, card3


def render_strategy_guide_cards(
    row_10: pd.Series,
    row_15: pd.Series,
    delta_15: float,
    pct_15: float
) -> Tuple[str, str]:
    """Tab 3 mühendislik ve işletme strateji rehberi kartlarını döndürür."""
    guide1 = clean_html(f"""
    <div class="cupertino-card" style="height: 100%;">
        <div class="card-top">
            <div class="card-label"><span style="color: #38bdf8;">1.</span> 1.0 Döngü (Koruyucu / Pil Ömrü & Garanti Koruması)</div>
            <div class="card-icon">{ICONS['shield']}</div>
        </div>
        <div style="font-size: 0.83rem; color: #cbd5e1; margin: 0.6rem 0; line-height: 1.6;">
            • <b>Ne Zaman Seçilmeli?</b> LFP hücre garantisinin yıllık katı döngü sınırına (ör. yılda 365 EFC / 10 yıl) tabi olduğu ve pil ömrünün 15 yıla yayılması hedeflendiği durumlarda.<br>
            • <b>Maksimum Döngü Başı Verim:</b> Sınırlı 1 döngü hakkı yalnızca günün en derin fiyat farkına tahsis edildiğinden döngü başına en yüksek kâr (<b>${row_10['Döngü Başı Kâr ($/Cycle)']:,.2f}/Döngü</b>) bu modda oluşur.<br>
            • <b>Düşük Termal Stres:</b> Günde tek bir şarj/deşarj yapılarak inverter ve hücre termal yorgunluğu minimize edilir.
        </div>
        <div class="card-foot">
            <span>Öncelik:</span>
            <span class="val-mono" style="color: #38bdf8;">Pil Ömrü & Garanti Emniyeti</span>
        </div>
    </div>
    """)

    guide2 = clean_html(f"""
    <div class="cupertino-card" style="height: 100%;">
        <div class="card-top">
            <div class="card-label"><span style="color: #4edea3;">2.</span> 1.5 Döngü (Kısmi Güç Modülasyonu & Altın Oran)</div>
            <div class="card-icon">{ICONS['zap']}</div>
        </div>
        <div style="font-size: 0.83rem; color: #cbd5e1; margin: 0.6rem 0; line-height: 1.6;">
            • <b>Ne Zaman Seçilmeli?</b> Türkiye piyasasındaki çift pik (sabah mini piki 08:00-11:00 ve akşam ana piki 17:00-21:00) ile öğle solar çukurunu (duck curve) nakde çevirmek istendiğinde.<br>
            • <b>Kısmi Güç Avantajı:</b> Batarya sabah 50 MWh kısmi deşarj yapıp, öğle 12:00-14:00 ucuz solar saatinde şarj olur ve akşam 100 MWh tam güçle boşalır.<br>
            • <b>Hücreyi Bitirmeden Yüksek Nakit Akışı:</b> 2.0 tam döngünün getirdiği ağır hücre yıpranması yerine, sadece 1.5 döngüyle kârı <b>+${delta_15:,.2f} (+%{pct_15:.2f})</b> artırır.
        </div>
        <div class="card-foot">
            <span>Denge:</span>
            <span class="val-mono" style="color: #4edea3;">Optimum Kâr / Yıpranma Dengesi</span>
        </div>
    </div>
    """)

    return guide1, guide2


def render_daily_mini_kpi_cards(
    charge_cost: float,
    discharge_revenue: float,
    net_profit: float,
    degradation_cost: float,
    max_spread: float,
    min_ptf: float,
    max_ptf: float,
    cycles: float = 0.0
) -> str:
    """Günün 5 kritik metriğini (Net Kâr, Deşarj Geliri, Şarj Gideri, Yıpranma, Maks. Spread)
    gösteren zarif, kompakt 5 sütunlu yatay mini kart şablonunu üretir."""
    deg_val_class = "amber" if degradation_cost > 0 else "slate"
    deg_val_text = f"${degradation_cost:,.2f}" if degradation_cost > 0 else "$0.00"
    deg_sub = "Hücre Aşınması" if degradation_cost > 0 else "Sıfır Aşınma"

    return clean_html(f"""
    <div class="daily-kpi-grid">
        <!-- 1. Günün Net Kârı -->
        <div class="mini-kpi-card highlight-profit">
            <div class="mini-kpi-top">
                <span class="mini-kpi-label">Günün Net Kârı</span>
                <span class="mini-kpi-badge emerald">{cycles:.2f} EFC</span>
            </div>
            <div class="mini-kpi-value emerald">${net_profit:,.2f}</div>
            <div class="mini-kpi-sub">Arbitraj Net Getirisi</div>
        </div>

        <!-- 2. Günün Deşarj Geliri -->
        <div class="mini-kpi-card">
            <div class="mini-kpi-top">
                <span class="mini-kpi-label">Deşarj Geliri</span>
                <span style="color: #4edea3; font-size: 0.85rem;">{ICONS['north_east']}</span>
            </div>
            <div class="mini-kpi-value emerald">${discharge_revenue:,.2f}</div>
            <div class="mini-kpi-sub">Şebekeye Satış</div>
        </div>

        <!-- 3. Günün Şarj Gideri -->
        <div class="mini-kpi-card">
            <div class="mini-kpi-top">
                <span class="mini-kpi-label">Şarj Gideri</span>
                <span style="color: #f87171; font-size: 0.85rem;">{ICONS['south_west']}</span>
            </div>
            <div class="mini-kpi-value rose">${charge_cost:,.2f}</div>
            <div class="mini-kpi-sub">Şebekeden Alış</div>
        </div>

        <!-- 4. Günün Yıpranma Maliyeti -->
        <div class="mini-kpi-card">
            <div class="mini-kpi-top">
                <span class="mini-kpi-label">Yıpranma</span>
                <span style="color: {'#ffb95f' if degradation_cost > 0 else '#94a3b8'}; font-size: 0.85rem;">{ICONS['shield']}</span>
            </div>
            <div class="mini-kpi-value {deg_val_class}">{deg_val_text}</div>
            <div class="mini-kpi-sub">{deg_sub}</div>
        </div>

        <!-- 5. Günün Maksimum Spread'i -->
        <div class="mini-kpi-card">
            <div class="mini-kpi-top">
                <span class="mini-kpi-label">Günün Maks. Spread'i</span>
                <span style="color: #38bdf8; font-size: 0.85rem;">{ICONS['sliders']}</span>
            </div>
            <div class="mini-kpi-value sky">${max_spread:,.2f} <span style="font-size: 0.72rem; color: #94a3b8; font-weight: 500;">/MWh</span></div>
            <div class="mini-kpi-sub">Maks: ${max_ptf:.1f} | Min: ${min_ptf:.1f}</div>
        </div>
    </div>
    """)

