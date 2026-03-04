"""
数据清洗流水线
- engine_maker 拆分（取首个企业做主字段）
- 能源类型修正（Gasoline 含柴油区分）
- 企业名显示名清洗
- 车辆大类 / 质量分级
- 调用 remarks_parser 做备注结构化
- 输出 cleaned Parquet
"""
from __future__ import annotations

import re
import time

import numpy as np
import pandas as pd

from src.config import (
    CLEANED_PARQUET, CACHE_DIR, BATCH_DATES,
    ENERGY_TYPE_MAP, classify_vehicle, classify_mass,
)
from src.data_loader import load_raw, build_raw_parquet, RAW_PARQUET
from src.remarks_parser import parse_remarks


# ── engine_maker 拆分 ─────────────────────────────────

def _split_maker(raw: str) -> str:
    """取拼接企业名中的第一个完整企业名。"""
    if not raw or raw == "<NA>":
        return ""
    parts = re.split(r'(?<=有限公司)|(?<=股份有限公司)', raw)
    for p in parts:
        p = p.strip().lstrip("/")
        if len(p) >= 4 and ("公司" in p or "集团" in p):
            return p
    return raw[:40] if len(raw) > 40 else raw


def _display_name(full: str) -> str:
    """去除企业后缀用于图表显示。"""
    if not full:
        return ""
    name = full
    for suffix in ["股份有限公司", "有限责任公司", "有限公司", "(中国)", "（中国）"]:
        name = name.replace(suffix, "")
    return name.strip()


# ── 能源类型修正 ──────────────────────────────────────

_DIESEL_EMISSION = re.compile(r'GB17691|GB\s*3847')


def _fix_energy_type(row) -> str:
    """将 Gasoline 中的柴油车区分出来。"""
    etype = str(row.get("energy_type", ""))
    ename = str(row.get("energy_type_name", ""))

    mapped = ENERGY_TYPE_MAP.get(etype, ename if ename and ename != "<NA>" else "未知")
    if mapped == "传统燃料":
        emission = str(row.get("emission_standard", ""))
        disp = row.get("displacement", None)
        if _DIESEL_EMISSION.search(emission):
            return "柴油"
        if disp and disp == disp and disp > 2500:
            return "柴油"
        return "汽油"
    return mapped


# ── 主清洗流程 ────────────────────────────────────────

def run_full_clean(force: bool = False) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if CLEANED_PARQUET.exists() and not force:
        return pd.read_parquet(CLEANED_PARQUET)

    if not RAW_PARQUET.exists():
        build_raw_parquet()

    t0 = time.time()
    print("[cleaner] 加载原始 Parquet ...")
    df = load_raw()
    print(f"[cleaner] {len(df)} 条记录")

    # 1) 批次日期
    df["batch_date"] = df["batch"].map(BATCH_DATES)

    # 2) 能源类型修正
    print("[cleaner] 修正能源类型 ...")
    df["energy_clean"] = df.apply(_fix_energy_type, axis=1)

    # 3) engine_maker 拆分
    print("[cleaner] 拆分 engine_maker ...")
    df["engine_maker_first"] = df["engine_maker"].fillna("").apply(_split_maker)
    df["engine_maker_display"] = df["engine_maker_first"].apply(_display_name)

    # 4) manufacturer 显示名
    df["manufacturer_display"] = df["manufacturer"].fillna("").apply(_display_name)

    # 5) 车辆大类
    df["vehicle_category"] = df["vehicle_type"].fillna("").apply(classify_vehicle)

    # 6) 质量分级
    df["mass_class"] = df["total_mass"].apply(classify_mass)

    # 7) ABS_maker 清洗（取第一个有效企业）
    df["abs_maker_clean"] = df["ABS_maker"].fillna("").apply(_split_maker)
    df["abs_maker_display"] = df["abs_maker_clean"].apply(_display_name)

    # 8) bridge_maker 清洗
    df["bridge_maker_clean"] = df["bridge_maker"].fillna("").astype(str).replace("<NA>", "")

    # 9) 备注结构化
    print("[cleaner] 解析备注文本 ...")
    df = parse_remarks(df)

    # 10) 确保 list/object 列转 string 以便 Parquet 序列化
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("string")

    elapsed = time.time() - t0
    print(f"[cleaner] 清洗完成, 耗时 {elapsed:.1f}s")

    df.to_parquet(CLEANED_PARQUET, engine="pyarrow", index=False)
    size_mb = CLEANED_PARQUET.stat().st_size / 1024 / 1024
    print(f"[cleaner] 写入 {CLEANED_PARQUET} ({size_mb:.1f} MB)")
    return df


if __name__ == "__main__":
    run_full_clean(force=True)
