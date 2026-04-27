"""用户管理 — 管理员审批面板 + 登录记录 + 密码管理"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from dashboard.auth import (
    UserStore,
    get_current_user,
    get_login_log,
    is_current_user_admin,
    notify_user_added,
    notify_user_approved,
    notify_user_password_reset,
    notify_user_rejected,
)

# ── 权限检查 ──

if not is_current_user_admin():
    st.error("🚫 仅管理员可访问此页面")
    st.stop()

admin_email = get_current_user()
store = UserStore()

st.markdown("# 🔐 用户管理")
st.caption(f"当前管理员: {admin_email}")

tab_pending, tab_approved, tab_rejected, tab_add, tab_log, tab_changepw, tab_resetpw = st.tabs(
    ["⏳ 待审批", "✅ 已批准", "❌ 已拒绝", "➕ 添加用户", "📋 登录记录", "🔑 修改密码", "🔄 重置密码"]
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
                    notified = notify_user_approved(email, admin_email)
                    st.toast(f"已批准 {email}" + ("，已邮件通知" if notified else "，邮件未发送"), icon="✅")
                    st.rerun()
                if c3.button("❌ 拒绝", key=f"reject_{email}", use_container_width=True):
                    store.reject(email, admin_email)
                    notified = notify_user_rejected(email, admin_email)
                    st.toast(f"已拒绝 {email}" + ("，已邮件通知" if notified else "，邮件未发送"), icon="❌")
                    st.rerun()

# ── Tab 2: 已批准 ──

with tab_approved:
    approved = store.list_approved_and_active()
    if not approved:
        st.info("暂无已批准用户")
    else:
        st.success(f"共 {len(approved)} 个已批准用户")
        for email, info in sorted(approved.items()):
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                role_badge = "🔑 管理员" if store.is_admin(email) else "👤 用户"
                status = info.get("status", "approved")
                pw_badge = "✅ 已设密码" if status == "active" else "⚠️ 待设密码"
                c1.markdown(f"**{email}** &nbsp; {role_badge} &nbsp; {pw_badge}")
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
                    notified = notify_user_approved(email, admin_email)
                    st.toast(f"已重新批准 {email}" + ("，已邮件通知" if notified else "，邮件未发送"), icon="✅")
                    st.rerun()

# ── Tab 4: 添加用户 ──

with tab_add:
    st.markdown("直接添加已批准的 @zf.com 用户（无需申请流程，用户首次登录需自行设置密码）")
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
            notified = notify_user_added(new_email, admin_email)
            if notified:
                st.success(f"✅ 已添加并批准 {new_email}，已邮件通知用户设置密码")
            else:
                st.warning(f"✅ 已添加并批准 {new_email}，但邮件未发送；请手动通知用户设置密码")
            st.rerun()

# ── Tab 5: 登录记录 ──

with tab_log:
    st.markdown("### 📋 登录审计日志")
    log_df = get_login_log()
    if log_df.empty:
        st.info("暂无登录记录")
    else:
        # 筛选控件
        col_user, col_action, col_date = st.columns(3)
        with col_user:
            users = ["全部"] + sorted(log_df["email"].unique().tolist())
            sel_user = st.selectbox("用户", users, key="log_user_filter")
        with col_action:
            actions = ["全部"] + sorted(log_df["action"].unique().tolist())
            sel_action = st.selectbox("操作类型", actions, key="log_action_filter")
        with col_date:
            date_range = st.date_input(
                "日期范围",
                value=[log_df["timestamp"].min().date(), log_df["timestamp"].max().date()],
                key="log_date_filter",
            )

        filtered = log_df.copy()
        if sel_user != "全部":
            filtered = filtered[filtered["email"] == sel_user]
        if sel_action != "全部":
            filtered = filtered[filtered["action"] == sel_action]
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            import pandas as pd
            start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
            filtered = filtered[
                (filtered["timestamp"] >= start) & (filtered["timestamp"] < end)
            ]

        st.caption(f"共 {len(filtered)} 条记录")

        # 显示表格
        display_df = filtered.copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        action_labels = {
            "login": "✅ 登录",
            "failed": "❌ 失败",
            "register": "📝 注册",
            "set_password": "🔐 设密码",
            "logout": "🚪 登出",
        }
        display_df["action"] = display_df["action"].map(lambda x: action_labels.get(x, x))
        display_df.columns = ["用户", "操作", "时间", "IP"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 下载按钮
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 下载 CSV", csv, "login_log.csv", "text/csv", use_container_width=True)

# ── Tab 6: 修改密码（管理员修改自己的密码）──

with tab_changepw:
    st.markdown("### 🔑 修改管理员密码")
    with st.form("change_pw_form"):
        old_pw = st.text_input("当前密码", type="password")
        new_pw = st.text_input("新密码", type="password", placeholder="至少 6 位")
        confirm_pw = st.text_input("确认新密码", type="password")
        change_submitted = st.form_submit_button("确认修改", use_container_width=True, type="primary")

    if change_submitted:
        if not store.verify_password(admin_email, old_pw):
            st.error("❌ 当前密码错误")
        elif len(new_pw) < 6:
            st.error("❌ 新密码至少 6 位")
        elif new_pw != confirm_pw:
            st.error("❌ 两次密码不一致")
        else:
            store.set_password(admin_email, new_pw)
            st.success("✅ 密码已修改")

# ── Tab 7: 重置用户密码 ──

with tab_resetpw:
    st.markdown("### 🔄 重置用户密码")
    st.caption('重置后用户状态回到「待设密码」，下次登录时须重新设置密码。')

    active_users = {
        e: u for e, u in store.list_approved_and_active().items()
        if e != admin_email  # 不允许在这里重置自己
    }
    if not active_users:
        st.info("暂无可重置的用户")
    else:
        for email, info in sorted(active_users.items()):
            status = info.get("status", "")
            if status == "active":
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**{email}**")
                    c1.caption(f"当前状态: 已设密码")
                    if c2.button("重置密码", key=f"reset_{email}", use_container_width=True):
                        store.reset_password(email)
                        notified = notify_user_password_reset(email, admin_email)
                        st.toast(f"已重置 {email} 的密码" + ("，已邮件通知" if notified else "，邮件未发送"), icon="🔄")
                        st.rerun()
