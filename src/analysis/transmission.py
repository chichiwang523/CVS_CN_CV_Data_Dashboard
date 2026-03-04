"""变速箱分析"""
from __future__ import annotations
import pandas as pd
from src.config import BATCH_DATES


def transmission_type_distribution(df: pd.DataFrame) -> pd.DataFrame:
    has_tt = df[df["transmission_type"].notna() & (df["transmission_type"] != "") & (df["transmission_type"] != "<NA>")]
    return has_tt["transmission_type"].value_counts().reset_index().rename(
        columns={"index": "type", "count": "count", "transmission_type": "type"}
    )


def transmission_by_energy(df: pd.DataFrame) -> pd.DataFrame:
    has_tt = df[df["transmission_type"].notna() & (df["transmission_type"] != "") & (df["transmission_type"] != "<NA>")]
    return has_tt.groupby(["energy_clean", "transmission_type"]).size().reset_index(name="count")


def transmission_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """变速箱字段覆盖率按批次。"""
    rows = []
    for batch, g in df.groupby("batch"):
        total = len(g)
        has_type = g["transmission_type"].notna() & (g["transmission_type"] != "") & (g["transmission_type"] != "<NA>")
        rows.append({
            "batch": batch,
            "batch_date": BATCH_DATES.get(batch, ""),
            "total": total,
            "has_transmission_type": has_type.sum(),
            "coverage": has_type.sum() / total if total else 0,
        })
    return pd.DataFrame(rows)
