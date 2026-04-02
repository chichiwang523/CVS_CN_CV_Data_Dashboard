"""
Page 10: 公告 vs 上牌分析 — 型号匹配、公告-上牌时间差、配置表现、ZF 聚焦、建议摘要
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.sidebar import apply_sidebar_filters
from src.charts import (
    _apply_layout, bar_h, bar_v, dual_axis_chart, line_chart,
    grouped_bar, ZF_BLUE, ZF_COLORS, PLOTLY_LAYOUT,
)
from src.analysis.comparison import (
    build_comparison_table,
    time_lag_distribution, time_lag_by_year, time_lag_by_dimension,
    filter_mature_cohort, registration_coverage,
    aggregate_by_config, cross_dimension_matrix,
    zf_vs_market_by_dim, generate_summary, generate_executive_summary,
    zf_product_registration, zf_braking_breakdown, zf_by_vehicle_energy,
    zf_abs_supplier_competition, zf_eaxle_analysis, zf_drive_topology_analysis,
)
from src.retail_demo_loader import load_retail_full

# ── 页面设置 ──────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h1, h2, h3 { color: #003399; }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.3rem !important; }
    .stMetric label { font-size: 12px !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 24px !important; color: #003399; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 公告 vs 上牌零售对比分析")
st.caption("公告数据（290-388批）与 2025 年商用车零售（上牌）数据型号级匹配分析 | ZF Tier-1 市场定位视角")

# ── 数据加载 ──────────────────────────────────────────

df_announce = apply_sidebar_filters(default_batch_window=99)

min_lag = st.sidebar.slider(
    "成熟批次阈值（月）", 6, 48, 24, step=6,
    help="仅对首次公告后超过此月数的型号计算上牌覆盖率（估算）",
    key="comp_min_lag",
)

if len(df_announce) == 0:
    st.warning("当前筛选条件下无公告数据")
    st.stop()


@st.cache_data(ttl=3600, show_spinner="加载零售全量数据中...")
def _load_retail():
    return load_retail_full(force_rebuild=False)


df_retail = _load_retail()


@st.cache_data(ttl=3600, show_spinner="构建对比表中...")
def _build_comp(_a_hash, df_a, df_r):
    return build_comparison_table(df_a, df_r)


df_comp = _build_comp(
    hash(tuple(df_announce["model_code"].head(20).tolist()) + (len(df_announce),)),
    df_announce, df_retail,
)

df_mature = filter_mature_cohort(df_comp, min_lag)

# ── 维度选项 ──────────────────────────────────────────

DIM_OPTIONS = {
    "车辆大类": "vehicle_category",
    "能源类型": "energy_clean",
    "质量分级": "mass_class",
    "ABS 状态": "parsed_has_abs",
    "EBS 状态": "parsed_has_ebs",
}

# ══════════════════════════════════════════════════════
# Tabs
# ══════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "公告-上牌时间差",
    "匹配概览",
    "配置-市场表现",
    "ZF 聚焦分析",
    "Executive Summary",
])

# ── Tab 1: 公告-上牌时间差 ────────────────────────────

with tab1:
    st.markdown("## 公告-上牌时间差")
    st.info(
        "上牌数据仅覆盖 **2025 年**，因此时间差反映的是「该型号首次公告到 2025 年首次出现上牌记录」的间隔。"
        "2024/2025 年公告的型号可能尚未充分上牌，早年公告可能已在 2024 年前完成上牌但不在本数据窗口内。"
    )

    matched = df_comp[df_comp["has_retail"]]
    if len(matched) == 0:
        st.warning("当前筛选条件下无匹配型号")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("匹配型号数", f"{len(matched):,}")
        k2.metric("中位时间差", f"{matched['lag_months'].median():.0f} 月")
        k3.metric("平均时间差", f"{matched['lag_months'].mean():.1f} 月")
        k4.metric("25-75分位", f"{matched['lag_months'].quantile(0.25):.0f}~{matched['lag_months'].quantile(0.75):.0f} 月")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 时间差分布")
            lag_dist = time_lag_distribution(df_comp)
            if len(lag_dist) > 0:
                fig = bar_v(lag_dist, x="lag_bin", y="count", title="", height=380)
                fig.update_layout(xaxis_title="时间差区间", yaxis_title="型号数", xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("### 按公告年份的中位时间差")
            lag_year = time_lag_by_year(df_comp)
            if len(lag_year) > 0:
                fig = dual_axis_chart(
                    lag_year, x="announce_year",
                    y1="matched_models", y2="median_lag",
                    y1_name="匹配型号数", y2_name="中位时间差（月）",
                    height=380,
                )
                fig.update_layout(xaxis_title="公告年份")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown("### 按车辆大类的中位时间差")
            lag_cat = time_lag_by_dimension(df_comp, "vehicle_category")
            if len(lag_cat) > 0:
                fig = bar_h(lag_cat, x="median_lag", y="vehicle_category",
                            title="", height=max(300, len(lag_cat) * 30))
                fig.update_layout(xaxis_title="中位时间差（月）")
                st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.markdown("### 按能源类型的中位时间差")
            lag_energy = time_lag_by_dimension(df_comp, "energy_clean")
            if len(lag_energy) > 0:
                fig = bar_h(lag_energy, x="median_lag", y="energy_clean",
                            title="", height=max(300, len(lag_energy) * 30))
                fig.update_layout(xaxis_title="中位时间差（月）")
                st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: 匹配概览 ──────────────────────────────────

with tab2:
    st.markdown("## 匹配概览与上牌覆盖率（估算）")
    st.warning(
        f"以下上牌覆盖率基于「成熟批次」估算：仅统计首次公告于 2025-01 之前至少 **{min_lag} 个月**的型号。"
        "此指标反映「在 2025 年有上牌记录」的公告型号占比，非全生命周期真实上牌率。"
        "可通过左侧滑块调整阈值。"
    )

    stats_all = registration_coverage(df_comp)
    stats_mature = registration_coverage(df_mature)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("公告型号总数", f"{stats_all['total_models']:,}")
    k2.metric("有上牌记录", f"{stats_all['registered_models']:,}")
    k3.metric("原始覆盖率", f"{stats_all['coverage_rate']:.1%}")
    k4.metric(f"成熟批次覆盖率(≥{min_lag}月)", f"{stats_mature['coverage_rate']:.1%}")
    k5.metric("上牌总量", f"{stats_all['total_retail_qty']:,}")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 按车辆大类的上牌覆盖率")
        agg_cat = aggregate_by_config(df_mature, "vehicle_category")
        if len(agg_cat) > 0:
            agg_cat_show = agg_cat[agg_cat["total_models"] >= 10].copy()
            agg_cat_show["coverage_pct"] = (agg_cat_show["coverage_rate"] * 100).round(1)
            fig = bar_h(agg_cat_show, x="coverage_pct", y="vehicle_category",
                        title="", height=max(300, len(agg_cat_show) * 35))
            fig.update_layout(xaxis_title="上牌覆盖率 (%)")
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("### 按能源类型的上牌覆盖率")
        agg_energy = aggregate_by_config(df_mature, "energy_clean")
        if len(agg_energy) > 0:
            agg_e_show = agg_energy[agg_energy["total_models"] >= 10].copy()
            agg_e_show["coverage_pct"] = (agg_e_show["coverage_rate"] * 100).round(1)
            fig = bar_h(agg_e_show, x="coverage_pct", y="energy_clean",
                        title="", height=max(300, len(agg_e_show) * 35))
            fig.update_layout(xaxis_title="上牌覆盖率 (%)")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 按公告年份的上牌覆盖率曲线")
    _yc_rows = []
    for yr, g in df_comp.groupby("announce_year"):
        _yc_rows.append({
            "announce_year": yr,
            "total": len(g),
            "registered": int(g["has_retail"].sum()),
            "coverage_rate": g["has_retail"].mean(),
        })
    year_cov = pd.DataFrame(_yc_rows)
    if len(year_cov) > 0:
        fig = dual_axis_chart(
            year_cov, x="announce_year",
            y1="total", y2="coverage_rate",
            y1_name="公告型号数", y2_name="上牌覆盖率",
            height=380,
        )
        fig.update_layout(xaxis_title="公告年份", yaxis2_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("早年批次覆盖率高是因为有足够时间上牌；近年批次覆盖率低是因为上牌数据仅到 2025 年")

# ── Tab 3: 配置-市场表现 ─────────────────────────────

with tab3:
    st.markdown("## 配置-市场表现")
    st.caption(f"基于成熟批次（≥{min_lag}月），按选定维度分析上牌覆盖率与销量")

    dim_label = st.selectbox("选择分析维度", list(DIM_OPTIONS.keys()), key="comp_dim")
    dim_col = DIM_OPTIONS[dim_label]

    agg = aggregate_by_config(df_mature, dim_col)
    if len(agg) == 0:
        st.info("当前维度无数据")
    else:
        agg_show = agg[agg["total_models"] >= 10].copy()
        agg_show["coverage_pct"] = (agg_show["coverage_rate"] * 100).round(1)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"### {dim_label} — 上牌覆盖率")
            fig = bar_h(agg_show, x="coverage_pct", y=dim_col,
                        title="", height=max(350, len(agg_show) * 30))
            fig.update_layout(xaxis_title="覆盖率 (%)")
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown(f"### {dim_label} — 上牌销量")
            fig = bar_h(agg_show, x="retail_qty", y=dim_col,
                        title="", height=max(350, len(agg_show) * 30))
            fig.update_layout(xaxis_title="2025年上牌量")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 交叉维度热力图：能源类型 × 车辆大类")
        matrix = cross_dimension_matrix(df_mature, "energy_clean", "vehicle_category")
        if matrix.size > 0:
            fig = px.imshow(
                (matrix * 100).round(1),
                text_auto=".1f",
                color_continuous_scale="Blues",
                labels=dict(x="车辆大类", y="能源类型", color="覆盖率(%)"),
            )
            _apply_layout(fig, "", height=max(350, len(matrix) * 40))
            fig.update_layout(margin=dict(l=120, t=40))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 详细数据")
        display_cols = {
            dim_col: dim_label, "total_models": "公告型号数",
            "reg_models": "有上牌型号", "coverage_pct": "覆盖率(%)",
            "retail_qty": "上牌量",
        }
        st.dataframe(
            agg_show[[c for c in display_cols if c in agg_show.columns]]
            .rename(columns=display_cols),
            use_container_width=True, hide_index=True,
        )

# ── Tab 4: ZF 聚焦分析 ───────────────────────────────

with tab4:
    st.markdown("## ZF 聚焦分析")
    st.caption(f"基于成熟批次（≥{min_lag}月），从整体概览、制动产品、变速箱、细分市场等维度深入分析 ZF 配套车型的市场表现")

    # ── 4.0 全局 KPI ──
    zf_all = df_mature[df_mature["parsed_zf_mention"].fillna(False).astype(bool)]
    non_zf = df_mature[~df_mature["parsed_zf_mention"].fillna(False).astype(bool)]
    zf_stats = registration_coverage(zf_all)
    non_zf_stats = registration_coverage(non_zf)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("ZF 型号数", f"{zf_stats['total_models']:,}")
    k2.metric("ZF 上牌覆盖率", f"{zf_stats['coverage_rate']:.1%}")
    k3.metric("ZF 上牌量", f"{zf_stats['total_retail_qty']:,}")
    k4.metric("非ZF 上牌覆盖率", f"{non_zf_stats['coverage_rate']:.1%}")
    gap = zf_stats['coverage_rate'] - non_zf_stats['coverage_rate']
    k5.metric("ZF vs 市场差距", f"{gap:+.1%}")

    # ── 4.1 制动系统细分 ──
    st.markdown("---")
    st.markdown("### 1. 制动系统 — ZF vs 竞品上牌对比")

    braking_df = zf_braking_breakdown(df_mature)
    if len(braking_df) > 0:
        braking_df["覆盖率(%)"] = (braking_df["覆盖率"] * 100).round(1)

        col_brake1, col_brake2 = st.columns(2)
        with col_brake1:
            fig = px.bar(braking_df, x="分类", y="覆盖率(%)",
                         text="覆盖率(%)", color="分类",
                         color_discrete_sequence=ZF_COLORS)
            _apply_layout(fig, "制动系统分类 — 上牌覆盖率", 420)
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}%")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_brake2:
            fig = px.bar(braking_df, x="分类", y="上牌量",
                         text="上牌量", color="分类",
                         color_discrete_sequence=ZF_COLORS)
            _apply_layout(fig, "制动系统分类 — 上牌量", 420)
            fig.update_traces(textposition="outside", texttemplate="%{text:,}")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            braking_df[["分类", "公告型号数", "有上牌型号", "覆盖率(%)", "上牌量"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("制动系统数据不足")

    # ── 4.2 ZF ABS/EBS 产品型号级分析 ──
    st.markdown("---")
    st.markdown("### 2. ZF ABS/EBS 产品型号上牌表现 (Top 15)")
    st.caption("基于 ZF 配套车型的 ABS/EBS 型号字段拆分统计")

    prod_df = zf_product_registration(df_mature, top_n=15)
    if len(prod_df) > 0:
        prod_df["coverage_pct"] = (prod_df["coverage_rate"] * 100).round(1)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig = px.bar(prod_df, x="total", y="model", orientation="h",
                         text="total", color_discrete_sequence=[ZF_BLUE])
            _apply_layout(fig, "ZF 产品型号 — 配套车型数量", max(400, len(prod_df) * 32))
            fig.update_traces(textposition="outside")
            fig.update_layout(yaxis=dict(autorange="reversed", automargin=True),
                              xaxis_title="配套车型数")
            st.plotly_chart(fig, use_container_width=True)

        with col_p2:
            fig = px.bar(prod_df, x="coverage_pct", y="model", orientation="h",
                         text="coverage_pct", color_discrete_sequence=["#FF8C00"])
            _apply_layout(fig, "ZF 产品型号 — 上牌覆盖率", max(400, len(prod_df) * 32))
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}%")
            fig.update_layout(yaxis=dict(autorange="reversed", automargin=True),
                              xaxis_title="覆盖率 (%)")
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            prod_df.rename(columns={
                "model": "产品型号", "total": "配套车型数",
                "registered": "有上牌型号", "coverage_pct": "覆盖率(%)",
                "retail_qty": "上牌量",
            }).drop(columns=["coverage_rate"], errors="ignore"),
            use_container_width=True, hide_index=True,
        )

        with st.expander("产品型号说明"):
            st.markdown("""
