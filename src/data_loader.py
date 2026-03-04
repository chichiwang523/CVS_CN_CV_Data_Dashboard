"""
数据加载与 Parquet 缓存管理
- 首次运行：读取 99 个 JSON -> 合并 DataFrame -> 写 Parquet (~150 MB)
- 后续运行：直接读 Parquet (< 3 s)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import DATA_DIR, CACHE_DIR, RAW_PARQUET, CLEANED_PARQUET, BATCH_RANGE


def _list_batch_jsons(data_dir: Path = DATA_DIR) -> list[Path]:
    files = sorted(
        data_dir.glob("vehicle_data_batch_*.json"),
        key=lambda p: int(p.stem.split("_")[-1]),
    )
    return files


def build_raw_parquet(force: bool = False) -> Path:
    """将全量 JSON 合并为单一 Parquet 文件，返回路径。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_PARQUET.exists() and not force:
        return RAW_PARQUET

    json_files = _list_batch_jsons()
    if not json_files:
        raise FileNotFoundError(f"在 {DATA_DIR} 中未找到 vehicle_data_batch_*.json 文件")

    frames: list[pd.DataFrame] = []
    t0 = time.time()
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        records = raw.get("data", raw) if isinstance(raw, dict) else raw
        if isinstance(records, dict):
            records = list(records.values())
        df = pd.DataFrame(records)
        frames.append(df)

    merged = pd.concat(frames, ignore_index=True)
    elapsed = time.time() - t0
    print(f"[data_loader] 读取 {len(json_files)} 个 JSON, {len(merged)} 条记录, 耗时 {elapsed:.1f}s")

    _numeric_cols = [
        "total_mass", "curb_weight", "axle_count", "length", "width",
        "displacement", "power_kw", "fuel_consumption", "motor_power",
    ]
    for col in _numeric_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")

    # height / max_speed 等字段可能含逗号分隔的多值（"3500,3700"），保留为字符串
    _str_cols = ["height", "max_speed", "emission_standard"]
    for col in _str_cols:
        if col in merged.columns:
            merged[col] = merged[col].astype(str).replace("nan", None)

    if "batch" in merged.columns:
        merged["batch"] = merged["batch"].astype(int)

    # 确保所有 object 列统一为 string 以避免 pyarrow 混合类型报错
    for col in merged.select_dtypes(include=["object"]).columns:
        merged[col] = merged[col].astype("string")

    merged.to_parquet(RAW_PARQUET, engine="pyarrow", index=False)
    size_mb = RAW_PARQUET.stat().st_size / 1024 / 1024
    print(f"[data_loader] Parquet 写入 {RAW_PARQUET} ({size_mb:.1f} MB)")
    return RAW_PARQUET


def load_raw(batches: Optional[list[int]] = None) -> pd.DataFrame:
    """加载原始 Parquet，可选按批次筛选。"""
    if not RAW_PARQUET.exists():
        build_raw_parquet()
    df = pd.read_parquet(RAW_PARQUET)
    if batches:
        df = df[df["batch"].isin(batches)]
    return df


def load_cleaned(batches: Optional[list[int]] = None) -> pd.DataFrame:
    """加载清洗后 Parquet；若不存在则先跑清洗流水线。"""
    if not CLEANED_PARQUET.exists():
        from src.data_cleaner import run_full_clean
        run_full_clean()
    df = pd.read_parquet(CLEANED_PARQUET)
    if batches:
        df = df[df["batch"].isin(batches)]
    return df


def available_batches() -> list[int]:
    """返回已有数据的批次列表。"""
    if RAW_PARQUET.exists():
        df = pd.read_parquet(RAW_PARQUET, columns=["batch"])
        return sorted(df["batch"].unique().tolist())
    jsons = _list_batch_jsons()
    return sorted(int(p.stem.split("_")[-1]) for p in jsons)
