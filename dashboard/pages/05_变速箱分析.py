"""Page 5: 变速箱分析"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.transmission import (
    transmission_type_distribution, transmission_by_energy, transmission_coverage,
)
from src.charts import pie_chart, grouped_bar, line_chart, bar_h

st.markdown("# ⚙️ 变速箱分析 Transmission")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

st.info("⚠️ 变速箱类型数据覆盖率较低 (约 3-5%)，结果仅供参考。大量车型未填写变速箱字段。")

# ── 变速箱类型 ──
col1, col2 = st.columns(2)
with col1:
    st.subheader("变速箱类型分布")
    tt = transmission_type_distribution(df_f)
    if len(tt) > 0:
        fig = pie_chart(tt, names="type", values="count", height=350)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("变速箱类型 × 能源类型")
    te = transmission_by_energy(df_f)
    if len(te) > 0:
        fig = grouped_bar(te, x="energy_clean", y="count", color="transmission_type", height=350)
        st.plotly_chart(fig, use_container_width=True)

# ── 覆盖率趋势 ──
st.subheader("变速箱字段覆盖率趋势")
cov = transmission_coverage(df_trend)
cov_range = cov[cov["batch"].between(b_min, b_max)]
fig = line_chart(cov_range, x="batch_date", y="coverage", title="", height=300)
fig.update_layout(yaxis_title="覆盖率", yaxis_tickformat=".1%")
st.plotly_chart(fig, use_container_width=True)
