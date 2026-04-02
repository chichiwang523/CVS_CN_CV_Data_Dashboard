"""
零售（上牌/保险）月度数据加载器
读取 CVdata/2025年*月商用车零售统计表.xlsx → 清洗 → 缓存为 Parquet
提供两种粒度：demo（轻量 13 列）和 full（含型号/配置等完整字段，用于对比分析）
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, CACHE_DIR

RETAIL_PARQUET = CACHE_DIR / "retail_demo_2025.parquet"
RETAIL_FULL_PARQUET = CACHE_DIR / "retail_full_2025.parquet"

_KEEP_COLS = [
    "年月", "车辆名称", "车辆类型", "载货车分类（按功能用途）",
    "底盘企业简称", "马力_hp", "燃料种类", "数量",
]

_KEEP_COLS_FULL = [
    "年月", "车辆型号", "底盘型号", "制造厂名称", "品牌", "企业简称",
    "底盘企业简称", "车辆类型", "车辆名称", "载货车分类（按功能用途）",
    "功率_kw", "马力_hp", "排量_ml", "总质量", "整备质量",
    "轴数", "驱动形式", "发动机型号", "发动机企业", "排放水平",
    "燃料种类", "省份", "城市", "数量",
]

_NUMERIC_FULL = ["功率_kw", "排量_ml", "总质量", "整备质量", "马力_hp"]


def _retail_files() -> list[Path]:
    return sorted(DATA_DIR.glob("2025年*月商用车零售统计表.xlsx"))


def _safe_str(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


def _map_fuel_hybrid_phev_other(v: str) -> str:
    fuel = _safe_str(v)
    if not fuel:
        return "Other fuels"
    if "插电式混合动力" in fuel:
        return "PHEV"
    if "混合动力" in fuel:
        return "Hybrid"
    if fuel in ("纯电动", "燃料电池"):
        return fuel
    return "Other fuels"


def _map_fuel_ng(v: str) -> str:
    fuel = _safe_str(v).upper()
    if not fuel:
        return "未知"
    if fuel in {"天然气", "LNG", "CNG", "NG", "CNG,LNG"}:
        return "NG"
    return _safe_str(v)


def _extract_year_month(series: pd.Series):
    year_list, month_list = [], []
    for v in series:
        s = _safe_str(v)
        m = re.match(r"(\d{4})(\d{2})", s)
        if m:
            year_list.append(int(m.group(1)))
            month_list.append(int(m.group(2)))
        else:
            year_list.append(None)
            month_list.append(None)
    return pd.array(year_list, dtype=pd.Int64Dtype()), pd.array(month_list, dtype=pd.Int64Dtype())


# ── Demo 版（轻量，09 页面用） ─────────────────────────

def _read_one(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    keep = [c for c in _KEEP_COLS if c in df.columns]
    df = df[keep].copy()
    df["马力_hp"] = pd.to_numeric(df.get("马力_hp"), errors="coerce")
    df["数量"] = pd.to_numeric(df.get("数量"), errors="coerce").fillna(0).astype(int)
    df["fuel_map_hybrid_phev_other"] = df["燃料种类"].map(_map_fuel_hybrid_phev_other)
    df["fuel_map_ng"] = df["燃料种类"].map(_map_fuel_ng)
    df["source_file"] = path.name
    return df


def build_retail_demo_parquet(force: bool = False) -> Path:
    if RETAIL_PARQUET.exists() and not force:
        return RETAIL_PARQUET
    files = _retail_files()
    if not files:
        raise FileNotFoundError(f"未找到零售 Excel: {DATA_DIR}/2025年*月商用车零售统计表.xlsx")
    frames = [_read_one(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    years, months = _extract_year_month(df["年月"])
    df.insert(0, "年", years)
    df.insert(1, "月", months)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RETAIL_PARQUET, index=False)
    return RETAIL_PARQUET


def load_retail_demo(force_rebuild: bool = False) -> pd.DataFrame:
    if not RETAIL_PARQUET.exists() or force_rebuild:
        build_retail_demo_parquet(force=True)
    return pd.read_parquet(RETAIL_PARQUET, dtype_backend="pyarrow")


# ── Full 版（含型号等完整字段，对比分析用） ──────────────

def _read_one_full(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    keep = [c for c in _KEEP_COLS_FULL if c in df.columns]
    df = df[keep].copy()
    for c in _NUMERIC_FULL:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["数量"] = pd.to_numeric(df.get("数量"), errors="coerce").fillna(0).astype(int)
    df["fuel_map_hybrid_phev_other"] = df["燃料种类"].map(_map_fuel_hybrid_phev_other)
    df["fuel_map_ng"] = df["燃料种类"].map(_map_fuel_ng)
    df["source_file"] = path.name
    return df


def build_retail_full_parquet(force: bool = False) -> Path:
    if RETAIL_FULL_PARQUET.exists() and not force:
        return RETAIL_FULL_PARQUET
    files = _retail_files()
    if not files:
        raise FileNotFoundError(f"未找到零售 Excel: {DATA_DIR}/2025年*月商用车零售统计表.xlsx")
    frames = [_read_one_full(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    years, months = _extract_year_month(df["年月"])
    df.insert(0, "年", years)
    df.insert(1, "月", months)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RETAIL_FULL_PARQUET, index=False)
    return RETAIL_FULL_PARQUET


def load_retail_full(force_rebuild: bool = False) -> pd.DataFrame:
    if not RETAIL_FULL_PARQUET.exists() or force_rebuild:
        build_retail_full_parquet(force=True)
    return pd.read_parquet(RETAIL_FULL_PARQUET, dtype_backend="pyarrow")
