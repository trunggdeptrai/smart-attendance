# face_recognition (mã bên thứ ba, sao chép nguyên bản)

- Nguồn: gói PyPI `face-recognition` 1.3.0 – tác giả Adam Geitgey (https://github.com/ageitgey/face_recognition).
- Giấy phép: MIT (xem `LICENSE` trong thư mục này). Chỉ sao chép `__init__.py` và `api.py`, không chỉnh sửa.
- Lý do: gói gốc khai báo phụ thuộc `dlib` nên trình cài đặt buộc biên dịch dlib từ mã nguồn
  (mất > 45 phút trên Streamlit Community Cloud, cần Visual Studio Build Tools trên Windows).
  Sao chép 2 tệp này cho phép dùng bản dựng sẵn `dlib-bin` (cùng phiên bản dlib 20.0.1).
- Mô hình đi kèm vẫn lấy từ gói `face-recognition-models` (CC0/MIT của tác giả).
