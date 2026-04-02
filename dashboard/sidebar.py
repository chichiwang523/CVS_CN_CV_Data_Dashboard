"""
共享侧边栏筛选器 — 市场分组 + 批次区间
所有看板页面统一调用此模块。
使用 st.session_state 保持筛选状态，切换页面不重置。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.config import ZF_MARKET_SEGMENTS, NON_ZF_CATEGORIES

_SS_SEGMENT = "sidebar_segment"
_SS_MODE    = "sidebar_batch_mode"
_SS_RANGE   = "sidebar_batch_range"
_SS_SINGLE  = "sidebar_batch_single"


@st.cache_data(ttl=3600, show_spinner="加载数据中...")
def _load():
    from src.data_loader import load_cleaned, CLEANED_PARQUET
    from src.data_cleaner import run_full_clean
    from src.config import DASHBOARD_COLUMNS
    if not CLEANED_PARQUET.exists():
        run_full_clean()
    return load_cleaned(columns=DASHBOARD_COLUMNS)


def _init_state(min_b: int, max_b: int, default_batch_window: int):
    """首次运行时用默认值初始化 session_state，后续切换页面不覆盖。"""
    if _SS_SEGMENT not in st.session_state:
        st.session_state[_SS_SEGMENT] = list(ZF_MARKET_SEGMENTS.keys())[0]
    if _SS_MODE not in st.session_state:
        st.session_state[_SS_MODE] = "批次区间"
    if _SS_RANGE not in st.session_state:
        default_start = max(min_b, max_b - default_batch_window + 1)
        st.session_state[_SS_RANGE] = (default_start, max_b)
    if _SS_SINGLE not in st.session_state:
        st.session_state[_SS_SINGLE] = max_b


def apply_sidebar_filters(default_batch_window: int = 24):
    """
    在侧边栏渲染市场分组选择器 + 批次选择器，返回筛选后的 DataFrame。
    筛选状态通过 session_state 跨页面保持，切换页面不重置。
    """
    df = _load()

    st.sidebar.markdown("### 🚛 商用车公告数据 Agent")
    st.sidebar.markdown("---")

    all_batches = sorted(df["batch"].unique())
    global_min_b = int(min(all_batches))
    global_max_b = int(max(all_batches))

    # 首次进入时初始化默认值
    _init_state(global_min_b, global_max_b, default_batch_window)

    # ── 市场分组 ──
    st.sidebar.markdown("**📊 市场分组**")
    segment_names = list(ZF_MARKET_SEGMENTS.keys())
    selected_segment = st.sidebar.selectbox(
        "选择市场",
        segment_names,
        index=segment_names.index(st.session_state[_SS_SEGMENT])
              if st.session_state[_SS_SEGMENT] in segment_names else 0,
        key=_SS_SEGMENT,
        help=(
            "ZF CVS 核心业务覆盖客车、中重卡、牵引车、挂车、专用车。"
            "选择「全部车型」可查看所有数据（含摩托车/轿车/乘用车等）。"
        ),
    )
    allowed_cats = ZF_MARKET_SEGMENTS[selected_segment]
    if allowed_cats is not None:
        filtered = df[df["vehicle_category"].isin(allowed_cats)].copy()
        n_excluded = len(df) - len(filtered)
        st.sidebar.caption(f"已过滤 {n_excluded:,} 条非目标记录")
    else:
        filtered = df.copy()

    st.sidebar.markdown("---")

    # ── 批次选择 ──
    st.sidebar.markdown("**📅 批次选择**")
    batches = sorted(filtered["batch"].unique())
    if len(batches) == 0:
        st.sidebar.warning("当前筛选条件下无数据")
        return filtered

    min_b, max_b = int(min(batches)), int(max(batches))

    # 修正 session_state 中的范围以防超出当前可用批次
    saved_range = st.session_state[_SS_RANGE]
    clipped_range = (
        max(min_b, min(saved_range[0], max_b)),
        max(min_b, min(saved_range[1], max_b)),
    )
    if clipped_range[0] > clipped_range[1]:
        clipped_range = (min_b, max_b)
    st.session_state[_SS_RANGE] = clipped_range

    saved_single = st.session_state[_SS_SINGLE]
    if saved_single not in batches:
        st.session_state[_SS_SINGLE] = max_b

    mode = st.sidebar.radio(
        "批次模式", ["全部批次", "批次区间", "单批次"],
        horizontal=True,
        key=_SS_MODE,
    )

    if mode == "批次区间":
        b_range = st.sidebar.slider(
            "批次区间", min_b, max_b,
            value=st.session_state[_SS_RANGE],
            key=_SS_RANGE,
        )
        filtered = filtered[filtered["batch"].between(b_range[0], b_range[1])]
    elif mode == "单批次":
        single_idx = batches.index(st.session_state[_SS_SINGLE]) if st.session_state[_SS_SINGLE] in batches else len(batches) - 1
        selected = st.sidebar.selectbox(
            "选择批次", batches, index=single_idx, key=_SS_SINGLE,
        )
        filtered = filtered[filtered["batch"] == selected]

    st.sidebar.markdown("---")
    st.sidebar.caption(f"当前: {len(filtered):,} 条 | {selected_segment}")

    return filtered


def get_full_zf_data():
    """返回 ZF 核心市场全量数据（不经批次筛选），用于趋势类计算。"""
    df = _load()
    zf_cats = ZF_MARKET_SEGMENTS["ZF 核心市场 (全部)"]
    return df[df["vehicle_category"].isin(zf_cats)].copy()
