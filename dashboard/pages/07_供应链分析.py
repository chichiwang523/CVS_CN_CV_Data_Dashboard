"""Page 7: 供应链分析"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dashboard.sidebar import apply_sidebar_filters
from src.analysis.energy import battery_cell_suppliers, battery_pack_suppliers, battery_chemistry_distribution
from src.charts import bar_h, pie_chart, line_chart, ZF_COLORS
from src.config import BATCH_DATES

st.set_page_config(page_title="供应链分析", layout="wide")
st.markdown("# 🔗 供应链分析 Supply Chain")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

# ── 发动机/电机供应商 ──
col1, col2 = st.columns(2)
with col1:
    st.subheader("发动机/电机供应商 Top 15 (传统燃料)")
    trad = df_f[df_f["energy_clean"].isin(["柴油", "汽油"])]
    eng_top = trad["engine_maker_display"].value_counts().head(15).reset_index()
    eng_top.columns = ["supplier", "count"]
    fig = bar_h(eng_top, x="count", y="supplier", height=420)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("电机供应商 Top 15 (BEV)")
    bev = df_f[df_f["energy_clean"] == "纯电动"]
    mot_top = bev["engine_maker_display"].value_counts().head(15).reset_index()
    mot_top.columns = ["supplier", "count"]
    fig = bar_h(mot_top, x="count", y="supplier", height=420)
    st.plotly_chart(fig, use_container_width=True)

# ── 电池供应商 ──
st.markdown("---")
col3, col4 = st.columns(2)
with col3:
    st.subheader("电芯供应商 Top 10")
    bcs = battery_cell_suppliers(df_f, 10)
    if len(bcs) > 0:
        fig = bar_h(bcs, x="count", y="display", height=380)
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("电池包供应商 Top 10")
    bps = battery_pack_suppliers(df_f, 10)
    if len(bps) > 0:
        fig = bar_h(bps, x="count", y="display", height=380)
        st.plotly_chart(fig, use_container_width=True)

# ── 桥供应商 ──
st.markdown("---")
col5, col6 = st.columns(2)
with col5:
    st.subheader("桥供应商分布")
    bridge = df_f[df_f["bridge_maker_clean"].notna() & (df_f["bridge_maker_clean"] != "") & (df_f["bridge_maker_clean"] != "<NA>")]
    if len(bridge) > 0:
        br_top = bridge["bridge_maker_clean"].value_counts().head(10).reset_index()
        br_top.columns = ["supplier", "count"]
        fig = bar_h(br_top, x="count", y="supplier", height=350)
        st.plotly_chart(fig, use_container_width=True)

with col6:
    st.subheader("电池化学类型分布")
    bc = battery_chemistry_distribution(df_f)
    fig = pie_chart(bc, names="chemistry", values="count", height=350)
    st.plotly_chart(fig, use_container_width=True)
