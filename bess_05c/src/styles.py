"""
BESS 0.5C Dashboard - Stitch MCP "Cupertino Industrial Precision" Design System
Tasarım Felsefesi: Apple Cupertino Desktop Minimalizmi & Google Material 3 Hassasiyeti.
Stitch MCP Projesi: projects/16755274104988602417 (Screen: 7c41597e547c43eda28242eadeb34a08)
"""

# SVG Vektör İkonları (Katı Anti-Emoji & Apple SF Symbols / Google Material Standartları)
ICONS = {
    "zap": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    "battery": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="17" height="12" rx="2.5" ry="2.5"></rect><line x1="22" y1="10" x2="22" y2="14" stroke-width="2.5"></line><line x1="6" y1="9.5" x2="6" y2="14.5"></line><line x1="10" y1="9.5" x2="10" y2="14.5"></line><line x1="14" y1="9.5" x2="14" y2="14.5"></line></svg>',
    "calendar": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    "clock": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
    "dollar": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    "shield": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    "sliders": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>',
    "target": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
    "trending": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "download": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
    "chart": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
    "refresh": '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
    "check": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "north_east": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>',
    "south_west": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="17" y1="7" x2="7" y2="17"></line><polyline points="17 17 7 17 7 7"></polyline></svg>',
    "info": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
}

