"""Pydantic 模型"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class VehicleQuery(BaseModel):
    batches: Optional[list[int]] = None
    energy_type: Optional[str] = None
    vehicle_category: Optional[str] = None
    manufacturer: Optional[str] = None
    keyword: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
    fields: Optional[list[str]] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list[dict]


class StatsResponse(BaseModel):
    batch_range: Optional[str] = None
    total_records: int
    data: dict
