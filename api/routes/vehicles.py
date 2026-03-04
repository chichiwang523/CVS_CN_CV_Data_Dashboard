"""车辆查询接口"""
from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Optional
import math

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


def _get_df():
    from src.data_loader import load_cleaned
    return load_cleaned()


@router.get("/")
def query_vehicles(
    batch: Optional[list[int]] = Query(None),
    batch_start: Optional[int] = None,
    batch_end: Optional[int] = None,
    energy_type: Optional[str] = None,
    vehicle_category: Optional[str] = None,
    manufacturer: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fields: Optional[str] = None,
):
    df = _get_df()

    if batch:
        df = df[df["batch"].isin(batch)]
    elif batch_start and batch_end:
        df = df[df["batch"].between(batch_start, batch_end)]

    if energy_type:
        df = df[df["energy_clean"] == energy_type]
    if vehicle_category:
        df = df[df["vehicle_category"] == vehicle_category]
    if manufacturer:
        df = df[df["manufacturer"].fillna("").str.contains(manufacturer, case=False, na=False)]
    if keyword:
        mask = (
            df["brand"].fillna("").str.contains(keyword, case=False, na=False) |
            df["model_code"].fillna("").str.contains(keyword, case=False, na=False) |
            df["engine_maker"].fillna("").str.contains(keyword, case=False, na=False)
        )
        df = df[mask]

    total = len(df)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size

    if fields:
        cols = [c.strip() for c in fields.split(",") if c.strip() in df.columns]
    else:
        cols = [
            "batch", "batch_date", "model_code", "brand", "vehicle_type",
            "manufacturer_display", "energy_clean", "power_kw", "total_mass",
            "engine_maker_display", "abs_maker_display",
        ]

    records = df[cols].iloc[start:start + page_size].fillna("").to_dict(orient="records")

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "data": records,
    }
