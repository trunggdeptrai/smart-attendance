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
    st.subheader("3. Điểm danh tự động")
    st.markdown(
        "Mở **Điểm danh tự động**, chọn buổi học và camera, bấm **ĐIỂM DANH VÀO**. "
        "Camera tự bật; từng học sinh đứng trước camera 1–2 giây, mỗi lần một người. "
        "Hệ thống ghi nhận khi cùng một học sinh được nhận ra ở 2 lần liên tiếp và "
        "hiển thị trong bảng học sinh đã điểm danh. Cuối buổi chọn **ĐIỂM DANH RA VỀ**; "
        "lượt ra chỉ được ghi cho học sinh đã có lượt vào. Bấm **Dừng camera** khi kết thúc."
    )

with st.container(border=True):
    st.subheader("4. Điểm danh có xác nhận và thủ công")
    st.markdown(
        "Mở **Điểm danh có xác nhận / thủ công** khi học sinh không nhận diện được hoặc "
        "cần điều chỉnh kết quả: chụp ảnh hoặc tải ảnh lên, kiểm tra mã, họ tên, lớp và "
        "xác nhận từng kết quả; có thể ghi nhận thủ công hoặc đánh dấu vắng mặt."
    )
    st.warning(
        "Không nhận diện được không có nghĩa là vắng mặt. Trạng thái vắng chỉ được "
        "lưu khi giáo viên chọn và xác nhận."
    )

with st.container(border=True):
    st.subheader("5. Tra cứu báo cáo")
    st.markdown(
        "Dùng **Lịch sử điểm danh** để lọc và xuất CSV/Excel; dùng **Báo cáo chuyên cần** "
        "để xem sĩ số, các trạng thái đã xác nhận và học sinh chưa ghi nhận."
    )

st.subheader("Khắc phục sự cố")
st.markdown(
    """
    - Nếu camera không hiển thị: kiểm tra quyền camera của trình duyệt và chọn HTTPS hoặc localhost. Trên iPhone, mở bằng Safari.
    - Nếu báo nhiều khuôn mặt: chỉ để một học sinh trong khung hình.
    - Nếu chưa có mô hình: đăng ký ảnh, sau đó chọn **Huấn luyện mô hình**.
    - Nếu nhận diện sai: đăng ký thêm ảnh đúng học sinh, ánh sáng tốt; giáo viên có thể ghi nhận thủ công.
    - Tạo bản sao lưu tại **Cài đặt** trước khi cập nhật phiên bản hoặc chuyển máy.
    """
)
