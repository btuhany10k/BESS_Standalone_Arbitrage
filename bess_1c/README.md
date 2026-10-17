# BESS Standalone Arbitrage Platform
## Battery Energy Storage Systems (BESS) Arbitrage & Feasibility Dashboard

This repository provides simulation, optimization, and feasibility analytics for utility-scale battery energy storage systems (BESS) participating in Day-Ahead electricity markets.

---

### 🔋 Standalone BESS Arbitrage Strategy (1C Storage)
- **Configuration:** 1C / 1-Hour Storage Duration (e.g. 50 MW / 50 MWh)
- **Mathematical Optimization Engine:** Full-block economic dispatch and dual-cycling heuristic optimizer
- **Features:**
  - 1-Cycle (Single Block) and Up to 2-Cycles (Dual Block) dispatch strategies
  - Operator State of Charge (SoC) management (day-start & day-end target constraints)
  - Cell degradation cost & efficiency loss economic filtering (standby when unprofitable)
  - 24-hour interactive dispatch profile (price, power, and SoC trajectory)
  - Monthly and annual financial breakdown tables and charts
  - Incremental monthly benefit curve for additional cycling
  - Multi-year (2024 vs 2025) comparative performance benchmarking
  - Comprehensive 5-sheet audit-ready Excel report export (`.xlsx`)
- **Web App:** Deployed on Streamlit Cloud

---

### 📊 Dataset (`data/`)
The platform uses real hourly Day-Ahead market price ($/MWh) datasets:
- `data/PTF2024.csv`: 2024 hourly prices (8,784 records, leap year)
- `data/PTF2025.csv`: 2025 hourly prices (8,760 records, full year)

---

### 🚀 Quick Start (Local Run)
```bash
# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit application
streamlit run app.py
```
