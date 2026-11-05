"""Đăng nhập đơn giản cho ứng dụng (một tài khoản quản trị).

Mật khẩu KHÔNG lưu dạng chữ trong mã nguồn. Cấu hình đặt trong
``.streamlit/secrets.toml`` (đã .gitignore) hoặc mục Secrets của Streamlit Cloud:

    [auth]
    username = "admin"
    password_hash = "pbkdf2_sha256$200000$<salt_hex>$<hash_hex>"

Tạo chuỗi băm bằng: ``python scripts/set_password.py``.
"""

import hashlib
import hmac
import os
import time

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


def hash_password(password, salt=None, iterations=ITERATIONS):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"{ALGORITHM}${iterations}${salt}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$")
        if algorithm != ALGORITHM:
            return False
        candidate = hash_password(password, salt=salt, iterations=int(iterations))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(candidate.split("$")[-1], expected)


def check_credentials(username, password, config):
    """config: dict có 'username' và 'password_hash'."""
    if not config:
        return False
    user_ok = hmac.compare_digest((username or "").strip(), str(config.get("username", "")))
    pass_ok = verify_password(password or "", str(config.get("password_hash", "")))
    return user_ok and pass_ok


def load_auth_config():
    """Đọc cấu hình từ st.secrets['auth'], hoặc biến môi trường khi chạy ngoài Streamlit."""
    try:
        import streamlit as st

        section = st.secrets.get("auth")
        if section:
            return {"username": section.get("username"), "password_hash": section.get("password_hash")}
    except Exception:  # không có secrets.toml
        pass
    username = os.environ.get("SMART_ATTENDANCE_ADMIN_USER")
    password_hash = os.environ.get("SMART_ATTENDANCE_ADMIN_PASSWORD_HASH")
    if username and password_hash:
        return {"username": username, "password_hash": password_hash}
    return None


def _login_view():
    import streamlit as st

    config = load_auth_config()
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.title("SMART ATTENDANCE")
        st.caption("Hệ thống điểm danh học sinh thông minh – vui lòng đăng nhập")
        if config is None:
            st.error(
                "Chưa cấu hình tài khoản đăng nhập. Chạy `python scripts/set_password.py` "
                "(máy cục bộ) hoặc khai báo mục [auth] trong Secrets (Streamlit Cloud)."
            )
            return

        locked_until = st.session_state.get("auth_locked_until", 0)
        if time.time() < locked_until:
            st.error(f"Nhập sai quá {MAX_FAILED_ATTEMPTS} lần. Thử lại sau {int(locked_until - time.time())} giây.")
            return

        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")
        if submitted:
            if check_credentials(username, password, config):
                st.session_state["auth_user"] = username.strip()
                st.session_state["auth_failed"] = 0
                st.rerun()
            failed = st.session_state.get("auth_failed", 0) + 1
            st.session_state["auth_failed"] = failed
            if failed >= MAX_FAILED_ATTEMPTS:
                st.session_state["auth_locked_until"] = time.time() + LOCKOUT_SECONDS
                st.session_state["auth_failed"] = 0
            st.error("Sai tên đăng nhập hoặc mật khẩu.")


def require_login():
    """Chặn mọi trang khi chưa đăng nhập.

    Khi chưa đăng nhập, ứng dụng chỉ đăng ký DUY NHẤT trang đăng nhập với
    st.navigation (ẩn), nên mở thẳng đường dẫn trang khác (vd /Settings) cũng
    chỉ thấy form đăng nhập. Hàm dừng script sau khi hiển thị form.
    """
    import streamlit as st

    if st.session_state.get("auth_user"):
        with st.sidebar:
            st.caption(f"Đang đăng nhập: **{st.session_state['auth_user']}**")
            if st.button("Đăng xuất", icon=":material/logout:", width="stretch"):
                st.session_state.pop("auth_user", None)
                st.rerun()
        return

    st.navigation([st.Page(_login_view, title="Đăng nhập", icon=":material/lock:")], position="hidden").run()
    st.stop()
