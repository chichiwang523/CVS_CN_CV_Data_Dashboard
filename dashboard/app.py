"""
中国商用车公告数据分析 Agent — 主入口 (st.navigation 路由)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dashboard.auth import (
    check_auth,
    render_login_form,
    render_logout_button,
    is_current_user_admin,
)

st.set_page_config(
    page_title="中国商用车数据分析平台",
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

# ── 认证门控 ──────────────────────────────────────────
if not check_auth():
    render_login_form()
    st.stop()

# ── 已登录 → 构建导航 ────────────────────────────────
_DIR = Path(__file__).resolve().parent / "pages"

pages: dict[str, list] = {
    "首页": [
        st.Page(str(_DIR / "00_intro.py"), title="China CV Data App Intro", icon="🏠"),
    ],
    "公告数据": [
        st.Page(str(_DIR / "01_数据看板.py"), title="数据看板", icon="📊"),
        st.Page(str(_DIR / "02_市场趋势.py"), title="市场趋势", icon="📈"),
        st.Page(str(_DIR / "03_电动化分析.py"), title="电动化分析", icon="🔋"),
        st.Page(str(_DIR / "04_制动系统.py"), title="制动系统", icon="🛑"),
        st.Page(str(_DIR / "05_变速箱分析.py"), title="变速箱分析", icon="⚙️"),
        st.Page(str(_DIR / "06_竞争对手.py"), title="竞争对手", icon="🏭"),
        st.Page(str(_DIR / "07_供应链分析.py"), title="供应链分析", icon="🔗"),
        st.Page(str(_DIR / "08_数据查询.py"), title="数据查询", icon="📋"),
    ],
    "零售数据": [
        st.Page(str(_DIR / "09_上牌数据看板.py"), title="上牌/零售分析", icon="🚚"),
        st.Page(str(_DIR / "10_公告vs上牌分析.py"), title="公告 vs 上牌零售", icon="🔀"),
    ],
}

# 管理员额外看到用户管理页面
if is_current_user_admin():
    pages["管理"] = [
        st.Page(str(_DIR / "11_admin.py"), title="用户管理", icon="🔐"),
    ]

pg = st.navigation(pages)

render_logout_button()

pg.run()
