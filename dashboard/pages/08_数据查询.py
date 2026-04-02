"""Page 8: 数据查询与导出"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dashboard.sidebar import apply_sidebar_filters

st.markdown("# 📋 数据查询 Data Explorer")

df_f = apply_sidebar_filters(default_batch_window=6)

if len(df_f) == 0:
    st.warning("当前筛选条件下无数据")
    st.stop()

# ── 附加筛选器 (能源 / 车辆类型 / 关键词) ──
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 附加筛选**")

energy_types = ["全部"] + sorted(df_f["energy_clean"].dropna().unique().tolist())
sel_energy = st.sidebar.selectbox("能源类型", energy_types)
if sel_energy != "全部":
    df_f = df_f[df_f["energy_clean"] == sel_energy]

categories = ["全部"] + sorted(df_f["vehicle_category"].dropna().unique().tolist())
sel_cat = st.sidebar.selectbox("车辆大类", categories)
if sel_cat != "全部":
    df_f = df_f[df_f["vehicle_category"] == sel_cat]

keyword = st.sidebar.text_input("关键词搜索 (品牌/企业/型号)")
if keyword:
    mask = (
        df_f["brand"].fillna("").str.contains(keyword, case=False, na=False) |
        df_f["manufacturer"].fillna("").str.contains(keyword, case=False, na=False) |
        df_f["model_code"].fillna("").str.contains(keyword, case=False, na=False) |
        df_f["engine_maker"].fillna("").str.contains(keyword, case=False, na=False) |
        df_f["_remarks_raw"].fillna("").str.contains(keyword, case=False, na=False)
    )
    df_f = df_f[mask]

# ── 列选择 ──
default_cols = [
    "batch", "batch_date", "model_code", "brand", "vehicle_type", "vehicle_category",
    "manufacturer_display", "energy_clean", "power_kw", "total_mass",
    "engine_maker_display", "abs_maker_display", "bridge_maker_clean",
]
all_cols = list(df_f.columns)
selected_cols = st.multiselect("选择显示列", all_cols, default=[c for c in default_cols if c in all_cols])

if not selected_cols:
    selected_cols = default_cols

# ── 显示 ──
st.markdown(f"**共 {len(df_f):,} 条记录**")

PAGE_SIZE = 100
total_pages = max(1, (len(df_f) - 1) // PAGE_SIZE + 1)
page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)
start = (page - 1) * PAGE_SIZE
end = start + PAGE_SIZE

st.dataframe(df_f[selected_cols].iloc[start:end], use_container_width=True, hide_index=True, height=600)
st.caption(f"显示第 {start+1}-{min(end, len(df_f))} 条，共 {len(df_f):,} 条，共 {total_pages} 页")

# ── 导出 ──
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    csv_data = df_f[selected_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 导出当前筛选 (CSV)", csv_data,
                       f"vehicle_data_filtered.csv", "text/csv")
with col2:
    st.info("完整数据请使用离线脚本: `python -m scripts.export_excel`")
