"""市场概览与趋势分析"""
from __future__ import annotations
import pandas as pd
from src.config import BATCH_DATES


def overview_kpis(df: pd.DataFrame) -> dict:
    return {
        "total_records": len(df),
        "total_batches": df["batch"].nunique(),
        "batch_range": f"{df['batch'].min()}-{df['batch'].max()}",
        "total_manufacturers": df["manufacturer"].nunique(),
        "total_brands": df["brand"].nunique(),
        "energy_types": df["energy_clean"].nunique(),
        "vehicle_types": df["vehicle_type"].nunique(),
        "bev_count": (df["energy_clean"] == "纯电动").sum(),
        "bev_ratio": (df["energy_clean"] == "纯电动").mean(),
    }


def batch_record_counts(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("batch").size().reset_index(name="count")
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def energy_distribution_by_batch(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby(["batch", "energy_clean"]).size().reset_index(name="count")
    total = df.groupby("batch").size().reset_index(name="total")
    out = out.merge(total, on="batch")
    out["ratio"] = out["count"] / out["total"]
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def top_manufacturers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby("manufacturer_display")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(n)
    )


def manufacturer_trend(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    top = top_manufacturers(df, n)["manufacturer_display"].tolist()
    sub = df[df["manufacturer_display"].isin(top)]
    out = sub.groupby(["batch", "manufacturer_display"]).size().reset_index(name="count")
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def vehicle_type_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["vehicle_category", "vehicle_type"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def mass_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["mass_class", "energy_clean"]).size().reset_index(name="count")


def concentration_trend(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """CR-N 集中度趋势"""
    rows = []
    for batch, g in df.groupby("batch"):
        total = len(g)
        top = g["manufacturer_display"].value_counts().head(top_n).sum()
        rows.append({"batch": batch, "batch_date": BATCH_DATES.get(batch, ""), f"CR{top_n}": top / total if total else 0})
    return pd.DataFrame(rows)
