"""China CV Data App — Intro / 首页"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from src.config import ZF_MARKET_SEGMENTS, NON_ZF_CATEGORIES


@st.cache_data(ttl=3600, show_spinner="加载数据中...")
def _load_data():
    from src.data_loader import load_cleaned, CLEANED_PARQUET
    from src.data_cleaner import run_full_clean
    if not CLEANED_PARQUET.exists():
        run_full_clean()
    return load_cleaned(columns=["batch", "vehicle_category", "energy_clean", "manufacturer"])


df_all = _load_data()

zf_core = ZF_MARKET_SEGMENTS["ZF 核心市场 (全部)"]

st.markdown("# China CV Data App")

st.markdown("""
> **数据源**：中国工信部《道路机动车辆生产企业及产品公告》，采集自
> [商用车网 cn357.com](https://www.cn357.com)，覆盖第 290–388 批（约 2017-10 至 2025-12）。

本平台对 **82 万+** 车型公告数据进行结构化清洗与多维分析，提供市场趋势、
电动化深度洞察、制动系统竞争格局、变速箱覆盖、供应链分布等专题看板，
并支持自由字段探索和数据导出。

**数据覆盖**：
- **公告数据**：第 290–388 批工信部公告，涵盖车型参数、制动配置、供应链等字段
- **零售数据**：2025 年商用车上牌/保险统计，反映终端销量表现

请从左侧菜单选择分析页面。
""")

st.info(
    "**数据质量提示**：公告数据存在字段缺失、填写不规范等问题。"
    "部分分析（如电驱动桥 vs 集中驱动的拓扑推断）基于企业名称关键词启发式判断，"
    "结论仅供参考，详见各页面的方法说明。"
)

st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("总车型数", f"{len(df_all):,}")

zf_df = df_all[df_all["vehicle_category"].isin(zf_core)]
col2.metric("ZF 核心市场", f"{len(zf_df):,}", f"{len(zf_df)/len(df_all):.1%}")
col3.metric("纯电动(BEV)", f"{(zf_df['energy_clean']=='纯电动').sum():,}",
            f"{(zf_df['energy_clean']=='纯电动').mean():.1%}")
col4.metric("主机厂数量", f"{zf_df['manufacturer'].nunique():,}")
col5.metric("覆盖批次", f"{df_all['batch'].nunique()}")

st.markdown("---")
st.markdown("#### 车辆类别分布 (全量数据)")
cat_counts = df_all["vehicle_category"].value_counts()
col_data = []
for cat, cnt in cat_counts.items():
    marker = " ✅" if cat in (zf_core or []) else " ⛔"
    if cat in NON_ZF_CATEGORIES:
        marker = " ⛔"
    col_data.append({"类别": cat, "数量": f"{cnt:,}", "占比": f"{cnt/len(df_all):.1%}", "ZF相关": marker})

st.dataframe(pd.DataFrame(col_data), use_container_width=True, hide_index=True)
