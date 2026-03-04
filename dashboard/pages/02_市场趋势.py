"""Page 2: 市场趋势"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.market import (
    manufacturer_trend, vehicle_type_distribution,
    mass_distribution, concentration_trend, top_manufacturers,
)
from src.charts import area_chart, pie_chart, bar_h, line_chart, grouped_bar, ZF_COLORS

st.set_page_config(page_title="市场趋势", layout="wide")
st.markdown("# 📈 市场趋势 Market Trends")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

# ── 主机厂份额变化 ──
st.subheader("Top 10 主机厂趋势")
mfr_trend = manufacturer_trend(df_trend, 10)
mfr_range = mfr_trend[mfr_trend["batch"].between(b_min, b_max)]
fig = area_chart(mfr_range, x="batch_date", y="count", color="manufacturer_display", height=420)
fig.update_layout(xaxis_title="批次", yaxis_title="车型数")
st.plotly_chart(fig, use_container_width=True)

# ── 车辆类型 + 质量分布 ──
col1, col2 = st.columns(2)
with col1:
    st.subheader("车辆大类分布")
    vt = vehicle_type_distribution(df_f)
    cat_df = vt.groupby("vehicle_category")["count"].sum().reset_index().sort_values("count", ascending=False)
    fig = pie_chart(cat_df, names="vehicle_category", values="count", height=380)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("质量分级 × 能源类型")
    mass_df = mass_distribution(df_f)
    fig = grouped_bar(mass_df, x="mass_class", y="count", color="energy_clean", height=380)
    fig.update_layout(xaxis_title="质量分级", yaxis_title="数量")
    st.plotly_chart(fig, use_container_width=True)

# ── 品牌集中度 ──
st.subheader("品牌集中度趋势 (CR5 / CR10)")
cr5 = concentration_trend(df_trend, 5)
cr10 = concentration_trend(df_trend, 10)
cr5["指标"] = "CR5"
cr10["指标"] = "CR10"
cr5 = cr5.rename(columns={"CR5": "concentration"})
cr10 = cr10.rename(columns={"CR10": "concentration"})
cr_all = pd.concat([cr5[["batch_date", "batch", "concentration", "指标"]], cr10[["batch_date", "batch", "concentration", "指标"]]])
cr_range = cr_all[cr_all["batch"].between(b_min, b_max)]
fig = line_chart(cr_range, x="batch_date", y="concentration", color="指标", height=350)
fig.update_layout(yaxis_title="集中度", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# ── 车辆类型细分 Top 20 ──
st.subheader("车辆类型细分 Top 20")
vt_top = vt.head(20)
fig = bar_h(vt_top, x="count", y="vehicle_type", height=500)
st.plotly_chart(fig, use_container_width=True)
