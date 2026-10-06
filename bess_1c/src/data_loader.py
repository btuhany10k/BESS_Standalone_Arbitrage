"""
EPİAŞ PTF Veri Yükleyici ve Temizleyici (Data Loader)
2024 ve 2025 PTF (TL, USD, EUR) verilerini yükler ve standartlaştırır.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd


def parse_turkish_float(val) -> float:
    """Türkçe sayı formatını (örn: '1.299,98' veya '44,16') float'a dönüştürür."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(" ", "")
    # Noktaları binlik ayracı olarak kaldır, virgülü noktaya çevir
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

    # Genellikle EPİAŞ CSV'leri noktalı virgül (;) ile ayrılır
    df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig")
    if df.shape[1] <= 1:
        # Alternatif ayraçlar
        for sep in [",", "\t"]:
            df = pd.read_csv(file_path, sep=sep, encoding="utf-8-sig")
            if df.shape[1] > 1:
                break

    # Sütun isimlerini temizle
    df.columns = [str(c).strip() for c in df.columns]

    # USD sütununu bul
    usd_col = None
    for c in df.columns:
        c_lower = c.lower()
        if "usd" in c_lower or "dolar" in c_lower:
            usd_col = c
            break

    tl_col = None
    for c in df.columns:
        c_lower = c.lower()
        if "tl" in c_lower or "try" in c_lower:
            tl_col = c
            break

    if usd_col is None:
        raise ValueError(f"{file_path} içinde USD bazlı PTF sütunu bulunamadı! Mevcut sütunlar: {df.columns.tolist()}")

    # Sayısal dönüşümler
    df["ptf_usd"] = df[usd_col].apply(parse_turkish_float)
    if tl_col:
        df["ptf_tl"] = df[tl_col].apply(parse_turkish_float)

    # Tarih ve Saat sütunlarını bul
    date_cols = [c for c in df.columns if "tarih" in c.lower() or "date" in c.lower()]
    hour_cols = [c for c in df.columns if "saat" in c.lower() or "hour" in c.lower()]

    if not date_cols or not hour_cols:
        raise ValueError(f"Tarih veya Saat sütunu eksik: {df.columns.tolist()}")

    date_col = date_cols[0]
    hour_col = hour_cols[0]

    df["tarih_str"] = df[date_col].astype(str).str.strip()
    df["saat_str"] = df[hour_col].astype(str).str.strip()

    # Saat numarasını al (0-23)
    df["hour"] = df["saat_str"].apply(lambda x: int(str(x).split(":")[0]) if ":" in str(x) else int(x))

    # Tarih parsing (DD.MM.YYYY)
    df["date"] = pd.to_datetime(df["tarih_str"], format="%d.%m.%Y", errors="coerce")
    if df["date"].isna().any():
        df["date"] = pd.to_datetime(df["tarih_str"], dayfirst=True)

    df["datetime"] = df["date"] + pd.to_timedelta(df["hour"], unit="h")
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()

    cols_to_keep = ["datetime", "date", "year", "month", "day", "hour", "saat_str", "ptf_usd"]
    if "ptf_tl" in df.columns:
        cols_to_keep.append("ptf_tl")

    cleaned = df[cols_to_keep].sort_values("datetime").reset_index(drop=True)
    return cleaned


def load_all_ptf_data(base_dir: Path | str = ".") -> Dict[int, pd.DataFrame]:
    """2024 ve 2025 PTF dosyalarını yükleyip sözlük olarak döndürür."""
    base_dir = Path(base_dir)
    data = {}

    candidates = {
        2024: [
            base_dir / "PTF2024.csv",
            base_dir / "ptf_2024.csv",
            base_dir / "data" / "PTF2024.csv",
            base_dir.parent / "data" / "PTF2024.csv",
            base_dir.parent / "data" / "ptf_2024.csv",
        ],
        2025: [
            base_dir / "PTF2025.csv",
            base_dir / "ptf_2025.csv",
            base_dir / "data" / "PTF2025.csv",
            base_dir.parent / "data" / "PTF2025.csv",
            base_dir.parent / "data" / "ptf_2025.csv",
        ],
    }

    for year, paths in candidates.items():
        for p in paths:
            if p.exists():
                data[year] = load_ptf_file(p)
                break

    return data
