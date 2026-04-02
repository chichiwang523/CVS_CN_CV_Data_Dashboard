"""
认证模块 — 邮箱登录 + 管理员审批
- @zf.com 域名限制
- JSON 文件存储用户状态
- 阿里云 DirectMail SMTP 通知管理员（可选降级）
"""
from __future__ import annotations

import fcntl
import json
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import streamlit as st

from src.config import (
    AUTH_DOMAIN,
    ADMIN_EMAILS,
    USERS_JSON,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_FROM,
)

logger = logging.getLogger(__name__)

_SS_EMAIL = "auth_email"


# ── 用户存储 ─────────────────────────────────────────

class UserStore:
    """简单的 JSON 文件用户库，带文件锁防并发写入。"""

    def __init__(self, path: Path = USERS_JSON):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"admin_emails": ADMIN_EMAILS, "users": {}})

    # ── 读写 ──

    def _read(self) -> dict:
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(self._path, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, ensure_ascii=False, indent=2)
            fcntl.flock(f, fcntl.LOCK_UN)

    # ── 查询 ──

    def get_user(self, email: str) -> Optional[dict]:
        data = self._read()
        return data.get("users", {}).get(email)

    def is_approved(self, email: str) -> bool:
        u = self.get_user(email)
        return u is not None and u.get("status") == "approved"

    def is_pending(self, email: str) -> bool:
        u = self.get_user(email)
        return u is not None and u.get("status") == "pending"

    def is_rejected(self, email: str) -> bool:
        u = self.get_user(email)
        return u is not None and u.get("status") == "rejected"

    def is_admin(self, email: str) -> bool:
        data = self._read()
        return email in data.get("admin_emails", [])

    def list_by_status(self, status: str) -> dict[str, dict]:
        data = self._read()
        return {
            e: u for e, u in data.get("users", {}).items()
            if u.get("status") == status
        }

    def list_all(self) -> dict[str, dict]:
        return self._read().get("users", {})

    # ── 写入 ──

    def add_pending(self, email: str):
        data = self._read()
        data.setdefault("users", {})[email] = {
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": None,
            "role": "user",
        }
        self._write(data)

    def approve(self, email: str, approver: str):
        data = self._read()
        if email in data.get("users", {}):
            data["users"][email]["status"] = "approved"
            data["users"][email]["approved_by"] = approver
            self._write(data)

    def reject(self, email: str, approver: str):
        data = self._read()
        if email in data.get("users", {}):
            data["users"][email]["status"] = "rejected"
            data["users"][email]["approved_by"] = approver
            self._write(data)

    def revoke(self, email: str, approver: str):
        """撤销已批准用户的权限（设为 rejected）。"""
        self.reject(email, approver)

    def add_approved(self, email: str, approver: str):
        """管理员直接添加已批准用户。"""
        data = self._read()
        data.setdefault("users", {})[email] = {
            "status": "approved",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": approver,
            "role": "user",
        }
        self._write(data)


# ── 邮件通知 ─────────────────────────────────────────

def _send_email(to: str, subject: str, body: str) -> bool:
    """通过阿里云 DirectMail SMTP 发送邮件，失败时仅记日志不阻塞。"""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM]):
        logger.warning("SMTP 未配置，跳过邮件通知")
        return False
    try:
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=10) as srv:
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_FROM, [to], msg.as_string())
        logger.info(f"邮件已发送至 {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False


def notify_admin_new_request(applicant_email: str):
    """向所有管理员发送新用户申请通知。"""
    subject = f"[CV Data Platform] 新用户申请 — {applicant_email}"
    body = f"""
    <h3>新用户访问申请</h3>
    <p><strong>申请邮箱：</strong>{applicant_email}</p>
    <p><strong>申请时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <hr>
    <p>请登录 <a href="http://139.224.204.17">CV Data Platform 管理面板</a> 进行审批。</p>
    """
    for admin in ADMIN_EMAILS:
        _send_email(admin, subject, body)


# ── 登录 UI ──────────────────────────────────────────

def render_login_form():
    """渲染登录页面。返回后调用 st.stop() 阻止后续内容。"""
    store = UserStore()

    # 居中布局
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown(
            """
            <div style="text-align:center; margin-top:8vh;">
                <h1 style="color:#003399; font-size:2.5rem;">🚛 China CV Data Platform</h1>
                <p style="color:#666; font-size:1.1rem;">中国商用车公告数据分析平台 · ZF Internal</p>
                <hr style="margin:2rem 0;">
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "ZF 邮箱",
                placeholder="your.name@zf.com",
                help="仅限 @zf.com 后缀的邮箱",
            ).strip().lower()
            submitted = st.form_submit_button("登 录", use_container_width=True, type="primary")

        if submitted and email:
            # 1️⃣ 域名校验
            if not email.endswith(f"@{AUTH_DOMAIN}"):
                st.error(f"❌ 仅限 @{AUTH_DOMAIN} 邮箱登录")
                return

            # 2️⃣ 已批准 → 直接进入
            if store.is_approved(email):
                st.session_state[_SS_EMAIL] = email
                st.rerun()

            # 3️⃣ 待审批
            elif store.is_pending(email):
                st.warning("⏳ 您的申请正在等待管理员审批，请稍后再试。")
                st.info(f"管理员: {', '.join(ADMIN_EMAILS)}")
                return

            # 4️⃣ 已拒绝
            elif store.is_rejected(email):
                st.error("🚫 您的访问申请已被拒绝。如有疑问请联系管理员。")
                st.info(f"管理员: {', '.join(ADMIN_EMAILS)}")
                return

            # 5️⃣ 新用户 → 创建 pending + 通知管理员
            else:
                store.add_pending(email)
                notify_admin_new_request(email)
                st.warning("⏳ 访问申请已提交！请等待管理员审批。")
                st.info(f"管理员 {', '.join(ADMIN_EMAILS)} 将在收到通知后尽快处理。")
                return

        elif submitted and not email:
            st.warning("请输入邮箱地址")


def render_logout_button():
    """在侧边栏底部渲染当前用户信息和登出按钮。"""
    email = st.session_state.get(_SS_EMAIL, "")
    if email:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"👤 **{email}**")
        if st.sidebar.button("退出登录", use_container_width=True):
            del st.session_state[_SS_EMAIL]
            st.rerun()


def check_auth() -> bool:
    """检查是否已登录。返回 True 表示已认证。"""
    return _SS_EMAIL in st.session_state and st.session_state[_SS_EMAIL]


def get_current_user() -> str:
    """获取当前登录用户邮箱。"""
    return st.session_state.get(_SS_EMAIL, "")


def is_current_user_admin() -> bool:
    """当前登录用户是否是管理员。"""
    email = get_current_user()
    if not email:
        return False
    return UserStore().is_admin(email)
