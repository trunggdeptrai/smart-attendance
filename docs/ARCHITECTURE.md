# Kiến trúc hệ thống

## Tầng và trách nhiệm

| Tầng | Thư mục | Trách nhiệm |
|---|---|---|
| Giao diện | `app.py`, `pages/`, `ui/` | Điều hướng, biểu mẫu, hiển thị camera, bảng, biểu đồ. Không chứa logic nghiệp vụ phức tạp |
| Xử lý ảnh & nhận diện | `core/face_detect.py`, `save_face.py`, `face_dataset.py`, `face_recognizer.py`, `camera_stream.py`, `live_camera.py` | Phát hiện, cắt, mã hóa, phân loại, luồng nhận diện nền (thread) |
| Nghiệp vụ & dữ liệu | `db/` | Mô hình bảng, migration, CRUD lớp/học sinh/giáo viên, ghi và truy vấn lượt điểm danh, kiểm tra hợp lệ |
| Hạ tầng | `core/paths.py`, `core/backup.py`, `core/research_log.py`, `core/attendance_export.py` | Đường dẫn cấu hình được, sao lưu/khôi phục, nhật ký nghiên cứu, xuất Excel |
| Nghiên cứu | `research/` | Đánh giá offline, không chạy trong luồng điểm danh |

## Cơ sở dữ liệu (SQLite)

| Bảng | Vai trò |
|---|---|
| `classes` | Lớp học (`class_code` duy nhất, GVCN) |
| `teachers` | Giáo viên |
| `students` | Học sinh (`student_code` duy nhất, lớp, trạng thái: Đang học/Đã xóa/…) |
| `employees` | Bảng tương thích từ đồ án gốc (chấm công nhân viên); mỗi học sinh có một dòng tương ứng |
| `attendance_logs` | Lượt điểm danh: học sinh, lớp, ngày, buổi, `log_type` IN/OUT, trạng thái, phương thức face/manual, khoảng cách |
| `schema_migrations` | Phiên bản migration (1–3) |

Ràng buộc chống trùng: chỉ mục duy nhất có điều kiện `idx_student_attendance_session (student_code, attendance_date, session_name, log_type)` cho bản ghi face/manual.

Migration tự động tạo bản sao DB trong `database_backups/` trước khi nâng cấp schema.

## Luồng điểm danh camera trực tiếp

1. Component HTML/JS (`ui/live_camera/index.html`) lấy khung hình từ camera trình duyệt, gửi ảnh base64 về Streamlit.
2. `detect_faces` (480 px) → nếu đúng 1 khuôn mặt, `get_or_update_prediction` khởi chạy thread nền gọi `predict_face` (được bọc `logged_predictor` để ghi nhật ký).
3. Kết quả lưu trong `PredictionStore` (an toàn luồng), giãn cách thử lại 1,5 s khi Unknown.
4. Giáo viên bấm “Điểm danh vào/ra” → `record_student_attendance` kiểm tra hợp lệ → ghi DB → ghi `teacher_decisions.csv`.

## Cấu hình đường dẫn

`core/paths.py` cố định mọi đường dẫn theo thư mục dự án (trước đây phụ thuộc thư mục làm việc hiện hành) và cho phép ghi đè:

- `SMART_ATTENDANCE_DATA_ROOT` – thư mục gốc dữ liệu;
- `SMART_ATTENDANCE_DB` – tệp SQLite.

Nhờ đó kiểm thử chạy trên bản sao dữ liệu (`tests/run_all.py`) và có thể đặt dữ liệu ngoài thư mục mã nguồn khi triển khai.

## Khả năng mở rộng (định hướng, chưa thực hiện)

- Đăng nhập/phân quyền giáo viên.
- Mã hóa ảnh mẫu và tệp mô hình khi lưu.
- Thay Haar Cascade bằng bộ phát hiện học sâu (ví dụ CNN của dlib hoặc YuNet của OpenCV) – cần thực nghiệm so sánh trước.
