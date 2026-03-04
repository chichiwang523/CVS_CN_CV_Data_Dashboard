"""电驱动深度分析 — 电驱桥 vs 集中驱动、TZ型号、电机供应商"""
from __future__ import annotations
import pandas as pd
import numpy as np
from src.config import BATCH_DATES


def drive_topology_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    return bev["parsed_drive_topology"].value_counts().reset_index().rename(
        columns={"index": "topology", "count": "count", "parsed_drive_topology": "topology"}
    )


def drive_topology_trend(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    out = bev.groupby(["batch", "parsed_drive_topology"]).size().reset_index(name="count")
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def eaxle_supplier_share(df: pd.DataFrame) -> pd.DataFrame:
    eaxle = df[df["parsed_drive_topology"] == "电驱桥(参考)"]
    from src.data_cleaner import _display_name
    return (
        eaxle["engine_maker_display"]
        .value_counts()
        .head(10)
        .reset_index()
        .rename(columns={"index": "supplier", "count": "count", "engine_maker_display": "supplier"})
    )


def tz_number_vs_power(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[(df["energy_clean"] == "纯电动") & (df["parsed_tz_number"].notna())]
    bev = bev[bev["power_kw"] > 0]
    return bev[["parsed_tz_number", "power_kw", "parsed_tz_suffix_type",
                "parsed_tz_maker_code", "vehicle_category", "mass_class"]].copy()


def tz_suffix_type_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[(df["energy_clean"] == "纯电动") & (df["parsed_tz_suffix_type"] != "")]
    return bev["parsed_tz_suffix_type"].value_counts().reset_index().rename(
        columns={"index": "suffix", "count": "count", "parsed_tz_suffix_type": "suffix"}
    )


def tz_maker_code_distribution(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    bev = df[(df["energy_clean"] == "纯电动") & (df["parsed_tz_maker_code"] != "")]
    return bev["parsed_tz_maker_code"].value_counts().head(n).reset_index().rename(
        columns={"index": "code", "count": "count", "parsed_tz_maker_code": "code"}
    )


def bev_by_mass_class(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    out = bev.groupby(["batch", "mass_class"]).size().reset_index(name="count")
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def eaxle_trend(df: pd.DataFrame) -> pd.DataFrame:
    bev = df[df["energy_clean"] == "纯电动"]
    rows = []
    for batch, g in bev.groupby("batch"):
        total_bev = len(g)
        eaxle = (g["parsed_drive_topology"] == "电驱桥(参考)").sum()
        rows.append({
            "batch": batch,
            "batch_date": BATCH_DATES.get(batch, ""),
            "total_bev": total_bev,
            "eaxle_count": eaxle,
            "eaxle_ratio": eaxle / total_bev if total_bev else 0,
        })
    return pd.DataFrame(rows)
