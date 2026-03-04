"""
中国商用车公告数据分析 Agent — 主入口
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from src.config import ZF_MARKET_SEGMENTS, NON_ZF_CATEGORIES

st.set_page_config(
    page_title="中国商用车公告数据 Agent",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; padding-bottom: 1rem; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    h1, h2, h3 { color: #003399; }
    h1 { font-size: 2rem !important; margin-bottom: 0.2rem !important; }
    .stMetric label { font-size: 13px !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 28px !important; color: #003399; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner="加载数据中...")
def load_data():
    from src.data_loader import load_cleaned, CLEANED_PARQUET
    from src.data_cleaner import run_full_clean
    if not CLEANED_PARQUET.exists():
        run_full_clean()
    return load_cleaned()


def sidebar_filters(df):
    """侧边栏筛选控件：市场分组 + 批次，返回筛选后 DataFrame。"""
    st.sidebar.markdown("### 🚛 商用车公告数据 Agent")
    st.sidebar.markdown("---")

    st.sidebar.markdown("**📊 市场分组**")
    segment_names = list(ZF_MARKET_SEGMENTS.keys())
    selected_segment = st.sidebar.selectbox(
        "选择市场",
        segment_names,
        index=0,
        help="ZF CVS 核心业务覆盖客车、中重卡、牵引车、挂车、专用车。选择「全部车型」可查看所有数据（含摩托车/轿车/乘用车）。",
    )
    allowed_cats = ZF_MARKET_SEGMENTS[selected_segment]
    if allowed_cats is not None:
        filtered = df[df["vehicle_category"].isin(allowed_cats)]
    else:
        filtered = df

    if allowed_cats is not None:
        st.sidebar.caption(
            f"已过滤 {len(df) - len(filtered):,} 条非目标记录 "
            f"(摩托车 {(df['vehicle_category']=='摩托车').sum():,} / "
            f"轿车 {(df['vehicle_category']=='轿车').sum():,} / "
            f"乘用车 {(df['vehicle_category']=='乘用车').sum():,})"
        )

    st.sidebar.markdown("---")

    st.sidebar.markdown("**📅 批次选择**")
    batches = sorted(filtered["batch"].unique())
    if len(batches) == 0:
        st.sidebar.warning("当前筛选条件下无数据")
        return filtered

    min_b, max_b = int(min(batches)), int(max(batches))

    mode = st.sidebar.radio("批次模式", ["全部批次", "批次区间", "单批次"], horizontal=True)
    if mode == "批次区间":
        b_range = st.sidebar.slider("批次区间", min_b, max_b, (max_b - 11, max_b))
        filtered = filtered[filtered["batch"].between(b_range[0], b_range[1])]
    elif mode == "单批次":
        selected = st.sidebar.selectbox("选择批次", batches, index=len(batches) - 1)
        filtered = filtered[filtered["batch"] == selected]

    return filtered


sidebar_batch_filter = sidebar_filters

df_all = load_data()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**数据总量**: {len(df_all):,} 条记录")
st.sidebar.markdown(f"**批次范围**: {df_all['batch'].min()}-{df_all['batch'].max()}")

zf_core = ZF_MARKET_SEGMENTS["ZF 核心市场 (全部)"]
n_core = (df_all["vehicle_category"].isin(zf_core)).sum()
st.sidebar.markdown(f"**ZF 核心市场**: {n_core:,} 条 ({n_core/len(df_all):.1%})")

# ═══════════════════════════════════════════════════════════
# 主页内容
# ═══════════════════════════════════════════════════════════

st.markdown("# 中国商用车公告数据分析平台")

st.markdown("""
> **数据源**：中国工信部《道路机动车辆生产企业及产品公告》，采集自
> [商用车网 cn357.com](https://www.cn357.com)，覆盖第 290–388 批（约 2017-10 至 2025-12）。

本平台对 **82 万+** 车型公告数据进行结构化清洗与多维分析，提供市场趋势、
电动化深度洞察、制动系统竞争格局、变速箱覆盖、供应链分布等专题看板，
并支持自由字段探索和数据导出。请从左侧菜单选择分析页面。
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
