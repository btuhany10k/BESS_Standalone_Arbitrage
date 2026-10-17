"""
Day-Ahead Market Price Data Loader and Cleaner
Loads and standardizes historical 2024 and 2025 hourly market price data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd


def parse_turkish_float(val) -> float:
    """Parses European / Turkish number strings (e.g. '1.299,98' or '44,16') into standard float."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(" ", "")
    # Remove thousand dots and replace decimal comma with dot
    val_str = val_str.replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return np.nan


def load_ptf_file(file_path: Union[Path, str]) -> pd.DataFrame:
    """Reads and cleans a single day-ahead price CSV file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Price file not found: {file_path}")

    df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig")
    if df.shape[1] <= 1:
        for sep in [",", "\t"]:
            df = pd.read_csv(file_path, sep=sep, encoding="utf-8-sig")
            if df.shape[1] > 1:
                break

    df.columns = [str(c).strip() for c in df.columns]

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
        raise ValueError(f"USD price column not found in {file_path}! Available columns: {df.columns.tolist()}")

    df["ptf_usd"] = df[usd_col].apply(parse_turkish_float)
    if tl_col:
        df["ptf_tl"] = df[tl_col].apply(parse_turkish_float)

    date_cols = [c for c in df.columns if "tarih" in c.lower() or "date" in c.lower()]
    hour_cols = [c for c in df.columns if "saat" in c.lower() or "hour" in c.lower()]

    if not date_cols or not hour_cols:
        raise ValueError(f"Date or Hour column missing in: {df.columns.tolist()}")

    date_col = date_cols[0]
    hour_col = hour_cols[0]

    df["tarih_str"] = df[date_col].astype(str).str.strip()
    df["saat_str"] = df[hour_col].astype(str).str.strip()

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
    if "ptf_tl" in df.columns:
        cols_to_keep.append("ptf_tl")

    cleaned = df[cols_to_keep].sort_values("datetime").reset_index(drop=True)
    return cleaned


def load_all_ptf_data(base_dir: Union[Path, str] = ".") -> Dict[int, pd.DataFrame]:
    """Loads 2024 and 2025 price datasets into a dictionary."""
    base_dir = Path(base_dir)
    data = {}
    cwd = Path.cwd()

    for year in [2024, 2025]:
        file_parent = Path(__file__).resolve().parent.parent
        candidates = [
            base_dir / f"PTF{year}.csv",
            base_dir / f"ptf_{year}.csv",
            base_dir / "data" / f"PTF{year}.csv",
            base_dir.parent / "data" / f"PTF{year}.csv",
            base_dir.parent / f"PTF{year}.csv",
            file_parent / "data" / f"PTF{year}.csv",
            file_parent.parent / "data" / f"PTF{year}.csv",
            cwd / f"PTF{year}.csv",
            cwd / "data" / f"PTF{year}.csv",
            cwd / "bess_1c" / "data" / f"PTF{year}.csv",
            cwd / "bess_05c" / "data" / f"PTF{year}.csv",
        ]
        for p in candidates:
            if p.exists():
                try:
                    data[year] = load_ptf_file(p)
                    break
                except Exception:
                    continue

    return data
