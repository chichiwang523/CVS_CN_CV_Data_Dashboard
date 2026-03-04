"""竞争对手综合分析 — ZF vs Bosch vs Knorr"""
from __future__ import annotations
import pandas as pd
from src.config import BATCH_DATES


def competitor_mention_trend(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for batch, g in df.groupby("batch"):
        total = len(g)
        rows.append({
            "batch": batch,
            "batch_date": BATCH_DATES.get(batch, ""),
            "total": total,
            "ZF/威伯科": g["parsed_zf_mention"].sum(),
            "Bosch/博世": g["parsed_bosch_mention"].sum(),
            "Knorr/克诺尔": g["parsed_knorr_mention"].sum(),
        })
    out = pd.DataFrame(rows)
    for col in ["ZF/威伯科", "Bosch/博世", "Knorr/克诺尔"]:
        out[f"{col}_ratio"] = out[col] / out["total"]
    return out


def competitor_by_vehicle_category(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cat, g in df.groupby("vehicle_category"):
        total = len(g)
        rows.append({
            "vehicle_category": cat,
            "total": total,
            "ZF/威伯科": g["parsed_zf_mention"].sum(),
            "Bosch/博世": g["parsed_bosch_mention"].sum(),
            "Knorr/克诺尔": g["parsed_knorr_mention"].sum(),
        })
    out = pd.DataFrame(rows)
    for col in ["ZF/威伯科", "Bosch/博世", "Knorr/克诺尔"]:
        out[f"{col}_ratio"] = out[col] / out["total"]
    return out.sort_values("total", ascending=False)


def competitor_by_manufacturer(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Top N 主机厂与竞争对手的配对关系。"""
    top_mfr = df["manufacturer_display"].value_counts().head(n).index.tolist()
    sub = df[df["manufacturer_display"].isin(top_mfr)]
    rows = []
    for mfr, g in sub.groupby("manufacturer_display"):
        rows.append({
            "manufacturer": mfr,
            "total": len(g),
            "ZF/威伯科": g["parsed_zf_mention"].sum(),
            "Bosch/博世": g["parsed_bosch_mention"].sum(),
            "Knorr/克诺尔": g["parsed_knorr_mention"].sum(),
        })
    return pd.DataFrame(rows).sort_values("total", ascending=False)
