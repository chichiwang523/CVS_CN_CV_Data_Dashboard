"""用户管理 — 管理员审批面板"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from dashboard.auth import UserStore, get_current_user, is_current_user_admin

# ── 权限检查 ──

if not is_current_user_admin():
    st.error("🚫 仅管理员可访问此页面")
    st.stop()

admin_email = get_current_user()
store = UserStore()

st.markdown("# 🔐 用户管理")
st.caption(f"当前管理员: {admin_email}")

tab_pending, tab_approved, tab_rejected, tab_add = st.tabs(
    ["⏳ 待审批", "✅ 已批准", "❌ 已拒绝", "➕ 添加用户"]
)

# ── Tab 1: 待审批 ──

with tab_pending:
    pending = store.list_by_status("pending")
    if not pending:
        st.success("没有待审批的用户 🎉")
    else:
        st.warning(f"有 {len(pending)} 个待审批用户")
        for email, info in sorted(pending.items()):
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{email}**")
                c1.caption(f"申请时间: {info.get('requested_at', 'N/A')[:19]}")
                if c2.button("✅ 批准", key=f"approve_{email}", use_container_width=True):
                    store.approve(email, admin_email)
                    st.toast(f"已批准 {email}", icon="✅")
                    st.rerun()
                if c3.button("❌ 拒绝", key=f"reject_{email}", use_container_width=True):
                    store.reject(email, admin_email)
                    st.toast(f"已拒绝 {email}", icon="❌")
                    st.rerun()

# ── Tab 2: 已批准 ──

with tab_approved:
    approved = store.list_by_status("approved")
    if not approved:
        st.info("暂无已批准用户")
    else:
        st.success(f"共 {len(approved)} 个已批准用户")
        for email, info in sorted(approved.items()):
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                role_badge = "🔑 管理员" if store.is_admin(email) else "👤 用户"
                c1.markdown(f"**{email}** &nbsp; {role_badge}")
                c1.caption(
                    f"审批人: {info.get('approved_by', 'N/A')} · "
                    f"时间: {info.get('requested_at', 'N/A')[:19]}"
                )
                # 不允许撤销管理员自己的权限
                if email != admin_email:
                    if c2.button("撤销", key=f"revoke_{email}", use_container_width=True):
                        store.revoke(email, admin_email)
                        st.toast(f"已撤销 {email} 的访问权限", icon="⚠️")
                        st.rerun()

# ── Tab 3: 已拒绝 ──

with tab_rejected:
    rejected = store.list_by_status("rejected")
    if not rejected:
        st.info("暂无被拒绝用户")
    else:
        for email, info in sorted(rejected.items()):
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{email}**")
                c1.caption(f"操作人: {info.get('approved_by', 'N/A')}")
                if c2.button("重新批准", key=f"reapprove_{email}", use_container_width=True):
                    store.approve(email, admin_email)
                    st.toast(f"已重新批准 {email}", icon="✅")
                    st.rerun()

# ── Tab 4: 添加用户 ──

with tab_add:
    st.markdown("直接添加已批准的 @zf.com 用户（无需申请流程）")
    with st.form("add_user_form"):
        new_email = st.text_input(
            "邮箱地址",
            placeholder="colleague@zf.com",
        ).strip().lower()
        add_submitted = st.form_submit_button("添加并批准", use_container_width=True, type="primary")

    if add_submitted and new_email:
        if not new_email.endswith("@zf.com"):
            st.error("❌ 仅限 @zf.com 邮箱")
        elif store.is_approved(new_email):
            st.info(f"ℹ️ {new_email} 已是已批准用户")
        else:
            store.add_approved(new_email, admin_email)
            st.success(f"✅ 已添加并批准 {new_email}")
            st.rerun()
