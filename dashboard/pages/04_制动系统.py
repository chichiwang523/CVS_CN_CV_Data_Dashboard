"""Page 4: 制动系统分析 — ABS/EBS 竞争格局"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from dashboard.sidebar import apply_sidebar_filters, _load
from src.analysis.braking import (
    abs_supplier_share_fast, abs_supplier_trend,
    ebs_penetration_trend, zf_product_breakdown,
)
from src.charts import pie_chart, line_chart, dual_axis_chart, bar_h, area_chart, ZF_COLORS

st.markdown("# 🛑 制动系统分析 Braking System")
st.caption("ABS/EBS 市场份额 — ZF/采埃孚 vs Bosch/博世 vs Knorr/克诺尔")

df_f = apply_sidebar_filters(default_batch_window=24)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

df_full = _load()
seg_cats = df_f["vehicle_category"].unique().tolist()
df_trend = df_full[df_full["vehicle_category"].isin(seg_cats)]
b_min, b_max = int(df_f["batch"].min()), int(df_f["batch"].max())

# ── ABS 供应商份额 ──
col1, col2 = st.columns(2)
with col1:
    st.subheader("ABS 供应商市场份额")
    share = abs_supplier_share_fast(df_f)
    fig = pie_chart(share, names="supplier", values="count", height=400)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("ABS 供应商份额排名")
    share_sorted = share.sort_values("count", ascending=False)
    share_sorted["占比"] = (share_sorted["count"] / share_sorted["count"].sum() * 100).round(1).astype(str) + "%"
    st.dataframe(share_sorted.rename(columns={"supplier": "供应商", "count": "车型数"}),
                 use_container_width=True, hide_index=True)

# ── ABS 份额趋势 ──
st.markdown("---")
st.subheader("ABS 供应商份额趋势")
trend_df = abs_supplier_trend(df_trend)
trend_range = trend_df[trend_df["batch"].between(b_min, b_max)]
main_suppliers = ["ZF/采埃孚", "Knorr/克诺尔", "Bosch/博世", "瑞立科密", "万安科技"]
trend_main = trend_range[trend_range["abs_supplier"].isin(main_suppliers)]
fig = line_chart(trend_main, x="batch_date", y="ratio", color="abs_supplier",
                 title="", height=420)
fig.update_layout(xaxis_title="批次", yaxis_title="份额", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# ── EBS 渗透率 + ZF 产品 ──
col3, col4 = st.columns(2)
with col3:
    st.subheader("EBS 渗透率趋势")
    ebs_df = ebs_penetration_trend(df_trend)
    ebs_range = ebs_df[ebs_df["batch"].between(b_min, b_max)]
    fig = dual_axis_chart(ebs_range, x="batch_date", y1="has_ebs", y2="ebs_ratio",
                          y1_name="提及 EBS 车型数", y2_name="EBS 渗透率", height=380)
    fig.update_layout(yaxis2_tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("ZF/采埃孚 ABS 产品型号 Top 15")
    zf_models = zf_product_breakdown(df_f)
    if len(zf_models) > 0:
        fig = bar_h(zf_models, x="count", y="model", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("所选范围无 ZF 产品数据")

# ── 关键洞察 ──
st.markdown("---")
st.subheader("📋 关键洞察")
total_abs = df_f["parsed_has_abs"].sum()
total_ebs = df_f["parsed_has_ebs"].sum()
zf_total = df_f["parsed_zf_mention"].sum()
bosch_total = df_f["parsed_bosch_mention"].sum()
knorr_total = df_f["parsed_knorr_mention"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("提及 ABS 车型", f"{total_abs:,}", f"占总量 {total_abs/len(df_f):.1%}")
c2.metric("提及 EBS 车型", f"{total_ebs:,}", f"占总量 {total_ebs/len(df_f):.1%}")
c3.metric("ZF 配套提及", f"{zf_total:,}", f"占 ABS 车型 {zf_total/total_abs:.1%}" if total_abs else "")
c4.metric("竞品总提及", f"{bosch_total+knorr_total:,}",
          f"Bosch {bosch_total:,} + Knorr {knorr_total:,}")
