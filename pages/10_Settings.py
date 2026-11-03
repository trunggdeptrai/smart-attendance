import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.face_recognizer import ENCODINGS_PATH, LABEL_MAP_PATH
from db.session import DB_PATH, engine

st.title("Cài đặt và tình trạng hệ thống")
st.caption("Thông tin vận hành hiện tại; các đường dẫn dữ liệu chỉ được hiển thị cục bộ.")

database_ok = False
database_error = None
try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        database_ok = True
except SQLAlchemyError as error:
    database_error = str(error)

status_col, model_col = st.columns(2)
with status_col:
    st.subheader("Cơ sở dữ liệu")
    if database_ok:
        st.success("SQLite đang hoạt động.")
    else:
        st.error(f"Không thể kết nối SQLite: {database_error}")
    st.code(str(DB_PATH), language=None)
    st.caption("Sao lưu tệp cơ sở dữ liệu trước khi triển khai hoặc di chuyển máy chủ.")

with model_col:
    st.subheader("Mô hình nhận diện")
    if ENCODINGS_PATH.exists() and LABEL_MAP_PATH.exists():
        st.success("Đã có dữ liệu mô hình nhận diện.")
    else:
        st.warning("Chưa có mô hình. Đăng ký ảnh khuôn mặt rồi huấn luyện mô hình.")
    st.caption("Embeddings được lưu trong thư mục models/; không đưa thư mục này lên nơi công khai.")

st.subheader("Camera và quyền riêng tư")
st.markdown(
    """
    - Camera được mở từ trình duyệt khi người dùng chụp ảnh; hãy cấp quyền camera cho trang ứng dụng.
    - Ảnh mẫu khuôn mặt nằm trong `data/faces/` trên máy chạy ứng dụng.
    - Không lưu ảnh/embeddings vào thư mục public hoặc kho mã nguồn.
    - Chỉ thu thập dữ liệu sinh trắc học khi có sự đồng ý và tuân thủ quy định bảo vệ dữ liệu cá nhân.
    - Ứng dụng hiện chưa có đăng nhập/phân quyền giáo viên; chỉ triển khai trong môi trường được kiểm soát.
    """
)
