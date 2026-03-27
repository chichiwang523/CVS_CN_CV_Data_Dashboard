"""Page 6: 竞争对手分析"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.competitor import (
    competitor_mention_trend, competitor_by_vehicle_category, competitor_by_manufacturer,
)
from src.charts import line_chart, grouped_bar, bar_h, ZF_COLORS

st.markdown("# 🏭 竞争对手分析 Competitor Analysis")
st.caption("ZF/采埃弗 vs Bosch/博世 vs Knorr/克诺尔 — 基于公告备注提及频次")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

# ── 提及率趋势 ──
st.subheader("竞争对手提及率趋势")
trend = competitor_mention_trend(df_trend)
trend_range = trend[trend["batch"].between(b_min, b_max)]
cols = ["ZF/采埃弗_ratio", "Bosch/博世_ratio", "Knorr/克诺尔_ratio"]
melted = trend_range.melt(id_vars=["batch_date"], value_vars=cols, var_name="competitor", value_name="ratio")
melted["competitor"] = melted["competitor"].str.replace("_ratio", "")
fig = line_chart(melted, x="batch_date", y="ratio", color="competitor", height=420)
fig.update_layout(yaxis_title="提及率 (占当批总车型)", yaxis_tickformat=".0%", xaxis_title="批次")
st.plotly_chart(fig, use_container_width=True)

# ── 按车辆类型 ──
st.subheader("竞争对手 × 车辆大类")
by_cat = competitor_by_vehicle_category(df_f)
cols_abs = ["ZF/采埃弗", "Bosch/博世", "Knorr/克诺尔"]
melted_cat = by_cat.melt(id_vars=["vehicle_category"], value_vars=cols_abs,
                          var_name="competitor", value_name="count")
fig = grouped_bar(melted_cat, x="vehicle_category", y="count", color="competitor",
                  title="各车辆类型中竞争对手提及次数", height=420)
st.plotly_chart(fig, use_container_width=True)

# ── 按主机厂 ──
st.subheader("Top 15 主机厂 × 竞争对手配套")
by_mfr = competitor_by_manufacturer(df_f, 15)
melted_mfr = by_mfr.melt(id_vars=["manufacturer"], value_vars=cols_abs,
                           var_name="competitor", value_name="count")
fig = grouped_bar(melted_mfr, x="manufacturer", y="count", color="competitor",
                  title="", height=450, barmode="group")
fig.update_layout(xaxis_tickangle=45)
st.plotly_chart(fig, use_container_width=True)

# ── 数据表 ──
st.subheader("详细数据")
st.dataframe(by_mfr.rename(columns={"manufacturer": "主机厂", "total": "总车型数"}),
             use_container_width=True, hide_index=True)
