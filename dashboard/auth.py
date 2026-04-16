"""
认证模块 — 邮箱/手机号 + 密码登录，管理员审批 + 用户自设密码
- @zf.com 域名限制（管理员豁免）
- 管理员可通过手机号别名登录
- SHA-256 + 随机 salt 密码存储
- JSON 文件存储用户状态
- JSONL 登录审计日志
- 阿里云 DirectMail SMTP 通知管理员（可选降级）
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from src.config import (
    AUTH_DOMAIN,
    ADMIN_EMAILS,
    ADMIN_PHONE_MAP,
    USERS_JSON,
    LOGIN_LOG,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_FROM,
)

logger = logging.getLogger(__name__)

_SS_EMAIL = "auth_email"


# ── 密码工具 ──────────────────────────────────────────

def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """返回 (hex_hash, hex_salt)。若不传 salt 则随机生成。"""
    if salt is None:
        salt_bytes = os.urandom(16)
    else:
        salt_bytes = bytes.fromhex(salt)
    h = hashlib.sha256(salt_bytes + password.encode("utf-8")).hexdigest()
    return h, salt_bytes.hex()


def _verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    h, _ = _hash_password(password, stored_salt)
    return h == stored_hash


# ── 用户存储 ─────────────────────────────────────────

class UserStore:
    """JSON 文件用户库，带文件锁防并发写入。"""

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
        """已批准（含已设密码 active 和待设密码 approved）。"""
        u = self.get_user(email)
        return u is not None and u.get("status") in ("approved", "active")

    def is_active(self, email: str) -> bool:
        """已设密码，可正常登录。"""
        u = self.get_user(email)
        return u is not None and u.get("status") == "active"

    def needs_password_setup(self, email: str) -> bool:
        """已批准但尚未设置密码。"""
        u = self.get_user(email)
        return u is not None and u.get("status") == "approved" and u.get("password_hash") is None

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

    def list_approved_and_active(self) -> dict[str, dict]:
        """列出所有已批准（含 active）的用户。"""
        data = self._read()
        return {
            e: u for e, u in data.get("users", {}).items()
            if u.get("status") in ("approved", "active")
        }

    def list_all(self) -> dict[str, dict]:
        return self._read().get("users", {})

    # ── 密码 ──

    def verify_password(self, email: str, password: str) -> bool:
        u = self.get_user(email)
        if not u or not u.get("password_hash") or not u.get("salt"):
            return False
        return _verify_password(password, u["password_hash"], u["salt"])

    def set_password(self, email: str, password: str):
        """设置密码并将状态改为 active。"""
        data = self._read()
        if email not in data.get("users", {}):
            return
        h, s = _hash_password(password)
        data["users"][email]["password_hash"] = h
        data["users"][email]["salt"] = s
        data["users"][email]["status"] = "active"
        self._write(data)

    def reset_password(self, email: str):
        """管理员重置用户密码 → 状态回到 approved，用户下次需重设。"""
        data = self._read()
        if email not in data.get("users", {}):
            return
        data["users"][email]["password_hash"] = None
        data["users"][email]["salt"] = None
        data["users"][email]["status"] = "approved"
        self._write(data)

    # ── 写入 ──

    def add_pending(self, email: str):
        data = self._read()
        data.setdefault("users", {})[email] = {
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": None,
            "role": "user",
            "password_hash": None,
            "salt": None,
        }
        self._write(data)

    def approve(self, email: str, approver: str):
        data = self._read()
        if email in data.get("users", {}):
            data["users"][email]["status"] = "approved"
            data["users"][email]["approved_by"] = approver
            # 清除密码，要求用户重新设置
            data["users"][email]["password_hash"] = None
            data["users"][email]["salt"] = None
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
        """管理员直接添加已批准用户（待设密码）。"""
        data = self._read()
        data.setdefault("users", {})[email] = {
            "status": "approved",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": approver,
            "role": "user",
            "password_hash": None,
            "salt": None,
        }
        self._write(data)


# ── 登录审计日志 ──────────────────────────────────────

def _log_login(email: str, action: str = "login"):
    """追加写入 login_log.jsonl。"""
    try:
        ip = "unknown"
        try:
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For", headers.get("X-Real-Ip", "unknown"))
        except Exception:
            pass
        record = {
            "email": email,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": ip,
        }
        LOGIN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOGIN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"写入登录日志失败: {e}")


def get_login_log() -> pd.DataFrame:
    """读取登录审计日志，返回 DataFrame。"""
    if not LOGIN_LOG.exists():
        return pd.DataFrame(columns=["email", "action", "timestamp", "ip"])
    records = []
    with open(LOGIN_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not records:
        return pd.DataFrame(columns=["email", "action", "timestamp", "ip"])
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp", ascending=False).reset_index(drop=True)


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


# ── 输入解析 ─────────────────────────────────────────

def _resolve_input(raw: str) -> str | None:
    """将用户输入解析为邮箱。纯数字视为手机号查找映射。返回 None 表示无效。"""
    raw = raw.strip().lower()
    if not raw:
        return None
    # 纯数字 → 手机号映射
    if raw.isdigit():
        mapped = ADMIN_PHONE_MAP.get(raw)
        if mapped:
            return mapped
        return None  # 未注册的手机号
    # 含 @ → 邮箱
    if "@" in raw:
        return raw
    return None


def _is_email_allowed(email: str) -> bool:
    """检查邮箱是否允许登录/注册。管理员豁免域名限制。"""
    if email in ADMIN_EMAILS:
        return True
    return email.endswith(f"@{AUTH_DOMAIN}")


# ── 登录 UI ──────────────────────────────────────────

def render_login_form():
    """渲染登录/注册/设密码页面。返回后调用 st.stop() 阻止后续内容。"""
    store = UserStore()

    # 居中布局
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown(
            """
            <div style="text-align:center; margin-top:6vh;">
                <h1 style="color:#003399; font-size:2.5rem;">🚛 China CV Data Platform</h1>
                <p style="color:#666; font-size:1.1rem;">中国商用车公告数据分析平台 · ZF Internal</p>
                <hr style="margin:2rem 0;">
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register, tab_setpw = st.tabs(["🔑 登录", "📝 注册", "🔐 设置密码"])

        # ── Tab 1: 登录 ──
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                account = st.text_input(
                    "邮箱 / 手机号",
                    placeholder="your.name@zf.com 或管理员手机号",
                ).strip()
                password = st.text_input(
                    "密码",
                    type="password",
                    placeholder="请输入密码",
                )
                submitted = st.form_submit_button("登 录", use_container_width=True, type="primary")

            if submitted:
                email = _resolve_input(account)
                if email is None:
                    if account.strip().isdigit():
                        st.error("❌ 该手机号未注册为管理员")
                    else:
                        st.error("❌ 请输入有效的邮箱或管理员手机号")
                    _log_login(account, "failed")
                    return

                if not _is_email_allowed(email):
                    st.error(f"❌ 仅限 @{AUTH_DOMAIN} 邮箱登录")
                    _log_login(email, "failed")
                    return

                if not store.is_approved(email):
                    if store.is_pending(email):
                        st.warning("⏳ 您的申请正在等待管理员审批，请稍后再试。")
                    elif store.is_rejected(email):
                        st.error("🚫 您的访问申请已被拒绝。如有疑问请联系管理员。")
                    else:
                        st.error('❌ 用户未注册，请先点击「注册」选项卡提交申请。')
                    return

                # 检查是否需要设密码
                if store.needs_password_setup(email):
                    st.warning('⚠️ 您的账号已获批准，但尚未设置密码。请点击「设置密码」选项卡完成设置。')
                    return

                # 验证密码
                if not store.verify_password(email, password):
                    st.error("❌ 密码错误")
                    _log_login(email, "failed")
                    return

                # ✅ 登录成功
                st.session_state[_SS_EMAIL] = email
                _log_login(email, "login")
                st.rerun()

        # ── Tab 2: 注册 ──
        with tab_register:
            st.markdown("提交 @zf.com 邮箱申请，等待管理员审批后即可使用。")
            with st.form("register_form", clear_on_submit=True):
                reg_email = st.text_input(
                    "ZF 邮箱",
                    placeholder="your.name@zf.com",
                    help=f"仅限 @{AUTH_DOMAIN} 后缀",
                ).strip().lower()
                reg_submitted = st.form_submit_button("提交申请", use_container_width=True, type="primary")

            if reg_submitted and reg_email:
                if not reg_email.endswith(f"@{AUTH_DOMAIN}"):
                    st.error(f"❌ 仅限 @{AUTH_DOMAIN} 邮箱注册")
                elif store.is_approved(reg_email):
                    st.info('ℹ️ 该邮箱已获批准，请直接登录（如未设密码请点击「设置密码」）。')
                elif store.is_pending(reg_email):
                    st.warning("⏳ 您的申请已提交，正在等待管理员审批。")
                elif store.is_rejected(reg_email):
                    st.error("🚫 该邮箱申请已被拒绝，请联系管理员。")
                else:
                    store.add_pending(reg_email)
                    _log_login(reg_email, "register")
                    notify_admin_new_request(reg_email)
                    st.success("✅ 申请已提交！请等待管理员审批。")
                    st.info('管理员审批后，请返回「设置密码」选项卡完成密码设置。')
            elif reg_submitted:
                st.warning("请输入邮箱地址")

        # ── Tab 3: 设置密码 ──
        with tab_setpw:
            st.markdown("管理员审批后，首次登录前需设置密码。")
            with st.form("setpw_form", clear_on_submit=False):
                pw_email = st.text_input(
                    "邮箱",
                    placeholder="your.name@zf.com",
                ).strip().lower()
                pw_new = st.text_input("设置密码", type="password", placeholder="至少 6 位")
                pw_confirm = st.text_input("确认密码", type="password", placeholder="再次输入")
                pw_submitted = st.form_submit_button("确认设置", use_container_width=True, type="primary")

            if pw_submitted and pw_email:
                if not store.needs_password_setup(pw_email):
                    if store.is_pending(pw_email):
                        st.warning("⏳ 您的申请尚未审批，请耐心等待。")
                    elif store.is_active(pw_email):
                        st.info("ℹ️ 密码已设置，请直接登录。如需重置请联系管理员。")
                    elif store.is_rejected(pw_email):
                        st.error("🚫 该邮箱申请已被拒绝。")
                    else:
                        st.error("❌ 该邮箱未注册或未获批准。")
                    return

                if len(pw_new) < 6:
                    st.error("❌ 密码至少 6 位")
                elif pw_new != pw_confirm:
                    st.error("❌ 两次密码不一致")
                else:
                    store.set_password(pw_email, pw_new)
                    _log_login(pw_email, "set_password")
                    st.success('✅ 密码设置成功！请返回「登录」选项卡登录。')
            elif pw_submitted:
                st.warning("请输入邮箱地址")


def render_logout_button():
    """在侧边栏底部渲染当前用户信息和登出按钮。"""
    email = st.session_state.get(_SS_EMAIL, "")
    if email:
        store = UserStore()
        role = "🔑 管理员" if store.is_admin(email) else "👤 用户"
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"{role} **{email}**")
        if st.sidebar.button("退出登录", use_container_width=True):
            _log_login(email, "logout")
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
