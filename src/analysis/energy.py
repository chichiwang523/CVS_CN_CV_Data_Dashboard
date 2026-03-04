"""电动化与电池分析"""
from __future__ import annotations
import pandas as pd
import numpy as np
from src.config import BATCH_DATES


def bev_trend(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for batch, g in df.groupby("batch"):
        total = len(g)
        bev = (g["energy_clean"] == "纯电动").sum()
        fcev = (g["energy_clean"] == "氢燃料电池").sum()
        phev = (g["energy_clean"] == "插电混动").sum()
        rows.append({
            "batch": batch,
            "batch_date": BATCH_DATES.get(batch, ""),
            "total": total,
            "bev": bev, "bev_ratio": bev / total if total else 0,
            "fcev": fcev, "fcev_ratio": fcev / total if total else 0,
            "phev": phev, "phev_ratio": phev / total if total else 0,
            "nev_ratio": (bev + fcev + phev) / total if total else 0,
        })
    return pd.DataFrame(rows)


def bev_vehicle_types(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    return bev.groupby("vehicle_category").size().reset_index(name="count").sort_values("count", ascending=False)


def bev_motor_suppliers(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    return (
        bev["engine_maker_display"]
        .value_counts()
        .head(n)
        .reset_index()
        .rename(columns={"index": "supplier", "count": "count", "engine_maker_display": "supplier"})
    )


def bev_power_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[(df["energy_clean"] == "纯电动") & (df["power_kw"] > 0) & (df["power_kw"] < 1000)]
    return bev[["power_kw", "vehicle_category", "mass_class"]].copy()


def battery_chemistry_trend(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    out = bev.groupby(["batch", "parsed_battery_chemistry"]).size().reset_index(name="count")
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def battery_chemistry_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    return bev["parsed_battery_chemistry"].value_counts().reset_index().rename(
        columns={"index": "chemistry", "count": "count", "parsed_battery_chemistry": "chemistry"}
    )


def battery_cell_suppliers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    makers = bev["parsed_battery_cell_makers"].dropna().astype(str)
    all_makers = makers[makers != ""].str.split("|").explode()
    all_makers = all_makers[all_makers.str.len() > 4]
    # 清洗：去掉明显不是企业名的条目
    from src.data_cleaner import _display_name
    counts = all_makers.value_counts().head(n).reset_index()
    counts.columns = ["supplier", "count"]
    counts["display"] = counts["supplier"].apply(_display_name)
    return counts


def battery_pack_suppliers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    makers = bev["parsed_battery_pack_makers"].dropna().astype(str)
    all_makers = makers[makers != ""].str.split("|").explode()
    all_makers = all_makers[all_makers.str.len() > 4]
    from src.data_cleaner import _display_name
    counts = all_makers.value_counts().head(n).reset_index()
    counts.columns = ["supplier", "count"]
    counts["display"] = counts["supplier"].apply(_display_name)
    return counts


def battery_capacity_stats(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    has_kwh = bev[bev["parsed_battery_kwh"].notna() & (bev["parsed_battery_kwh"] > 0)]
    return has_kwh[["parsed_battery_kwh", "power_kw", "total_mass", "vehicle_category", "mass_class"]].copy()