- **ABS-E 4S / ABS-E**: 威伯科（WABCO，现ZF）经典 ABS 产品线
- **EBS3 / EBS 5**: 电子制动系统，高端市场定位
- **CM-EBS**: WABCO 模块化 EBS 产品
- **CM2XL-4S / CM4XL-4S**: 瑞立科密与 WABCO 合资产品
- 以上为参考信息，具体以 ZF 官方产品型号目录为准
""")
    else:
        st.info("无 ZF ABS/EBS 产品型号数据")

    # ── 4.3 ABS 供应商竞争格局 ──
    st.markdown("---")
    st.markdown("### 3. ABS 供应商竞争格局")
    st.caption("展示主要 ABS 供应商的公告配套量与上牌表现，ZF 系供应商（威伯科/WABCO/瑞立科密/采埃孚）高亮标注")

    supplier_df = zf_abs_supplier_competition(df_mature, top_n=12)
    if len(supplier_df) > 0:
        supplier_df["coverage_pct"] = (supplier_df["coverage_rate"] * 100).round(1)
        supplier_df["tag"] = supplier_df["is_zf_family"].map({True: "ZF 系", False: "竞品"})

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig = px.bar(supplier_df, x="total", y="supplier", orientation="h",
                         text="total", color="tag",
                         color_discrete_map={"ZF 系": ZF_BLUE, "竞品": "#999999"})
            _apply_layout(fig, "ABS 供应商 — 配套车型数量", max(400, len(supplier_df) * 32))
            fig.update_traces(textposition="outside")
            fig.update_layout(yaxis=dict(autorange="reversed", automargin=True),
                              xaxis_title="配套车型数")
            st.plotly_chart(fig, use_container_width=True)

        with col_s2:
            fig = px.bar(supplier_df, x="coverage_pct", y="supplier", orientation="h",
                         text="coverage_pct", color="tag",
                         color_discrete_map={"ZF 系": ZF_BLUE, "竞品": "#999999"})
            _apply_layout(fig, "ABS 供应商 — 上牌覆盖率", max(400, len(supplier_df) * 32))
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}%")
            fig.update_layout(yaxis=dict(autorange="reversed", automargin=True),
                              xaxis_title="覆盖率 (%)")
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            supplier_df.rename(columns={
                "supplier": "供应商", "total": "配套型号数",
                "registered": "有上牌型号", "coverage_pct": "覆盖率(%)",
                "retail_qty": "上牌量", "tag": "分类",
            }).drop(columns=["coverage_rate", "is_zf_family"], errors="ignore"),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("ABS 供应商数据不足")

    # ── 4.4 电桥/电驱动供应商分析 ──
    st.markdown("---")
    st.markdown("### 4. 电桥/电驱动供应商上牌分析")
    st.caption("基于公告 bridge_maker_clean 字段，展示电驱动/电桥供应商竞争格局，ZF 在电桥领域的市场地位")

    eaxle_df = zf_eaxle_analysis(df_mature)
    if len(eaxle_df) > 0:
        eaxle_df["coverage_pct"] = (eaxle_df["coverage_rate"] * 100).round(1)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            fig = px.bar(eaxle_df, x="supplier", y="total",
                         text="total", color_discrete_sequence=[ZF_BLUE])
            _apply_layout(fig, "电桥供应商 — 配套车型数量", 420)
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        with col_e2:
            fig = px.bar(eaxle_df, x="supplier", y="coverage_pct",
                         text="coverage_pct", color_discrete_sequence=["#FF8C00"])
            _apply_layout(fig, "电桥供应商 — 上牌覆盖率", 420)
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}%")
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            eaxle_df.rename(columns={
                "supplier": "供应商", "total": "配套型号数",
                "registered": "有上牌型号", "coverage_pct": "覆盖率(%)",
                "retail_qty": "上牌量",
            }).drop(columns=["coverage_rate"], errors="ignore"),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("电桥/电驱动供应商数据不足（仅新能源车型有此字段）")

    # ── 4.5 电驱动拓扑结构 ──
    st.markdown("---")
    st.markdown("### 5. 电驱动拓扑结构 — ZF vs 全市场")
    st.caption("对比不同电驱动拓扑（集中驱动/电驱桥/OEM自研等）的上牌表现，以及 ZF 在各拓扑中的参与度")

    topo_df = zf_drive_topology_analysis(df_mature)
    if len(topo_df) > 0:
        topo_df["coverage_pct"] = (topo_df["coverage_rate"] * 100).round(1)
        topo_df["zf_coverage_pct"] = (topo_df["zf_coverage_rate"] * 100).round(1)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            topo_melt = topo_df[["topology", "coverage_pct", "zf_coverage_pct"]].melt(
                id_vars="topology", var_name="对比", value_name="覆盖率(%)")
            topo_melt["对比"] = topo_melt["对比"].map({"coverage_pct": "全市场", "zf_coverage_pct": "ZF 配套"})
            fig = grouped_bar(topo_melt, x="topology", y="覆盖率(%)",
                              color="对比", title="电驱动拓扑 — 上牌覆盖率对比", height=420)
            fig.update_layout(xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

        with col_t2:
            topo_melt2 = topo_df[["topology", "retail_qty", "zf_retail_qty"]].melt(
                id_vars="topology", var_name="对比", value_name="上牌量")
            topo_melt2["对比"] = topo_melt2["对比"].map({"retail_qty": "全市场", "zf_retail_qty": "ZF 配套"})
            fig = grouped_bar(topo_melt2, x="topology", y="上牌量",
                              color="对比", title="电驱动拓扑 — 上牌量对比", height=420)
            fig.update_layout(xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            topo_df.rename(columns={
                "topology": "驱动拓扑", "total": "总型号数",
                "registered": "有上牌型号", "coverage_pct": "覆盖率(%)",
                "retail_qty": "上牌量", "zf_total": "ZF型号数",
                "zf_registered": "ZF有上牌", "zf_coverage_pct": "ZF覆盖率(%)",
                "zf_retail_qty": "ZF上牌量",
            }).drop(columns=["coverage_rate", "zf_coverage_rate"], errors="ignore"),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("电驱动拓扑数据不足（仅新能源车型有此字段）")

    # ── 4.6 变速箱维度 ──
    st.markdown("---")
    st.markdown("### 6. 变速箱类型 — ZF 配套上牌分析")

    if "transmission_type" in df_mature.columns:
        tx_data = []
        for tx_type in ["自动", "手动", "AMT"]:
            tx_mask = df_mature["transmission_type"].fillna("").astype(str).str.contains(tx_type, case=False, na=False)
            tx_sub = df_mature[tx_mask]
            if len(tx_sub) == 0:
                continue
            tx_zf = tx_sub[tx_sub["parsed_zf_mention"].fillna(False).astype(bool)]
            tx_non_zf = tx_sub[~tx_sub["parsed_zf_mention"].fillna(False).astype(bool)]
            tx_stats = registration_coverage(tx_sub)
            tx_zf_stats = registration_coverage(tx_zf) if len(tx_zf) > 0 else {"total_models": 0, "registered_models": 0, "coverage_rate": 0, "total_retail_qty": 0}
            tx_data.append({
                "变速箱类型": tx_type,
                "总型号数": tx_stats["total_models"],
                "总上牌量": tx_stats["total_retail_qty"],
                "总覆盖率": tx_stats["coverage_rate"],
                "ZF型号数": tx_zf_stats["total_models"],
                "ZF上牌量": tx_zf_stats["total_retail_qty"],
                "ZF覆盖率": tx_zf_stats["coverage_rate"],
            })
        if tx_data:
            tx_df = pd.DataFrame(tx_data)
            tx_df["总覆盖率(%)"] = (tx_df["总覆盖率"] * 100).round(1)
            tx_df["ZF覆盖率(%)"] = (tx_df["ZF覆盖率"] * 100).round(1)

            col_tx1, col_tx2 = st.columns(2)
            with col_tx1:
                tx_melt = tx_df[["变速箱类型", "总覆盖率(%)", "ZF覆盖率(%)"]].melt(
                    id_vars="变速箱类型", var_name="对比", value_name="覆盖率(%)")
                tx_melt["对比"] = tx_melt["对比"].map({"总覆盖率(%)": "全市场", "ZF覆盖率(%)": "ZF 配套"})
                fig = grouped_bar(tx_melt, x="变速箱类型", y="覆盖率(%)",
                                  color="对比", title="变速箱类型 — 上牌覆盖率对比", height=400)
                fig.update_layout(yaxis_title="覆盖率 (%)")
                st.plotly_chart(fig, use_container_width=True)

            with col_tx2:
                tx_melt2 = tx_df[["变速箱类型", "总上牌量", "ZF上牌量"]].melt(
                    id_vars="变速箱类型", var_name="对比", value_name="上牌量")
                tx_melt2["对比"] = tx_melt2["对比"].map({"总上牌量": "全市场", "ZF上牌量": "ZF 配套"})
                fig = grouped_bar(tx_melt2, x="变速箱类型", y="上牌量",
                                  color="对比", title="变速箱类型 — 上牌量对比", height=400)
                fig.update_layout(yaxis_title="上牌量")
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                tx_df[["变速箱类型", "总型号数", "总上牌量", "总覆盖率(%)",
                        "ZF型号数", "ZF上牌量", "ZF覆盖率(%)"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("变速箱类型数据不足")
    else:
        st.info("公告数据中无变速箱类型字段")

    # ── 4.7 ZF 细分市场：车辆大类 × 能源类型 ──
    st.markdown("---")
    st.markdown("### 7. ZF 细分市场上牌表现（车辆大类 × 能源类型）")

    ve_df = zf_by_vehicle_energy(df_mature)
    if len(ve_df) > 0:
        ve_df["coverage_pct"] = (ve_df["coverage_rate"] * 100).round(1)

        ve_pivot = ve_df.pivot_table(index="vehicle_category", columns="energy_clean",
                                     values="coverage_pct", fill_value=0)
        if ve_pivot.size > 0:
            fig = px.imshow(
                ve_pivot, text_auto=".1f",
                color_continuous_scale="Blues",
                labels=dict(x="能源类型", y="车辆大类", color="覆盖率(%)"),
            )
            _apply_layout(fig, "ZF 车辆大类×能源 上牌覆盖率热力图", max(350, len(ve_pivot) * 45))
            fig.update_layout(margin=dict(l=120, t=50))
            st.plotly_chart(fig, use_container_width=True)

        ve_qty_pivot = ve_df.pivot_table(index="vehicle_category", columns="energy_clean",
                                          values="retail_qty", fill_value=0)
        if ve_qty_pivot.size > 0:
            fig = px.imshow(
                ve_qty_pivot, text_auto=",",
                color_continuous_scale="Oranges",
                labels=dict(x="能源类型", y="车辆大类", color="上牌量"),
            )
            _apply_layout(fig, "ZF 车辆大类×能源 上牌量热力图", max(350, len(ve_qty_pivot) * 45))
            fig.update_layout(margin=dict(l=120, t=50))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            ve_df.rename(columns={
                "vehicle_category": "车辆大类", "energy_clean": "能源类型",
                "total": "ZF型号数", "registered": "有上牌型号",
                "coverage_pct": "覆盖率(%)", "retail_qty": "上牌量",
            }).drop(columns=["coverage_rate"], errors="ignore"),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("ZF 细分市场数据不足")

    # ── 4.8 维度对比（保留原有功能） ──
    st.markdown("---")
    st.markdown("### 8. 自选维度 — ZF vs 全市场")

    zf_dim_label = st.selectbox("分析维度", list(DIM_OPTIONS.keys()), key="zf_dim")
    zf_dim_col = DIM_OPTIONS[zf_dim_label]

    zf_agg = zf_vs_market_by_dim(df_mature, zf_dim_col)
    if len(zf_agg) == 0:
        st.info("无数据")
    else:
        zf_show = zf_agg[zf_agg["total_models"] >= 10].copy()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"#### {zf_dim_label} — ZF vs 全市场上牌覆盖率")
            if len(zf_show) > 0:
                plot_df = zf_show[[zf_dim_col, "coverage_rate", "zf_coverage_rate"]].melt(
                    id_vars=zf_dim_col,
                    value_vars=["coverage_rate", "zf_coverage_rate"],
                    var_name="group", value_name="rate",
                )
                plot_df["group"] = plot_df["group"].map({
                    "coverage_rate": "全市场", "zf_coverage_rate": "ZF 配套",
                })
                plot_df["rate_pct"] = (plot_df["rate"] * 100).round(1)
                fig = grouped_bar(plot_df, x=zf_dim_col, y="rate_pct",
                                  color="group", title="", height=420)
                fig.update_layout(yaxis_title="覆盖率 (%)", xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown(f"#### {zf_dim_label} — ZF 渗透率（公告侧 vs 上牌侧）")
            if len(zf_show) > 0:
                pen_df = zf_show[[zf_dim_col, "zf_penetration_announce", "zf_penetration_retail"]].melt(
                    id_vars=zf_dim_col,
                    value_vars=["zf_penetration_announce", "zf_penetration_retail"],
                    var_name="side", value_name="penetration",
                )
                pen_df["side"] = pen_df["side"].map({
                    "zf_penetration_announce": "公告侧",
                    "zf_penetration_retail": "上牌侧",
                })
                pen_df["pen_pct"] = (pen_df["penetration"] * 100).round(1)
                fig = grouped_bar(pen_df, x=zf_dim_col, y="pen_pct",
                                  color="side", title="", height=420)
                fig.update_layout(yaxis_title="渗透率 (%)", xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

# ── Tab 5: Executive Summary ──────────────────────────

with tab5:
    st.markdown("## Executive Summary")
    st.caption(
        f"基于成熟批次（≥{min_lag}月）数据自动生成，"
        "从 ZF Tier-1 视角聚焦终端零售表现与市场定位"
    )

    exec_paragraphs = generate_executive_summary(df_comp=df_comp, df_mature=df_mature)

    if not exec_paragraphs:
        st.info("当前条件下数据不足，无法生成分析摘要")
    else:
        for para in exec_paragraphs:
            st.markdown(para)
            st.markdown("")  # spacing
