"""制动系统分析 — ABS/EBS 市场份额、ZF vs 竞争对手"""
from __future__ import annotations
import re
import pandas as pd
from src.config import BATCH_DATES, COMPETITOR_KEYWORDS


def _classify_abs_supplier(makers_str: str, abs_maker_clean: str, bridge_maker: str, remarks: str) -> str:
    """将 ABS 记录归类到供应商。优先用 parsed 备注，其次用字段。"""
    all_text = f"{makers_str} {abs_maker_clean} {bridge_maker} {remarks}"
    if not all_text.strip():
        return "未识别"
    for label, keywords in COMPETITOR_KEYWORDS.items():
        if any(kw in all_text for kw in keywords):
            return label
    if any(kw in all_text for kw in ["瑞立", "瑞立科密"]):
        return "瑞立科密"
    if "万安" in all_text:
        return "万安科技"
    if "元丰" in all_text:
        return "元丰股份"
    if "博瑞克" in all_text:
        return "博瑞克"
    if any(kw in all_text for kw in ["有限公司", "股份"]):
        return "其他"
    return "未识别"


def abs_supplier_share(df: pd.DataFrame) -> pd.DataFrame:
    has_abs = df[df["parsed_has_abs"]].copy()
    has_abs["abs_supplier"] = [
        _classify_abs_supplier(
            str(row.get("parsed_abs_makers", "")),
            str(row.get("abs_maker_clean", "")),
            str(row.get("bridge_maker_clean", "")),
            str(row.get("_remarks_raw", "")),
        )
        for _, row in has_abs.iterrows()
    ]
    return has_abs["abs_supplier"].value_counts().reset_index().rename(
        columns={"index": "supplier", "count": "count", "abs_supplier": "supplier"}
    )


def abs_supplier_share_fast(df: pd.DataFrame) -> pd.DataFrame:
    """向量化版本，适合82万条数据。"""
    has_abs = df[df["parsed_has_abs"]].copy()
    remarks = has_abs["_remarks_raw"].fillna("").astype(str)
    abs_makers = has_abs["parsed_abs_makers"].fillna("").astype(str)
    abs_field = has_abs["abs_maker_clean"].fillna("").astype(str)
    bridge = has_abs["bridge_maker_clean"].fillna("").astype(str)
    combined = remarks + " " + abs_makers + " " + abs_field + " " + bridge

    supplier = pd.Series("未识别", index=has_abs.index)
    supplier[combined.str.contains("威伯科|采埃孚|WABCO|ZF", case=False, regex=True)] = "ZF/采埃孚"
    mask_knorr = combined.str.contains("克诺尔|Knorr|东科克诺尔", case=False, regex=True)
    supplier[mask_knorr & (supplier == "未识别")] = "Knorr/克诺尔"
    mask_bosch = combined.str.contains("博世|Bosch", case=False, regex=True)
    supplier[mask_bosch & (supplier == "未识别")] = "Bosch/博世"
    supplier[combined.str.contains("瑞立", case=False) & (supplier == "未识别")] = "瑞立科密"
    supplier[combined.str.contains("万安", case=False) & (supplier == "未识别")] = "万安科技"
    supplier[combined.str.contains("元丰", case=False) & (supplier == "未识别")] = "元丰股份"
    supplier[combined.str.contains("博瑞克", case=False) & (supplier == "未识别")] = "博瑞克"
    supplier[(supplier == "未识别") & combined.str.contains("有限公司", case=False)] = "其他"

    return supplier.value_counts().reset_index().rename(columns={"index": "supplier", "count": "count"})


def abs_supplier_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按批次的 ABS 供应商份额趋势。"""
    has_abs = df[df["parsed_has_abs"]].copy()
    remarks = has_abs["_remarks_raw"].fillna("").astype(str)
    abs_makers = has_abs["parsed_abs_makers"].fillna("").astype(str)
    abs_field = has_abs["abs_maker_clean"].fillna("").astype(str)
    bridge = has_abs["bridge_maker_clean"].fillna("").astype(str)
    combined = remarks + " " + abs_makers + " " + abs_field + " " + bridge

    supplier = pd.Series("其他", index=has_abs.index)
    supplier[combined.str.contains("威伯科|采埃孚|WABCO|ZF", case=False, regex=True)] = "ZF/采埃孚"
    mask_knorr = combined.str.contains("克诺尔|Knorr|东科克诺尔", case=False, regex=True)
    supplier[mask_knorr & (supplier == "其他")] = "Knorr/克诺尔"
    mask_bosch = combined.str.contains("博世|Bosch", case=False, regex=True)
    supplier[mask_bosch & (supplier == "其他")] = "Bosch/博世"
    supplier[combined.str.contains("瑞立", case=False) & (supplier == "其他")] = "瑞立科密"
    supplier[combined.str.contains("万安", case=False) & (supplier == "其他")] = "万安科技"

    has_abs["abs_supplier"] = supplier
    out = has_abs.groupby(["batch", "abs_supplier"]).size().reset_index(name="count")
    totals = has_abs.groupby("batch").size().reset_index(name="total")
    out = out.merge(totals, on="batch")
    out["ratio"] = out["count"] / out["total"]
    out["batch_date"] = out["batch"].map(BATCH_DATES)
    return out


def ebs_penetration_trend(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for batch, g in df.groupby("batch"):
        total = len(g)
        has_ebs = g["parsed_has_ebs"].sum()
        opt_ebs = g["parsed_optional_ebs"].sum()
        rows.append({
            "batch": batch,
            "batch_date": BATCH_DATES.get(batch, ""),
            "total": total,
            "has_ebs": has_ebs,
            "optional_ebs": opt_ebs,
            "ebs_ratio": has_ebs / total if total else 0,
        })
    return pd.DataFrame(rows)


def zf_product_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """ZF/采埃孚 ABS 产品型号分布。"""
    zf = df[df["parsed_zf_mention"]].copy()
    models = zf["parsed_abs_models"].fillna("").astype(str)
    all_models = models[models != ""].str.split("|").explode()
    all_models = all_models[all_models.str.len() >= 2]
    vc = all_models.value_counts().head(15).reset_index()
    vc.columns = ["model", "count"]
    return vc
