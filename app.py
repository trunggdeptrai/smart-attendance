import streamlit as st

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

initialize_database()
initialize_attendance_logs()

st.sidebar.title("SMART ATTENDANCE")
st.sidebar.caption("Hệ thống điểm danh học sinh thông minh")

pages = {
    "TỔNG QUAN": [
        st.Page("pages/1_Dashboard.py", title="Trang tổng quan", icon=":material/dashboard:"),
    ],
    "QUẢN LÝ NHÀ TRƯỜNG": [
        st.Page("pages/2_Employees.py", title="Quản lý học sinh", icon=":material/groups:"),
        st.Page("pages/8_Classes.py", title="Quản lý lớp học và giáo viên", icon=":material/class:"),
    ],
    "ĐIỂM DANH": [
        st.Page("pages/4_Attendance.py", title="Điểm danh nhận diện khuôn mặt", icon=":material/face:"),
        st.Page("pages/3_Register_Face.py", title="Đăng ký khuôn mặt học sinh", icon=":material/person_add:"),
        st.Page("pages/5_History.py", title="Lịch sử điểm danh", icon=":material/history:"),
        st.Page("pages/9_Attendance_Report.py", title="Báo cáo chuyên cần", icon=":material/analytics:"),
    ],
    "HỆ THỐNG": [
        st.Page("pages/10_Settings.py", title="Cài đặt", icon=":material/settings:"),
        st.Page("pages/11_Guide.py", title="Hướng dẫn sử dụng", icon=":material/help:"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
