"""统计接口"""
from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


def _get_df():
    from src.data_loader import load_cleaned
    return load_cleaned()


def _filter_batch(df, batch_start=None, batch_end=None, batch=None):
    if batch:
        return df[df["batch"].isin(batch)]
    if batch_start and batch_end:
        return df[df["batch"].between(batch_start, batch_end)]
    return df


@router.get("/energy_distribution")
def energy_distribution(
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
):
    df = _filter_batch(_get_df(), batch_start, batch_end, batch)
    dist = df["energy_clean"].value_counts().to_dict()
    return {"total_records": len(df), "data": dist}


@router.get("/top_manufacturers")
def top_manufacturers(
    n: int = 10,
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
):
    df = _filter_batch(_get_df(), batch_start, batch_end, batch)
    top = df["manufacturer_display"].value_counts().head(n).to_dict()
    return {"total_records": len(df), "data": top}


@router.get("/abs_market_share")
def abs_market_share(
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
):
    df = _filter_batch(_get_df(), batch_start, batch_end, batch)
    from src.analysis.braking import abs_supplier_share_fast
    share = abs_supplier_share_fast(df)
    total_abs = share["count"].sum()
    result = {}
    for _, row in share.iterrows():
        result[row["supplier"]] = {
            "count": int(row["count"]),
            "ratio": round(row["count"] / total_abs, 4) if total_abs else 0,
        }
    return {"total_abs_records": int(total_abs), "data": result}


@router.get("/bev_analysis")
def bev_analysis(
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
):
    df = _filter_batch(_get_df(), batch_start, batch_end, batch)
    bev = df[df["energy_clean"] == "纯电动"]
    result = {
        "bev_count": len(bev),
        "bev_ratio": round(len(bev) / len(df), 4) if len(df) else 0,
        "drive_topology": bev["parsed_drive_topology"].value_counts().to_dict(),
        "battery_chemistry": bev["parsed_battery_chemistry"].value_counts().to_dict(),
        "motor_suppliers_top10": bev["engine_maker_display"].value_counts().head(10).to_dict(),
    }
    return {"total_records": len(df), "data": result}


@router.get("/competitor_mentions")
def competitor_mentions(
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
):
    df = _filter_batch(_get_df(), batch_start, batch_end, batch)
    return {
        "total_records": len(df),
        "data": {
            "ZF/威伯科": int(df["parsed_zf_mention"].sum()),
            "Bosch/博世": int(df["parsed_bosch_mention"].sum()),
            "Knorr/克诺尔": int(df["parsed_knorr_mention"].sum()),
        },
    }
