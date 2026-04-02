"""Page 1: Dashboard — KPI + 趋势 + 自由字段探索"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.market import overview_kpis, energy_distribution_by_batch, top_manufacturers, batch_record_counts
from src.analysis.energy import bev_trend
from src.analysis.braking import ebs_penetration_trend
from src.charts import (
    kpi_card_html, area_chart, bar_h, bar_v, dual_axis_chart,
    line_chart, pie_chart, grouped_bar, scatter_chart,
    ZF_COLORS, ZF_BLUE, PLOTLY_LAYOUT, _apply_layout,
)

st.markdown("# 📊 Dashboard")

df_f = apply_sidebar_filters(default_batch_window=12)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

# ═══════════════════════════════════════════════════════════
# Quick Insights (固定 KPI + 趋势)
# ═══════════════════════════════════════════════════════════

kpis = overview_kpis(df_f)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("选定范围车型数", f"{kpis['total_records']:,}")
c2.metric("BEV 占比", f"{kpis['bev_ratio']:.1%}", f"共{kpis['bev_count']:,}台")
c3.metric("主机厂数量", f"{kpis['total_manufacturers']:,}")
c4.metric("能源类型数", f"{kpis['energy_types']}")

zf_count = df_f["parsed_zf_mention"].sum()
zf_ratio = zf_count / len(df_f) if len(df_f) else 0
c5.metric("ZF 配套提及率", f"{zf_ratio:.1%}", f"共{zf_count:,}次")

st.markdown("---")

col_left, col_right = st.columns([3, 2])
with col_left:
    st.subheader("能源类型结构趋势")
    energy_df = energy_distribution_by_batch(df_trend)
    energy_range = energy_df[energy_df["batch"].between(b_min, b_max)]
    fig = area_chart(energy_range, x="batch_date", y="ratio", color="energy_clean",
                     title="", height=380)
    fig.update_layout(xaxis_title="批次 (月份)", yaxis_title="占比", yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Top 10 主机厂")
    top_mfr = top_manufacturers(df_f, 10)
    fig = bar_h(top_mfr, x="count", y="manufacturer_display", title="", height=380)
    st.plotly_chart(fig, use_container_width=True)

col_left2, col_right2 = st.columns(2)
with col_left2:
    st.subheader("新能源车型占比趋势")
    bev_df = bev_trend(df_trend)
    bev_range = bev_df[bev_df["batch"].between(b_min, b_max)]
    fig = dual_axis_chart(bev_range, x="batch_date", y1="bev", y2="bev_ratio",
                          y1_name="BEV 数量", y2_name="BEV 占比", title="", height=350)
    fig.update_layout(yaxis2_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with col_right2:
    st.subheader("EBS 渗透率趋势汇总")
    ebs_df = ebs_penetration_trend(df_trend)
    ebs_range = ebs_df[ebs_df["batch"].between(b_min, b_max)]
    fig = dual_axis_chart(ebs_range, x="batch_date", y1="has_ebs", y2="ebs_ratio",
                          y1_name="EBS 数量", y2_name="EBS 占比", title="", height=350)
    fig.update_layout(yaxis2_tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# 自由字段探索 (Free Exploration)
# ═══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("## 🔍 自由字段探索 Free Exploration")
st.caption("选择任意字段生成分布图表，支持交叉分析和数值统计。")

CATEGORICAL_FIELDS = {
    "能源类型 (energy_clean)": "energy_clean",
    "车辆大类 (vehicle_category)": "vehicle_category",
    "主机厂 (manufacturer_display)": "manufacturer_display",
    "品牌 (brand)": "brand",
    "发动机/电机企业 (engine_maker_display)": "engine_maker_display",
    "ABS 供应商 (abs_maker_display)": "abs_maker_display",
    "桥供应商 (bridge_maker_clean)": "bridge_maker_clean",
    "质量分级 (mass_class)": "mass_class",
    "排放标准 (emission_standard)": "emission_standard",
    "电池化学类型 (parsed_battery_chemistry)": "parsed_battery_chemistry",
    "电驱拓扑 (parsed_drive_topology)": "parsed_drive_topology",
    "TZ后缀类型 (parsed_tz_suffix_type)": "parsed_tz_suffix_type",
    "车辆类型 (vehicle_type)": "vehicle_type",
}

NUMERIC_FIELDS = {
    "功率 kW (power_kw)": "power_kw",
    "总质量 kg (total_mass)": "total_mass",
    "整备质量 kg (curb_weight)": "curb_weight",
    "排量 mL (displacement)": "displacement",
    "车长 mm (length)": "length",
    "车宽 mm (width)": "width",
    "额定功率 kW (parsed_motor_rated_kw)": "parsed_motor_rated_kw",
    "峰值功率 kW (parsed_motor_peak_kw)": "parsed_motor_peak_kw",
    "电池容量 kWh (parsed_battery_kwh)": "parsed_battery_kwh",
}

BOOLEAN_FIELDS = {
    "提及 ABS (parsed_has_abs)": "parsed_has_abs",
    "提及 EBS (parsed_has_ebs)": "parsed_has_ebs",
    "ZF 配套提及 (parsed_zf_mention)": "parsed_zf_mention",
    "Bosch 提及 (parsed_bosch_mention)": "parsed_bosch_mention",
    "Knorr 提及 (parsed_knorr_mention)": "parsed_knorr_mention",
}

ALL_FIELDS = {"分类字段": CATEGORICAL_FIELDS, "数值字段": NUMERIC_FIELDS, "布尔字段": BOOLEAN_FIELDS}

explore_col1, explore_col2 = st.columns([1, 1])

with explore_col1:
    field_group = st.selectbox("字段类型", list(ALL_FIELDS.keys()), key="fg1")
    field_options = ALL_FIELDS[field_group]
    selected_label = st.selectbox("选择字段", list(field_options.keys()), key="fl1")
    selected_col = field_options[selected_label]

with explore_col2:
    if field_group == "数值字段":
        st.markdown("**数值字段选项**")
        bins_count = st.slider("直方图分箱数", 10, 100, 30, key="bins1")
    else:
        top_n = st.slider("Top N 显示数量", 5, 50, 15, key="topn1")
        cross_field_label = st.selectbox(
            "交叉分析字段 (可选)",
            ["无"] + [k for k in CATEGORICAL_FIELDS.keys() if CATEGORICAL_FIELDS[k] != selected_col],
            key="cross1",
        )

# 字段统计摘要
series = df_f[selected_col]
stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
stat_c1.metric("总记录", f"{len(series):,}")
non_null = series.dropna()
if series.dtype == "string":
    non_null = non_null[non_null != ""]
stat_c2.metric("非空数", f"{len(non_null):,}")
stat_c3.metric("非空率", f"{len(non_null)/len(series):.1%}" if len(series) else "N/A")
stat_c4.metric("唯一值", f"{non_null.nunique():,}")

# ── 生成图表 ──
if field_group == "数值字段":
    num_data = pd.to_numeric(series, errors="coerce").dropna()
    if len(num_data) == 0:
        st.info("该字段无有效数值数据")
    else:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader(f"{selected_label} — 分布直方图")
            fig = px.histogram(
                num_data.to_frame(selected_col), x=selected_col,
                nbins=bins_count, color_discrete_sequence=[ZF_BLUE],
            )
            _apply_layout(fig, "", 400)
            fig.update_layout(xaxis_title=selected_label, yaxis_title="数量")
            st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            st.subheader(f"{selected_label} — 箱线图")
            fig = px.box(
                num_data.to_frame(selected_col), y=selected_col,
                color_discrete_sequence=[ZF_BLUE],
            )
            _apply_layout(fig, "", 400)
            fig.update_layout(yaxis_title=selected_label)
            st.plotly_chart(fig, use_container_width=True)

        desc = num_data.describe()
        st.markdown(
            f"**统计**: 均值={desc['mean']:,.1f} | 中位数={desc['50%']:,.1f} | "
            f"最小={desc['min']:,.1f} | 最大={desc['max']:,.1f} | 标准差={desc['std']:,.1f}"
        )

elif field_group == "布尔字段":
    bool_counts = series.value_counts().reset_index()
    bool_counts.columns = ["value", "count"]
    bool_counts["value"] = bool_counts["value"].map({True: "是", False: "否"})
    fig = pie_chart(bool_counts, names="value", values="count",
                    title=selected_label, height=380)
    st.plotly_chart(fig, use_container_width=True)

else:
    clean_series = series.fillna("").astype(str)
    clean_series = clean_series[clean_series != ""]
    n_unique = clean_series.nunique()

    cross_col = None
    if cross_field_label != "无":
        cross_col = CATEGORICAL_FIELDS[cross_field_label]

    if cross_col is not None:
        st.subheader(f"{selected_label} × {cross_field_label} — 交叉分析")
        work_df = df_f[[selected_col, cross_col]].copy()
        work_df[selected_col] = work_df[selected_col].fillna("").astype(str)
        work_df[cross_col] = work_df[cross_col].fillna("").astype(str)
        work_df = work_df[(work_df[selected_col] != "") & (work_df[cross_col] != "")]

        top_vals = work_df[selected_col].value_counts().head(top_n).index.tolist()
        work_df = work_df[work_df[selected_col].isin(top_vals)]

        cross_unique = work_df[cross_col].nunique()
        if cross_unique > 10:
            top_cross = work_df[cross_col].value_counts().head(10).index.tolist()
            work_df = work_df[work_df[cross_col].isin(top_cross)]

        cross_agg = work_df.groupby([selected_col, cross_col]).size().reset_index(name="count")
        fig = grouped_bar(cross_agg, x=selected_col, y="count", color=cross_col,
                          title="", height=max(400, top_n * 20))
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    else:
        value_counts = clean_series.value_counts()

        if n_unique <= 12:
            st.subheader(f"{selected_label} — 分布饼图")
            vc_df = value_counts.reset_index()
            vc_df.columns = ["value", "count"]
            fig = pie_chart(vc_df, names="value", values="count", height=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.subheader(f"{selected_label} — Top {top_n}")
            vc_df = value_counts.head(top_n).reset_index()
            vc_df.columns = ["value", "count"]
            fig = bar_h(vc_df, x="count", y="value",
                        height=max(350, top_n * 25))
            st.plotly_chart(fig, use_container_width=True)

    if n_unique > 12:
        st.caption(f"共 {n_unique:,} 个唯一值，显示 Top {min(top_n, n_unique)}")
