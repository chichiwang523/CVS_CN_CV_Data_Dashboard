"""
Page 9: 上牌数据看板 — 2025 商用车零售（保险/上牌）月度数据分析
独立数据源，不依赖公告数据的 sidebar 筛选器。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

from src.config import ZF_COLORS, ZF_BLUE
from src.retail_demo_loader import load_retail_demo

# ── 常量 ──────────────────────────────────────────────

_SS_STACK = "retail_filter_stack"
_CHART_FONT = dict(family="Microsoft YaHei, SimHei, Arial", size=12)
_CHART_MARGIN = dict(l=10, r=10, t=50, b=10)

FIELD_LABELS = {
    "车辆类型": "车辆类型",
    "载货车分类（按功能用途）": "载货车功能用途",
    "fuel_map_hybrid_phev_other": "能源类型",
    "fuel_map_ng": "燃料种类",
    "底盘企业简称": "底盘企业",
    "马力分箱": "马力分箱",
}

HP_ORDER = ["<=80", "81-120", "121-160", "161-220", "221-300", ">300", "未知"]

# ── 页面配置 ──────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h1 { color: #003399; font-size: 1.8rem !important; }
    h3 { color: #003399; font-size: 1.1rem !important; margin-bottom: 0.3rem !important; }
    .stMetric label { font-size: 12px !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 24px !important; color: #003399; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🚚 上牌/零售分析")
st.caption("数据源：2025年1-12月商用车零售统计表（保险/上牌数据） | 点击图中扇区/柱子可逐层下钻 | 从 ZF Tier-1 视角聚焦终端销量")


# ── 数据加载 ──────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="加载零售数据中...")
def _load_retail():
    return load_retail_demo(force_rebuild=False)


# ── 过滤器栈 ──────────────────────────────────────────

def _push_filter(field: str, value: str):
    stack: list = st.session_state.get(_SS_STACK, [])
    stack.append({"field": field, "value": value})
    st.session_state[_SS_STACK] = stack


def _pop_filter():
    stack: list = st.session_state.get(_SS_STACK, [])
    if stack:
        stack.pop()
    st.session_state[_SS_STACK] = stack


def _clear_filters():
    st.session_state[_SS_STACK] = []


def _get_filters() -> list[dict]:
    return st.session_state.get(_SS_STACK, [])


def _apply_filter_stack(df: pd.DataFrame, stack: list[dict]) -> pd.DataFrame:
    for f in stack:
        col, val = f["field"], f["value"]
        if col in df.columns:
            df = df[df[col].astype(str) == str(val)]
    return df


# ── 工具函数 ──────────────────────────────────────────

def _weighted_count(df: pd.DataFrame, field: str) -> pd.DataFrame:
    work = df.copy()
    work[field] = work[field].fillna("").astype(str).str.strip()
    work = work[work[field] != ""]
    if len(work) == 0:
        return pd.DataFrame(columns=[field, "count"])
    out = work.groupby(field, as_index=False)["数量"].sum().rename(columns={"数量": "count"})
    return out.sort_values("count", ascending=False)


def _horsepower_bin(v):
    if pd.isna(v):
        return "未知"
    try:
        x = float(v)
    except Exception:
        return "未知"
    if x <= 80:
        return "<=80"
    if x <= 120:
        return "81-120"
    if x <= 160:
        return "121-160"
    if x <= 220:
        return "161-220"
    if x <= 300:
        return "221-300"
    return ">300"


# ── 图表构建 ──────────────────────────────────────────

def _make_pie(df_counts: pd.DataFrame, field: str, title: str, height: int = 420):
    if len(df_counts) == 0:
        return go.Figure()
    top = df_counts.head(10).copy()
    others = df_counts.iloc[10:]
    if len(others) > 0:
        other_row = pd.DataFrame([{field: "其他", "count": others["count"].sum()}])
        top = pd.concat([top, other_row], ignore_index=True)

    fig = px.pie(
        top, names=field, values="count",
        hole=0.4, color_discrete_sequence=ZF_COLORS,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="label+percent",
        textfont_size=11,
        insidetextorientation="horizontal",
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#003399")),
        font=_CHART_FONT,
        margin=_CHART_MARGIN,
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5,
            font=dict(size=10),
        ),
        showlegend=True,
    )
    return fig


def _make_barh(df_counts: pd.DataFrame, field: str, title: str,
               top_n: int = 20, height: int = 450):
    if len(df_counts) == 0:
        return go.Figure()
    show = df_counts.head(top_n).copy()
    show = show.sort_values("count", ascending=True)
    fig = px.bar(
        show, x="count", y=field, orientation="h",
        color_discrete_sequence=[ZF_BLUE], text="count",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=10)
    bar_height = max(height, len(show) * 28 + 100)
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#003399")),
        font=_CHART_FONT,
        margin=dict(l=10, r=60, t=50, b=10),
        height=bar_height,
        paper_bgcolor="white",
        plot_bgcolor="#FAFAFA",
        xaxis=dict(title="", showticklabels=False),
        yaxis=dict(title="", tickfont=dict(size=11), automargin=True),
        showlegend=False,
    )
    return fig


def _render_chart_with_click(fig, key: str, df_counts: pd.DataFrame, field: str):
    events = plotly_events(fig, click_event=True, select_event=False,
                           hover_event=False, key=key)
    if events:
        idx = events[0].get("pointNumber")
        if idx is not None and 0 <= idx < len(df_counts):
            clicked_value = str(df_counts.iloc[idx][field])
            _push_filter(field, clicked_value)
            st.rerun()


# ══════════════════════════════════════════════════════
# 侧栏筛选（独立于公告数据的 sidebar）
# ══════════════════════════════════════════════════════

df_all = _load_retail()

st.sidebar.markdown("### 🚚 上牌数据筛选器")
st.sidebar.markdown("---")

years = sorted(df_all["年"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect("年份", years, default=years, key="retail_year")
df_1 = df_all[df_all["年"].isin(selected_years)] if selected_years else df_all.iloc[0:0]

months = sorted(df_1["月"].dropna().unique().tolist())
selected_months = st.sidebar.multiselect("月份", months, default=months, key="retail_month")
df_2 = df_1[df_1["月"].isin(selected_months)] if selected_months else df_1.iloc[0:0]

vehicle_names = sorted(
    [x for x in df_2["车辆名称"].dropna().astype(str).str.strip().unique().tolist() if x]
)
selected_vehicle = st.sidebar.selectbox("车辆名称", ["全部"] + vehicle_names,
                                        index=0, key="retail_vname")
df_base = df_2 if selected_vehicle == "全部" else df_2[df_2["车辆名称"] == selected_vehicle]

# 应用过滤器栈
filters = _get_filters()
df_plot = _apply_filter_stack(df_base, filters)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**筛选后记录**: {len(df_base):,}")

if filters:
    st.sidebar.markdown("**图间联动层级:**")
    for i, f in enumerate(filters, 1):
        label = FIELD_LABELS.get(f["field"], f["field"])
        st.sidebar.markdown(f"  {i}. {label} = `{f['value']}`")

    bc1, bc2 = st.sidebar.columns(2)
    with bc1:
        if st.sidebar.button("⬅ 返回上一步", use_container_width=True, key="retail_back_side"):
            _pop_filter()
            st.rerun()
    with bc2:
        if st.sidebar.button("✕ 清空全部", use_container_width=True, key="retail_clear_side"):
            _clear_filters()
            st.rerun()

if len(df_plot) == 0:
    st.warning("当前筛选条件下无数据，请调整筛选或返回上一步。")
    st.stop()

# ══════════════════════════════════════════════════════
# 联动面包屑 + 返回按钮
# ══════════════════════════════════════════════════════

if filters:
    breadcrumb_parts = []
    for f in filters:
        label = FIELD_LABELS.get(f["field"], f["field"])
        breadcrumb_parts.append(f"**{label}**: {f['value']}")
    breadcrumb_text = " → ".join(breadcrumb_parts)

    bar_left, bar_right = st.columns([5, 1])
    with bar_left:
        st.markdown(f"🔗 下钻路径: {breadcrumb_text}  （共 {len(filters)} 层）")
    with bar_right:
        if st.button("⬅ 返回上一步", key="retail_back_main", use_container_width=True):
            _pop_filter()
            st.rerun()

# ══════════════════════════════════════════════════════
# KPI 概览
# ══════════════════════════════════════════════════════

total_qty = pd.to_numeric(df_plot["数量"], errors="coerce").fillna(0).sum()
n_types = df_plot["车辆类型"].nunique()
n_chassis = df_plot["底盘企业简称"].nunique()

k1, k2, k3, k4 = st.columns(4)
k1.metric("记录数", f"{len(df_plot):,}")
k2.metric("零售总量", f"{total_qty:,.0f}")
k3.metric("车辆类型", f"{n_types}")
k4.metric("底盘企业", f"{n_chassis}")

st.markdown("---")

# ══════════════════════════════════════════════════════
# 图表
# ══════════════════════════════════════════════════════

# 图 1 + 图 2
col1, col2 = st.columns(2)
with col1:
    vc1 = _weighted_count(df_plot, "车辆类型")
    fig1 = _make_pie(vc1, "车辆类型", "车辆类型分布")
    _render_chart_with_click(fig1, "r_pie_vtype", vc1, "车辆类型")

with col2:
    vc2 = _weighted_count(df_plot, "载货车分类（按功能用途）")
    fig2 = _make_pie(vc2, "载货车分类（按功能用途）", "载货车分类（按功能用途）")
    _render_chart_with_click(fig2, "r_pie_cargo", vc2, "载货车分类（按功能用途）")

st.markdown("---")

# 图 3 + 图 6
col3, col6 = st.columns(2)
with col3:
    vc3 = _weighted_count(df_plot, "fuel_map_hybrid_phev_other")
    fig3 = _make_pie(vc3, "fuel_map_hybrid_phev_other",
                     "能源类型 (Hybrid/PHEV/BEV/FCEV/Other)")
    _render_chart_with_click(fig3, "r_pie_fuel1", vc3, "fuel_map_hybrid_phev_other")

with col6:
    vc6 = _weighted_count(df_plot, "fuel_map_ng")
    fig6 = _make_pie(vc6, "fuel_map_ng", "燃料种类 (NG 合并后)")
    _render_chart_with_click(fig6, "r_pie_fuel2", vc6, "fuel_map_ng")

st.markdown("---")

# 图 4: 底盘企业简称
top_n_chassis = st.slider("底盘企业简称 显示数量", 10, 50, 20, key="r_sl_chassis")
vc4 = _weighted_count(df_plot, "底盘企业简称")
fig4 = _make_barh(vc4, "底盘企业简称",
                  f"底盘企业简称 Top {top_n_chassis}", top_n=top_n_chassis)
_render_chart_with_click(
    fig4, "r_bar_chassis",
    vc4.head(top_n_chassis).sort_values("count", ascending=True).reset_index(drop=True),
    "底盘企业简称",
)

st.markdown("---")

# 图 5: 马力分箱
hp_df = df_plot.copy()
hp_df["马力分箱"] = hp_df["马力_hp"].map(_horsepower_bin)
vc5 = _weighted_count(hp_df, "马力分箱")
vc5["sort_key"] = vc5["马力分箱"].map({v: i for i, v in enumerate(HP_ORDER)}).fillna(99)
vc5 = vc5.sort_values("sort_key").drop(columns="sort_key")
fig5 = _make_barh(vc5, "马力分箱", "马力 (hp) 分箱分布", top_n=len(vc5), height=350)
_render_chart_with_click(
    fig5, "r_bar_hp",
    vc5.sort_values("count", ascending=True).reset_index(drop=True),
    "马力分箱",
)
