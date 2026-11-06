import sys
from pathlib import Path

import numpy as np
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)

from core.runtime_compat import runtime_compatibility_error

runtime_error = runtime_compatibility_error(sys.version_info, np.arange)
if runtime_error:
    st.error(runtime_error)
    st.stop()

from core.paths import ensure_runtime_directories
from db.attendance_repo import initialize_attendance_logs
from db.database import initialize_database
from ui.styles import apply_custom_css

st.set_page_config(
    page_title="SMART ATTENDANCE – HỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_custom_css()

from core.auth import require_login  # noqa: E402

require_login()

ensure_runtime_directories()
initialize_database()
initialize_attendance_logs()

st.sidebar.title("SMART ATTENDANCE")
st.sidebar.caption("Hệ thống điểm danh học sinh thông minh")

pages = {
    "TỔNG QUAN": [
        st.Page(PROJECT_ROOT / "pages" / "1_Dashboard.py", title="Trang tổng quan", icon=":material/dashboard:"),
    ],
    "QUẢN LÝ NHÀ TRƯỜNG": [
        st.Page(PROJECT_ROOT / "pages" / "2_Students.py", title="Quản lý học sinh", icon=":material/groups:"),
        st.Page(PROJECT_ROOT / "pages" / "8_Classes.py", title="Quản lý lớp học và giáo viên", icon=":material/class:"),
    ],
    "ĐIỂM DANH": [
        st.Page(PROJECT_ROOT / "pages" / "4_Attendance.py", title="Điểm danh tự động", icon=":material/face:"),
        st.Page(PROJECT_ROOT / "pages" / "13_Attendance_Manual.py", title="Điểm danh có xác nhận / thủ công", icon=":material/fact_check:"),
        st.Page(PROJECT_ROOT / "pages" / "3_Register_Face.py", title="Đăng ký khuôn mặt học sinh", icon=":material/person_add:"),
        st.Page(PROJECT_ROOT / "pages" / "5_History.py", title="Lịch sử điểm danh", icon=":material/history:"),
        st.Page(PROJECT_ROOT / "pages" / "9_Attendance_Report.py", title="Báo cáo chuyên cần", icon=":material/analytics:"),
    ],
    "NGHIÊN CỨU": [
        st.Page("pages/12_Research.py", title="Đánh giá thực nghiệm", icon=":material/science:"),
    ],
    "HỆ THỐNG": [
        st.Page(PROJECT_ROOT / "pages" / "10_Settings.py", title="Cài đặt", icon=":material/settings:"),
        st.Page(PROJECT_ROOT / "pages" / "11_Guide.py", title="Hướng dẫn sử dụng", icon=":material/help:"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
