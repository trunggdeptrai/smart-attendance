import streamlit as st

st.title("Hướng dẫn sử dụng")
st.caption("Quy trình thao tác đề xuất cho giáo viên và quản trị viên.")

with st.container(border=True):
    st.subheader("1. Khởi tạo danh mục")
    st.markdown(
        "Mở **Quản lý lớp học và giáo viên** để tạo lớp, thêm hồ sơ giáo viên "
        "và phân công giáo viên chủ nhiệm. Sau đó thêm học sinh tại **Quản lý học sinh**."
    )

with st.container(border=True):
    st.subheader("2. Đăng ký khuôn mặt")
    st.markdown(
        "Chọn học sinh, chụp hoặc tải ảnh rõ nét, mỗi ảnh chỉ có một khuôn mặt. "
        "Đăng ký nhiều ảnh trong điều kiện ánh sáng khác nhau và huấn luyện lại mô hình."
    )

with st.container(border=True):
    st.subheader("3. Điểm danh và xác nhận")
    st.markdown(
        "Chọn lớp, ngày và buổi học; chụp ảnh bằng camera hoặc tải ảnh lên. "
        "Kiểm tra mã, họ tên, lớp và khoảng cách nhận diện. Giáo viên cần xác nhận "
        "từng kết quả; có thể ghi nhận thủ công hoặc đánh dấu vắng mặt."
    )
    st.warning(
        "Không nhận diện được không có nghĩa là vắng mặt. Trạng thái vắng chỉ được "
        "lưu khi giáo viên chọn và xác nhận."
    )

with st.container(border=True):
    st.subheader("4. Tra cứu báo cáo")
    st.markdown(
        "Dùng **Lịch sử điểm danh** để lọc và xuất CSV/Excel; dùng **Báo cáo chuyên cần** "
        "để xem sĩ số, các trạng thái đã xác nhận và học sinh chưa ghi nhận."
    )

st.subheader("Khắc phục sự cố")
st.markdown(
    """
    - Nếu camera không hiển thị: kiểm tra quyền camera của trình duyệt và chọn HTTPS hoặc localhost.
    - Nếu chưa có mô hình: đăng ký ảnh, sau đó chọn **Huấn luyện mô hình**.
    - Nếu nhận diện sai: đăng ký thêm ảnh đúng học sinh, ánh sáng tốt; giáo viên có thể ghi nhận thủ công.
    - Sao lưu `attendance.db`, `data/faces/` và `models/` ở nơi được bảo vệ trước khi chuyển máy.
    """
)