# Stitch Cupertino & Material 3 CSS Spesifikasyonu
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
        
        /* Stitch Cupertino Palette */
        --surface-lowest: #0a0e16;
        --surface-base: #0f131c;
        --surface-container-low: #181c24;
        --surface-container: #1c2028;
        --surface-container-high: #262a33;
        --surface-container-highest: #31353e;
        
        --text-primary: #dfe2ee;
        --text-secondary: #bec8d2;
        --text-muted: #88929b;
        
        --outline-hairline: rgba(62, 72, 80, 0.45);
        --outline-specular: rgba(255, 255, 255, 0.08);
        
        /* Cupertino & Google Accents */
        --accent-sky: #89ceff;
        --accent-sky-container: #0ea5e9;
        --accent-emerald: #4edea3;
        --accent-rose: #ffb4ab;
        --accent-amber: #ffb95f;
    }

    html, body, [class*="css"] {
        font-family: var(--font-sans);
        color: var(--text-primary);
        background-color: var(--surface-lowest);
        min-height: 100dvh;
        -webkit-font-smoothing: antialiased;
    }

    /* Apple Cupertino Precision Header */
    .cupertino-header {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        padding-bottom: 1.25rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid var(--outline-hairline);
    }
    .cupertino-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .cupertino-title {
        font-size: 1.65rem;
        font-weight: 600;
        letter-spacing: -0.025em;
        color: #ffffff !important;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        line-height: 1.35;
    }
    .cupertino-spec-pill {
        font-family: var(--font-mono);
        font-size: 0.70rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        background: rgba(14, 165, 233, 0.12);
        color: var(--accent-sky);
        border: 1px solid rgba(14, 165, 233, 0.35);
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    .cupertino-live-dot {
        font-family: var(--font-mono);
        font-size: 0.70rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        background: rgba(78, 222, 163, 0.12);
        color: var(--accent-emerald);
        border: 1px solid rgba(78, 222, 163, 0.3);
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }
    .pulse-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: var(--accent-emerald);
        box-shadow: 0 0 8px #4edea3;
        animation: pulseAnimation 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
    }
    @keyframes pulseAnimation {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    .cupertino-sub-bar {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        font-size: 0.82rem;
        color: var(--text-secondary);
    }
    .cupertino-sub-tag {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        padding: 0.2rem 0.6rem;
        border-radius: 8px;
        font-family: var(--font-mono);
        font-size: 0.75rem;
        color: var(--text-primary);
    }

    /* Apple-Style Bento KPI Cards Grid (4-Column Balanced Grid) */
    .cupertino-bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.85rem;
        margin-bottom: 1.75rem;
    }
    @media (max-width: 1180px) {
        .cupertino-bento-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    @media (max-width: 640px) {
        .cupertino-bento-grid {
            grid-template-columns: 1fr;
        }
        .cupertino-card.hero-kpi {
            grid-column: span 1 !important;
        }
    }
    .cupertino-card {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular), 0 4px 20px -2px rgba(0, 0, 0, 0.35);
        border-radius: 16px;
        padding: 1.15rem 1.25rem;
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .cupertino-card:hover {
        transform: translateY(-2px);
        border-color: rgba(137, 206, 255, 0.35);
        box-shadow: inset 0 1px 0 0 var(--outline-specular), 0 10px 25px -4px rgba(0, 0, 0, 0.5);
    }
    .cupertino-card.hero-kpi {
        background: linear-gradient(135deg, rgba(28, 32, 40, 0.95) 0%, rgba(15, 19, 28, 0.98) 100%);
        border: 1px solid rgba(78, 222, 163, 0.35);
    }
    .cupertino-card.hero-kpi::after {
        content: '';
        position: absolute;
        top: -30px;
        right: -30px;
        width: 120px;
        height: 120px;
        background: radial-gradient(circle, rgba(78, 222, 163, 0.15) 0%, transparent 70%);
        pointer-events: none;
    }

    .card-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.45rem;
    }
    .card-label {
        font-family: var(--font-mono);
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #ffffff !important;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .card-icon {
        color: var(--text-muted);
        display: flex;
        align-items: center;
    }
    .card-metric {
        font-family: var(--font-mono);
        font-size: 1.7rem;
        font-weight: 600;
        letter-spacing: -0.03em;
        line-height: 1.15;
        color: #ffffff;
    }
    .card-metric.emerald { color: var(--accent-emerald); }
    .card-metric.rose { color: var(--accent-rose); }
    .card-metric.sky { color: var(--accent-sky); }
    .card-metric.amber { color: var(--accent-amber); }

    .card-foot {
        font-size: 0.76rem;
        color: var(--text-muted);
        margin-top: 0.45rem;
        padding-top: 0.45rem;
        border-top: 1px solid rgba(62, 72, 80, 0.3);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .card-foot span.val-mono {
        font-family: var(--font-mono);
        color: var(--text-primary);
        font-weight: 500;
    }

    /* Apple-Style Segmented Tab Bar */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        border-radius: 12px;
        padding: 4px;
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 8px;
        border: none !important;
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 0 16px !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--surface-container-high) !important;
        color: var(--accent-sky) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3), inset 0 1px 0 0 var(--outline-specular) !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* Apple Control Center Sidebar Containers */
    .sidebar-widget {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
    }
    .sidebar-widget-title {
        font-family: var(--font-mono);
        font-size: 0.70rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted);
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Tactile Buttons */
    .stDownloadButton button,
    .stButton button {
        border-radius: 10px !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }
    .stDownloadButton button:active,
    .stButton button:active {
        transform: translateY(1px) scale(0.98) !important;
    }

    /* Range Slider Precision Styling (Apple Sky Handle & Two-Tone Progress Track) */
    div[data-baseweb="slider"] {
        margin-top: 6px;
    }
    /* Preserve BaseWeb's dynamic linear-gradient (distinct color before vs after thumb) */
    div[data-baseweb="slider"] > div > div:nth-child(1) {
        border-radius: 9999px !important;
        height: 6px !important;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.15) !important;
    }
    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #38bdf8 !important;
        border: 2.5px solid #ffffff !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6), 0 0 8px rgba(56, 189, 248, 0.7) !important;
        width: 18px !important;
        height: 18px !important;
        cursor: grab !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    div[data-baseweb="slider"] div[role="slider"]:hover {
        transform: scale(1.15) !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.7), 0 0 12px rgba(56, 189, 248, 0.9) !important;
    }
    div[data-baseweb="slider"] div[role="slider"]:active {
        cursor: grabbing !important;
        transform: scale(1.05) !important;
    }
    div[data-baseweb="slider"] [data-testid="stSliderTickBar"] {
        background: rgba(255, 255, 255, 0.08) !important;
    }
    div[data-baseweb="slider"] div[data-testid="stSliderThumbValue"] {
        color: #ffffff !important;
        font-family: var(--font-mono) !important;
        font-weight: 600 !important;
        font-size: 0.76rem !important;
        background: #181c24 !important;
        padding: 0.15rem 0.45rem !important;
        border-radius: 5px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }
    div[data-testid="stSlider"] label p {
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        color: #dfe2ee !important;
    }

    /* Radio Buttons (Material 3 Toggle Cards) */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.4rem;
    }
    div[data-testid="stRadio"] label {
        background: #181c24 !important;
        border: 1px solid rgba(62, 72, 80, 0.4) !important;
        border-radius: 10px !important;
        padding: 0.5rem 0.85rem !important;
        margin-bottom: 0.25rem !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] label:hover {
        background: #1c2028 !important;
        border-color: rgba(14, 165, 233, 0.4) !important;
    }

    /* Selectboxes and Inputs */
    div[data-baseweb="select"] > div {
        background-color: #181c24 !important;
        border: 1px solid rgba(62, 72, 80, 0.45) !important;
        border-radius: 10px !important;
        color: #dfe2ee !important;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 1px #0ea5e9 !important;
    }
    div[data-baseweb="input"] > div {
        background-color: #181c24 !important;
        border: 1px solid rgba(62, 72, 80, 0.45) !important;
        border-radius: 10px !important;
        color: #dfe2ee !important;
    }
    div[data-baseweb="input"] > div:hover,
    div[data-baseweb="input"] > div:focus-within {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 1px #0ea5e9 !important;
    }

    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }
    div[data-testid="stMetricLabel"] p {
        font-family: var(--font-mono) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        color: var(--text-muted) !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetricValue"] div {
        font-family: var(--font-mono) !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }

    /* App Chrome Minimal Polish */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        backdrop-filter: none !important;
    }
    .block-container {
        padding-top: 4.75rem !important;
        padding-bottom: 3rem !important;
        max-width: 98% !important;
    }

    /* Monospace Tablolar */
    div[data-testid="stDataFrame"] {
        font-family: var(--font-mono) !important;
        font-size: 0.81rem;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--outline-hairline);
    }

    /* Cupertino Info & Success Containers */
    .bess-info-box {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        border-left: 3px solid var(--accent-sky);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        font-size: 0.83rem;
        color: var(--text-secondary);
        line-height: 1.55;
        margin: 0.65rem 0;
    }
    .bess-success-box {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        border-left: 3px solid var(--accent-emerald);
        box-shadow: inset 0 1px 0 0 var(--outline-specular);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        font-size: 0.83rem;
        color: var(--text-secondary);
        line-height: 1.55;
        margin: 0.65rem 0;
    }
    .excel-download-card {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        box-shadow: inset 0 1px 0 0 var(--outline-specular), 0 8px 24px -4px rgba(0, 0, 0, 0.4);
        border-radius: 16px;
        padding: 1.35rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .excel-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .excel-desc {
        font-size: 0.84rem;
        color: var(--text-secondary);
        line-height: 1.6;
    }

    /* Günün Kibar Ufak KPI Kartları (5 Sütunlu Grid) */
    .daily-kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0.65rem;
        margin-top: 0.6rem;
        margin-bottom: 1.1rem;
    }
    @media (max-width: 1100px) {
        .daily-kpi-grid {
            grid-template-columns: repeat(3, 1fr);
        }
    }
    @media (max-width: 768px) {
        .daily-kpi-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    @media (max-width: 480px) {
        .daily-kpi-grid {
            grid-template-columns: 1fr;
        }
    }
    .mini-kpi-card {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-hairline);
        border-radius: 12px;
        padding: 0.75rem 0.95rem;
        box-shadow: inset 0 1px 0 0 var(--outline-specular), 0 3px 12px -2px rgba(0, 0, 0, 0.35);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 84px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .mini-kpi-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-1px);
    }
    .mini-kpi-card.highlight-profit {
        background: linear-gradient(135deg, rgba(78, 222, 163, 0.09) 0%, var(--surface-container-low) 100%);
        border-color: rgba(78, 222, 163, 0.35);
    }
    .mini-kpi-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.25rem;
    }
    .mini-kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .mini-kpi-badge {
        font-family: var(--font-mono);
        font-size: 0.65rem;
        font-weight: 600;
        padding: 0.1rem 0.4rem;
        border-radius: 9999px;
    }
    .mini-kpi-badge.emerald {
        background: rgba(78, 222, 163, 0.15);
        color: #4edea3;
        border: 1px solid rgba(78, 222, 163, 0.3);
    }
    .mini-kpi-value {
        font-family: var(--font-mono);
        font-size: 1.16rem;
        font-weight: 700;
        line-height: 1.25;
        letter-spacing: -0.02em;
        color: #ffffff;
    }
    .mini-kpi-value.emerald { color: #4edea3; }
    .mini-kpi-value.rose { color: #f87171; }
    .mini-kpi-value.sky { color: #38bdf8; }
    .mini-kpi-value.amber { color: #ffb95f; }
    .mini-kpi-value.slate { color: #94a3b8; }
    .mini-kpi-sub {
        font-size: 0.69rem;
        color: #64748b;
        margin-top: 0.25rem;
        font-family: var(--font-mono);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
"""


def make_icon_badge(svg_code: str, color: str = "#0ea5e9", bg: str = "rgba(14, 165, 233, 0.12)", border: str = "rgba(14, 165, 233, 0.28)", size: int = 28) -> str:
    """Apple SF Symbols ve Google Material 3 tarzı dairesel/köşeli cam rozet ikonu üretir."""
    return (
        f'<span style="display: inline-flex; align-items: center; justify-content: center; '
        f'width: {size}px; height: {size}px; border-radius: {size//3}px; background: {bg}; '
        f'border: 1px solid {border}; color: {color}; vertical-align: middle; flex-shrink: 0;">'
        f'{svg_code}'
        f'</span>'
    )


def clean_html(raw_html: str) -> str:
    """Streamlit markdown render hatasını önlemek için HTML bloklarındaki satır arası gereksiz boşlukları temizler."""
    import re
    return re.sub(r'>\s+<', '><', raw_html.strip())


