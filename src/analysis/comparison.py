"""
公告 vs 上牌（零售）对比分析模块
核心功能：型号匹配、公告-上牌时间差分析、成熟批次上牌覆盖率、配置维度聚合、ZF 聚焦分析
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from src.config import _ANCHOR_BATCH, _ANCHOR_YEAR, _ANCHOR_MONTH


def _batch_to_abs_month(batch: int) -> int:
    """批次号 → 绝对月份数（year*12 + month），用于时间差计算"""
    delta = _ANCHOR_BATCH - batch
    return _ANCHOR_YEAR * 12 + _ANCHOR_MONTH - delta


def _batch_to_year(batch: int) -> int:
    am = _batch_to_abs_month(batch)
    return (am - 1) // 12


# ═══════════════════════════════════════════════════════
# 1. 对比表构建
# ═══════════════════════════════════════════════════════

def build_comparison_table(
    df_announce: pd.DataFrame,
    df_retail: pd.DataFrame,
) -> pd.DataFrame:
    """
    以公告去重型号为基准，left join 零售数据，计算时间差。

    返回 DataFrame，每行一个唯一 model_code，包含：
    - 公告侧字段（首次批次、配置、ZF 标记等）
    - has_retail: 是否在 2025 年有上牌记录
    - retail_qty: 2025 年上牌总量
    - first_reg_abs_month: 首次上牌绝对月份
    - lag_months: 首次上牌 - 首次公告 的月份差
    """
    # 公告侧：每个 model_code 取首次出现批次 + 配置字段
    agg_cols = {
        "batch": "min",
        "vehicle_category": "first",
        "energy_clean": "first",
        "mass_class": "first",
        "power_kw": "first",
        "manufacturer_display": "first",
        "parsed_zf_mention": "max",
        "parsed_has_abs": "max",
        "parsed_has_ebs": "max",
        "parsed_optional_ebs": "max",
        "parsed_bosch_mention": "max",
        "parsed_knorr_mention": "max",
        "parsed_abs_models": "first",
        "parsed_abs_makers": "first",
        "abs_maker_display": "first",
        "ABS_model": "first",
        "ABS_maker": "first",
        "transmission_type": "first",
        "transmission_model": "first",
        "bridge_maker": "first",
        "bridge_maker_clean": "first",
        "parsed_drive_topology": "first",
        "parsed_battery_chemistry": "first",
        "parsed_battery_pack_makers": "first",
        "parsed_battery_cell_makers": "first",
        "parsed_battery_kwh": "first",
        "parsed_tz_maker_code": "first",
    }
    existing = {k: v for k, v in agg_cols.items() if k in df_announce.columns}
    df_a = df_announce.groupby("model_code", as_index=False).agg(existing)
    df_a.rename(columns={"batch": "first_batch"}, inplace=True)
    df_a["announce_abs_month"] = df_a["first_batch"].map(_batch_to_abs_month)
    df_a["announce_year"] = df_a["first_batch"].map(_batch_to_year)

    # 零售侧：每个车辆型号聚合
    r = df_retail.copy()
    r["reg_abs_month"] = r["年"].fillna(0).astype(int) * 12 + r["月"].fillna(0).astype(int)
    retail_agg = r.groupby("车辆型号", as_index=False).agg(
        retail_qty=("数量", "sum"),
        first_reg_abs_month=("reg_abs_month", "min"),
    )

    # Left join
    merged = df_a.merge(
        retail_agg,
        left_on="model_code",
        right_on="车辆型号",
        how="left",
    )
    merged["has_retail"] = merged["retail_qty"].notna() & (merged["retail_qty"] > 0)
    merged["retail_qty"] = merged["retail_qty"].fillna(0).astype(int)
    merged["lag_months"] = np.where(
        merged["has_retail"],
        merged["first_reg_abs_month"] - merged["announce_abs_month"],
        np.nan,
    )
    merged.drop(columns=["车辆型号", "first_reg_abs_month"], inplace=True, errors="ignore")
    return merged


# ═══════════════════════════════════════════════════════
# 2. 公告-上牌时间差分析
# ═══════════════════════════════════════════════════════

_LAG_BINS = [-9999, -12, 0, 6, 12, 24, 36, 48, 60, 9999]
_LAG_LABELS = ["<-12月", "-12~0月", "0~6月", "6~12月",
               "12~24月", "24~36月", "36~48月", "48~60月", ">60月"]


def time_lag_distribution(df_comp: pd.DataFrame) -> pd.DataFrame:
    """时间差分箱分布"""
    matched = df_comp[df_comp["has_retail"]].copy()
    matched["lag_bin"] = pd.cut(matched["lag_months"], bins=_LAG_BINS, labels=_LAG_LABELS)
    return matched["lag_bin"].value_counts().sort_index().reset_index()


def time_lag_by_year(df_comp: pd.DataFrame) -> pd.DataFrame:
    """按公告年份统计中位/平均时间差及匹配型号数"""
    matched = df_comp[df_comp["has_retail"]].copy()
    out = matched.groupby("announce_year").agg(
        matched_models=("model_code", "count"),
        median_lag=("lag_months", "median"),
        mean_lag=("lag_months", "mean"),
    ).reset_index()
    return out.sort_values("announce_year")


def time_lag_by_dimension(df_comp: pd.DataFrame, dim: str) -> pd.DataFrame:
    """按指定维度统计中位时间差"""
    matched = df_comp[df_comp["has_retail"] & df_comp[dim].notna()].copy()
    if len(matched) == 0:
        return pd.DataFrame(columns=[dim, "median_lag", "count"])
    out = matched.groupby(dim).agg(
        median_lag=("lag_months", "median"),
        count=("model_code", "count"),
    ).reset_index().sort_values("median_lag")
    return out


# ═══════════════════════════════════════════════════════
# 3. 成熟批次上牌覆盖率
# ═══════════════════════════════════════════════════════

_REF_ABS_MONTH = 2025 * 12 + 1  # 2025-01，上牌数据起始


def filter_mature_cohort(df_comp: pd.DataFrame, min_lag_months: int = 24) -> pd.DataFrame:
    """筛选公告日期在上牌窗口起始前 >= min_lag_months 的型号"""
    cutoff = _REF_ABS_MONTH - min_lag_months
    return df_comp[df_comp["announce_abs_month"] <= cutoff].copy()


def registration_coverage(df: pd.DataFrame) -> dict:
    """计算一个子集的上牌覆盖率指标"""
    total = len(df)
    if total == 0:
        return {"total_models": 0, "registered_models": 0,
                "coverage_rate": 0.0, "total_retail_qty": 0}
    registered = df["has_retail"].sum()
    return {
        "total_models": total,
        "registered_models": int(registered),
        "coverage_rate": registered / total,
        "total_retail_qty": int(df["retail_qty"].sum()),
    }


# ═══════════════════════════════════════════════════════
# 4. 按配置维度聚合
# ═══════════════════════════════════════════════════════

def aggregate_by_config(
    df_comp: pd.DataFrame,
    group_col: str,
    zf_col: str = "parsed_zf_mention",
) -> pd.DataFrame:
    """
    按维度聚合，同时计算全市场和 ZF 子集的上牌覆盖率。
    """
    valid = df_comp[df_comp[group_col].notna() & (df_comp[group_col] != "")]
    has_zf = zf_col in valid.columns

    rows = []
    for name, sub in valid.groupby(group_col):
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        if has_zf:
            is_zf = sub[zf_col].fillna(False).astype(bool)
            zf = sub[is_zf]
        else:
            zf = sub.iloc[0:0]
        zt = len(zf)
        zr = int(zf["has_retail"].sum()) if zt > 0 else 0
        zrq = int(zf["retail_qty"].sum()) if zt > 0 else 0
        rows.append({
            group_col: name,
            "total_models": t,
            "reg_models": r,
            "coverage_rate": r / t if t else 0,
            "retail_qty": rq,
            "zf_models": zt,
            "zf_reg_models": zr,
            "zf_coverage_rate": zr / zt if zt else 0,
            "zf_retail_qty": zrq,
            "zf_penetration_announce": zt / t if t else 0,
            "zf_penetration_retail": zrq / rq if rq else 0,
        })

    result = pd.DataFrame(rows)
    if len(result) == 0:
        return result
    return result.sort_values("total_models", ascending=False)


def cross_dimension_matrix(
    df_comp: pd.DataFrame,
    row_col: str,
    col_col: str,
    value: str = "coverage_rate",
) -> pd.DataFrame:
    """交叉维度矩阵（如 能源类型 x 车辆大类 的上牌覆盖率）"""
    valid = df_comp[
        df_comp[row_col].notna() & (df_comp[row_col] != "") &
        df_comp[col_col].notna() & (df_comp[col_col] != "")
    ]
    rows = []
    for (r_val, c_val), sub in valid.groupby([row_col, col_col]):
        rate = sub["has_retail"].sum() / len(sub) if len(sub) > 0 else 0
        rows.append({row_col: r_val, col_col: c_val, value: rate})
    if not rows:
        return pd.DataFrame()
    grouped = pd.DataFrame(rows)
    return grouped.pivot(index=row_col, columns=col_col, values=value).fillna(0)


# ═══════════════════════════════════════════════════════
# 5. ZF 聚焦分析
# ═══════════════════════════════════════════════════════

def zf_vs_market_by_dim(
    df_comp: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    """ZF 上牌覆盖率 vs 全市场对比表"""
    agg = aggregate_by_config(df_comp, group_col)
    agg["gap"] = agg["zf_coverage_rate"] - agg["coverage_rate"]
    return agg


def zf_product_registration(df_comp: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """ZF ABS/EBS 产品型号级别的上牌覆盖率分析，使用 parsed_abs_models 或 ABS_model 字段"""
    zf = df_comp[df_comp["parsed_zf_mention"].fillna(False).astype(bool)].copy()
    if len(zf) == 0:
        return pd.DataFrame(columns=["model", "total", "registered", "coverage_rate", "retail_qty"])

    model_col = None
    for c in ["parsed_abs_models", "ABS_model"]:
        if c in zf.columns:
            non_empty = zf[c].fillna("").astype(str)
            if (non_empty != "").sum() > 0:
                model_col = c
                break
    if model_col is None:
        return pd.DataFrame(columns=["model", "total", "registered", "coverage_rate", "retail_qty"])

    models_raw = zf[model_col].fillna("").astype(str)
    rows = []
    for idx, ms in models_raw.items():
        if not ms or ms == "":
            continue
        parts = ms.split("|") if "|" in ms else ms.split(";")
        for m in parts:
            m = m.strip()
            if len(m) < 2 or len(m) > 30:
                continue
            rows.append({
                "model": m,
                "has_retail": zf.loc[idx, "has_retail"],
                "retail_qty": zf.loc[idx, "retail_qty"],
            })
    if not rows:
        return pd.DataFrame(columns=["model", "total", "registered", "coverage_rate", "retail_qty"])

    exploded = pd.DataFrame(rows)
    agg = []
    for name, sub in exploded.groupby("model"):
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        agg.append({"model": name, "total": t, "registered": r,
                     "coverage_rate": r / t if t else 0, "retail_qty": rq})
    result = pd.DataFrame(agg).sort_values("total", ascending=False).head(top_n)
    return result


def zf_braking_breakdown(df_comp: pd.DataFrame) -> pd.DataFrame:
    """ZF 制动系统分类的上牌覆盖率对比"""
    categories = [
        ("ZF + ABS", lambda d: d["parsed_zf_mention"].fillna(False) & d["parsed_has_abs"].fillna(False)),
        ("ZF + EBS", lambda d: d["parsed_zf_mention"].fillna(False) & d["parsed_has_ebs"].fillna(False)),
        ("ZF + 选装EBS", lambda d: d["parsed_zf_mention"].fillna(False) & d["parsed_optional_ebs"].fillna(False)),
        ("竞品 Bosch", lambda d: d["parsed_bosch_mention"].fillna(False)),
        ("竞品 Knorr", lambda d: d["parsed_knorr_mention"].fillna(False)),
        ("无ABS记录", lambda d: ~d["parsed_has_abs"].fillna(False)),
    ]
    rows = []
    for label, mask_fn in categories:
        try:
            mask = mask_fn(df_comp).astype(bool)
        except Exception:
            continue
        sub = df_comp[mask]
        if len(sub) == 0:
            continue
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        rows.append({
            "分类": label,
            "公告型号数": t,
            "有上牌型号": r,
            "覆盖率": r / t if t else 0,
            "上牌量": rq,
        })
    return pd.DataFrame(rows)


def zf_abs_supplier_competition(df_comp: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """ABS 供应商市场份额与上牌表现对比（含 ZF/WABCO 识别）"""
    if "abs_maker_display" not in df_comp.columns:
        return pd.DataFrame()

    _ZF_KEYWORDS = ["威伯科", "wabco", "采埃孚", "zf", "瑞立科密"]

    df = df_comp.copy()
    maker = df["abs_maker_display"].fillna("").astype(str)
    df = df[maker.str.len() > 2]
    if len(df) == 0:
        return pd.DataFrame()

    rows = []
    for name, sub in df.groupby("abs_maker_display"):
        if not isinstance(name, str) or len(name) <= 2:
            continue
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        is_zf = any(kw in name.lower() for kw in _ZF_KEYWORDS)
        rows.append({
            "supplier": name, "total": t, "registered": r,
            "coverage_rate": r / t if t else 0, "retail_qty": rq,
            "is_zf_family": is_zf,
        })
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows).sort_values("total", ascending=False).head(top_n)
    return result


def zf_eaxle_analysis(df_comp: pd.DataFrame) -> pd.DataFrame:
    """电桥/电驱动供应商上牌分析（bridge_maker_clean + parsed_drive_topology）"""
    if "bridge_maker_clean" not in df_comp.columns:
        return pd.DataFrame()

    df = df_comp.copy()
    bm = df["bridge_maker_clean"].fillna("").astype(str)
    df = df[bm.str.len() > 0]
    if len(df) == 0:
        return pd.DataFrame()

    rows = []
    for name, sub in df.groupby("bridge_maker_clean"):
        if not isinstance(name, str) or len(name) == 0:
            continue
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        rows.append({
            "supplier": name, "total": t, "registered": r,
            "coverage_rate": r / t if t else 0, "retail_qty": rq,
        })
    return pd.DataFrame(rows).sort_values("total", ascending=False) if rows else pd.DataFrame()


def zf_drive_topology_analysis(df_comp: pd.DataFrame) -> pd.DataFrame:
    """电驱动拓扑结构上牌分析"""
    if "parsed_drive_topology" not in df_comp.columns:
        return pd.DataFrame()

    df = df_comp.copy()
    topo = df["parsed_drive_topology"].fillna("").astype(str)
    df = df[topo.str.len() > 0]
    if len(df) == 0:
        return pd.DataFrame()

    rows = []
    for name, sub in df.groupby("parsed_drive_topology"):
        if not isinstance(name, str) or len(name) == 0:
            continue
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rq = int(sub["retail_qty"].sum())
        zf_sub = sub[sub["parsed_zf_mention"].fillna(False).astype(bool)]
        zt = len(zf_sub)
        zr = int(zf_sub["has_retail"].sum()) if zt > 0 else 0
        zrq = int(zf_sub["retail_qty"].sum()) if zt > 0 else 0
        rows.append({
            "topology": name, "total": t, "registered": r,
            "coverage_rate": r / t if t else 0, "retail_qty": rq,
            "zf_total": zt, "zf_registered": zr,
            "zf_coverage_rate": zr / zt if zt else 0,
            "zf_retail_qty": zrq,
        })
    return pd.DataFrame(rows).sort_values("total", ascending=False) if rows else pd.DataFrame()


def zf_by_vehicle_energy(df_comp: pd.DataFrame) -> pd.DataFrame:
    """ZF 按车辆大类 x 能源类型的上牌覆盖率矩阵"""
    zf = df_comp[df_comp["parsed_zf_mention"].fillna(False).astype(bool)].copy()
    if len(zf) == 0:
        return pd.DataFrame()
    rows = []
    for (cat, energy), sub in zf.groupby(["vehicle_category", "energy_clean"]):
        if len(sub) < 5:
            continue
        t = len(sub)
        r = int(sub["has_retail"].sum())
        rows.append({
            "vehicle_category": cat, "energy_clean": energy,
            "total": t, "registered": r,
            "coverage_rate": r / t if t else 0,
            "retail_qty": int(sub["retail_qty"].sum()),
        })
    return pd.DataFrame(rows).sort_values("total", ascending=False) if rows else pd.DataFrame()


# ═══════════════════════════════════════════════════════
# 6. 建议摘要自动生成
# ═══════════════════════════════════════════════════════

def generate_summary(
    df_comp: pd.DataFrame,
    dim: str = "vehicle_category",
    min_models: int = 50,
) -> pd.DataFrame:
    """
    基于配置聚合结果自动生成结构化建议（高潜力/差距/机会/风险）。
    """
    agg = aggregate_by_config(df_comp, dim)
    agg = agg[agg["total_models"] >= min_models]
    if len(agg) == 0:
        return pd.DataFrame(columns=[dim, "tag", "description"])

    median_cov = agg["coverage_rate"].median()
    median_qty = agg["retail_qty"].median()

    rows = []
    for _, r in agg.iterrows():
        name = r[dim]
        cov = r["coverage_rate"]
        qty = r["retail_qty"]
        zf_cov = r["zf_coverage_rate"]
        zf_pen_a = r["zf_penetration_announce"]
        zf_pen_r = r["zf_penetration_retail"]

        if cov > median_cov and qty > median_qty and zf_pen_a > 0:
            rows.append({
                dim: name, "tag": "高潜力",
                "description": f"上牌覆盖率 {cov:.1%}（高于中位 {median_cov:.1%}），"
                               f"销量 {qty:,}，ZF 已有布局（公告渗透 {zf_pen_a:.1%}），建议重点投入",
            })
        if zf_pen_a > 0.05 and zf_cov < cov * 0.7 and zf_cov > 0:
            rows.append({
                dim: name, "tag": "上牌率差距",
                "description": f"ZF 上牌覆盖率 {zf_cov:.1%} 低于全市场 {cov:.1%}，"
                               f"公告渗透 {zf_pen_a:.1%}，建议排查原因",
            })
        if qty > median_qty and zf_pen_r < 0.05:
            rows.append({
                dim: name, "tag": "渗透机会",
                "description": f"高销量配置（{qty:,}），ZF 上牌渗透仅 {zf_pen_r:.1%}，"
                               f"技术适配时建议作为渗透目标",
            })
        if cov < median_cov * 0.5 and zf_pen_a > 0.1:
            rows.append({
                dim: name, "tag": "风险",
                "description": f"上牌覆盖率仅 {cov:.1%}（远低于中位），"
                               f"但 ZF 公告渗透 {zf_pen_a:.1%} 偏高，存在结构性风险",
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[dim, "tag", "description"])


# ═══════════════════════════════════════════════════════
# 7. Executive Summary — 数据驱动分析摘要
# ═══════════════════════════════════════════════════════

def generate_executive_summary(
    df_comp: pd.DataFrame,
    df_mature: pd.DataFrame,
) -> list[str]:
    """
    基于成熟批次数据自动生成 Executive Summary 段落列表，
    从 ZF Tier-1 视角聚焦终端销量（零售）表现。
    返回 Markdown 格式字符串列表。
    """
    paragraphs: list[str] = []

    # ── 1. 市场总量概览 ──
    stats_all = registration_coverage(df_mature)
    zf_mask = df_mature["parsed_zf_mention"].fillna(False).astype(bool)
    zf_sub = df_mature[zf_mask]
    non_zf = df_mature[~zf_mask]
    zf_stats = registration_coverage(zf_sub)
    non_zf_stats = registration_coverage(non_zf)

    total_retail = stats_all["total_retail_qty"]
    zf_retail = zf_stats["total_retail_qty"]
    zf_share = zf_retail / total_retail if total_retail > 0 else 0

    p1 = (
        f"**市场总量**：成熟批次公告型号 {stats_all['total_models']:,} 个，"
        f"对应 2025 年零售总量 **{total_retail:,}** 辆。"
        f"ZF 配套车型零售量 **{zf_retail:,}** 辆，"
        f"零售市场份额 **{zf_share:.1%}**。"
    )
    if zf_stats["coverage_rate"] > non_zf_stats["coverage_rate"]:
        p1 += (
            f" ZF 配套型号零售覆盖率 {zf_stats['coverage_rate']:.1%}，"
            f"高于非 ZF 的 {non_zf_stats['coverage_rate']:.1%}，"
            f"表明 ZF 配套车型具备更好的市场转化能力。"
        )
    else:
        gap = non_zf_stats["coverage_rate"] - zf_stats["coverage_rate"]
        p1 += (
            f" ZF 配套型号零售覆盖率 {zf_stats['coverage_rate']:.1%}，"
            f"低于非 ZF 的 {non_zf_stats['coverage_rate']:.1%}（差距 {gap:.1%}），"
            f"需关注公告向零售转化的效率问题。"
        )
    paragraphs.append(p1)

    # ── 2. 核心产品零售表现 ──
    prod_df = zf_product_registration(df_mature, top_n=5)
    if len(prod_df) > 0:
        lines = []
        for _, row in prod_df.iterrows():
            lines.append(
                f"  - **{row['model']}**：配套 {row['total']} 个型号，"
                f"零售量 {row['retail_qty']:,} 辆，覆盖率 {row['coverage_rate']:.1%}"
            )
        top_product = prod_df.iloc[0]
        p2 = (
            f"**核心产品表现**：ZF ABS/EBS 产品中，**{top_product['model']}** "
            f"零售量最高（{top_product['retail_qty']:,} 辆），"
            f"覆盖率 {top_product['coverage_rate']:.1%}。Top 5 产品：\n"
            + "\n".join(lines)
        )
        paragraphs.append(p2)

    # ── 3. 细分市场洞察 ──
    agg_cat = aggregate_by_config(df_mature, "vehicle_category")
    agg_cat = agg_cat[agg_cat["total_models"] >= 30].copy()
    if len(agg_cat) > 0:
        # 最大零售量细分
        top_seg = agg_cat.sort_values("zf_retail_qty", ascending=False).head(3)
        seg_items = []
        for _, r in top_seg.iterrows():
            seg_items.append(
                f"**{r['vehicle_category']}**（ZF 零售 {r['zf_retail_qty']:,} 辆，"
                f"渗透率 {r['zf_penetration_retail']:.1%}）"
            )
        p3 = (
            f"**细分市场洞察**：ZF 零售量最高的细分市场为 "
            + "、".join(seg_items) + "。"
        )
        # 高覆盖率细分
        high_cov = agg_cat[agg_cat["zf_coverage_rate"] > agg_cat["coverage_rate"]].sort_values(
            "zf_retail_qty", ascending=False
        ).head(2)
        if len(high_cov) > 0:
            hc_names = "、".join(
                f"{r['vehicle_category']}（ZF {r['zf_coverage_rate']:.1%} vs 市场{r['coverage_rate']:.1%}）"
                for _, r in high_cov.iterrows()
            )
            p3 += f" 在 {hc_names} 细分中，ZF 覆盖率领先市场平均水平。"
        paragraphs.append(p3)

    # ── 4. 竞争定位（公告侧 vs 零售侧渗透差距） ──
    agg_cat2 = aggregate_by_config(df_mature, "vehicle_category")
    agg_cat2 = agg_cat2[agg_cat2["total_models"] >= 30].copy()
    if len(agg_cat2) > 0:
        agg_cat2["pen_gap"] = agg_cat2["zf_penetration_retail"] - agg_cat2["zf_penetration_announce"]

        # 公告渗透高但零售渗透低（转化差）
        weak_convert = agg_cat2[
            (agg_cat2["zf_penetration_announce"] > 0.05) &
            (agg_cat2["pen_gap"] < -0.02)
        ].sort_values("pen_gap").head(3)

        # 零售渗透高于公告（强势）
        strong = agg_cat2[agg_cat2["pen_gap"] > 0.01].sort_values("pen_gap", ascending=False).head(3)

        p4_parts = ["**竞争定位**："]
        if len(strong) > 0:
            strong_items = ", ".join(
                f"{r['vehicle_category']}（公告 {r['zf_penetration_announce']:.1%} → 零售 {r['zf_penetration_retail']:.1%}）"
                for _, r in strong.iterrows()
            )
            p4_parts.append(f"ZF 零售渗透率超越公告侧的品类：{strong_items}，说明在这些市场 ZF 产品竞争力强，OEM 更倾向选装。")

        if len(weak_convert) > 0:
            weak_items = ", ".join(
                f"{r['vehicle_category']}（公告 {r['zf_penetration_announce']:.1%} → 零售 {r['zf_penetration_retail']:.1%}）"
                for _, r in weak_convert.iterrows()
            )
            p4_parts.append(f" 需关注转化效率的品类：{weak_items}，虽有公告配套但终端销量偏低。")

        if len(p4_parts) > 1:
            paragraphs.append("".join(p4_parts))

    # ── 5. 产品机会 ──
    if len(agg_cat2) > 0:
        opportunity = agg_cat2[
            (agg_cat2["retail_qty"] > agg_cat2["retail_qty"].median()) &
            (agg_cat2["zf_penetration_retail"] < 0.08)
        ].sort_values("retail_qty", ascending=False).head(3)

        if len(opportunity) > 0:
            opp_items = []
            for _, r in opportunity.iterrows():
                opp_items.append(
                    f"**{r['vehicle_category']}**（零售 {r['retail_qty']:,} 辆，ZF 渗透仅 {r['zf_penetration_retail']:.1%}）"
                )
            p5 = (
                f"**产品机会**：以下高零售量市场 ZF 渗透率偏低，存在增量机会："
                + "；".join(opp_items) + "。"
                " 建议从 Tier-1 角度评估技术适配性与客户开发优先级。"
            )
            paragraphs.append(p5)

    # ── 6. 制动产品 vs 能源趋势 ──
    agg_energy = aggregate_by_config(df_mature, "energy_clean")
    agg_energy = agg_energy[agg_energy["total_models"] >= 20].copy()
    if len(agg_energy) > 0:
        bev = agg_energy[agg_energy["energy_clean"].str.contains("纯电", na=False)]
        trad = agg_energy[agg_energy["energy_clean"].str.contains("柴油", na=False)]
        parts = ["**能源趋势与产品定位**："]
        if len(bev) > 0:
            b = bev.iloc[0]
            parts.append(
                f"纯电动车型零售 {b['retail_qty']:,} 辆，"
                f"ZF 渗透率 {b['zf_penetration_retail']:.1%}。"
            )
        if len(trad) > 0:
            t = trad.iloc[0]
            parts.append(
                f"柴油车型零售 {t['retail_qty']:,} 辆，"
                f"ZF 渗透率 {t['zf_penetration_retail']:.1%}。"
            )
        if len(bev) > 0 and len(trad) > 0:
            b_pen = bev.iloc[0]["zf_penetration_retail"]
            t_pen = trad.iloc[0]["zf_penetration_retail"]
            if b_pen < t_pen:
                parts.append(
                    f" ZF 在纯电动领域渗透率（{b_pen:.1%}）低于柴油（{t_pen:.1%}），"
                    "电动化转型是业务拓展的关键方向。"
                )
            else:
                parts.append(
                    f" ZF 在纯电动领域渗透率（{b_pen:.1%}）已高于柴油（{t_pen:.1%}），"
                    "电动化布局进展良好。"
                )
        if len(parts) > 1:
            paragraphs.append("".join(parts))

    return paragraphs