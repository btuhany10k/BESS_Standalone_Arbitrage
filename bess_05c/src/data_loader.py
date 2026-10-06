"""
BESS 0.5C Projesi - EPİAŞ PTF Veri Yükleyici (Data Loader)
2024 ve 2025 EPİAŞ Piyasa Takas Fiyatı (PTF) saatlik verilerini yükler ve standartlaştırır.
"""

from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd


def parse_turkish_float(val) -> float:
    """Türkçe sayı formatını float'a dönüştürür (örn: '1.299,98' -> 1299.98)."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(" ", "")
    val_str = val_str.replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return np.nan


def load_ptf_file(file_path: Path | str) -> pd.DataFrame:
    """Tek bir EPİAŞ PTF CSV dosyasını okur ve temizler."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PTF dosyası bulunamadı: {file_path}")

    # Genellikle noktalı virgül (;) veya virgül (,)
    df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig")
    if df.shape[1] <= 1:
        for sep in [",", "\t"]:
            df = pd.read_csv(file_path, sep=sep, encoding="utf-8-sig")
            if df.shape[1] > 1:
                break

    df.columns = [str(c).strip() for c in df.columns]

    # USD sütunu
    usd_col = None
    for c in df.columns:
        c_lower = c.lower()
        if "usd" in c_lower or "dolar" in c_lower:
            usd_col = c
            break

    if usd_col is None:
        raise ValueError(f"{file_path} dosyasında USD bazlı PTF sütunu bulunamadı.")

    df["ptf_usd"] = df[usd_col].apply(parse_turkish_float)

    # Tarih ve saat
    date_cols = [c for c in df.columns if "tarih" in c.lower() or "date" in c.lower()]
    hour_cols = [c for c in df.columns if "saat" in c.lower() or "hour" in c.lower()]

    if not date_cols or not hour_cols:
        raise ValueError("Tarih veya saat sütunu eksik.")

    df["tarih_str"] = df[date_cols[0]].astype(str).str.strip()
    df["saat_str"] = df[hour_cols[0]].astype(str).str.strip()

    df["hour"] = df["saat_str"].apply(lambda x: int(str(x).split(":")[0]) if ":" in str(x) else int(x))
    df["date"] = pd.to_datetime(df["tarih_str"], format="%d.%m.%Y", errors="coerce")
    if df["date"].isna().any():
        df["date"] = pd.to_datetime(df["tarih_str"], dayfirst=True)

    df["datetime"] = df["date"] + pd.to_timedelta(df["hour"], unit="h")
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()

    cols_to_keep = ["datetime", "date", "year", "month", "day", "hour", "saat_str", "ptf_usd"]
    cleaned = df[cols_to_keep].sort_values("datetime").reset_index(drop=True)
    return cleaned


def load_all_ptf_data(base_dirs: Optional[list] = None) -> Dict[int, pd.DataFrame]:
    """2024 ve 2025 PTF dosyalarını tarayıp yükler."""
    if base_dirs is None:
        current_dir = Path(__file__).resolve().parent.parent
        parent_dir = current_dir.parent
        base_dirs = [current_dir, parent_dir, parent_dir / "data", current_dir / "data"]

    data = {}
    for year in [2024, 2025]:
        found = False
        for b in base_dirs:
            candidates = [
                b / f"PTF{year}.csv",
                b / f"ptf_{year}.csv",
                b / f"PTF_{year}.csv",
            ]
            for p in candidates:
                if p.exists():
                    data[year] = load_ptf_file(p)
                    found = True
                    break
            if found:
                break
    return data
