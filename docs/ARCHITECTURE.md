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
| `employees` | Bảng định danh kỹ thuật (tên lịch sử). Phản chiếu 1:1 bảng `students` (cùng mã học sinh; cột `department` = tên lớp), được tạo/cập nhật tự động cùng hồ sơ học sinh. Tồn tại vì `attendance_logs.employee_code` (NOT NULL) có khóa ngoại trỏ tới đây. Giao diện và nghiệp vụ chỉ dùng `students` |
| `attendance_logs` | Lượt điểm danh: học sinh, lớp, ngày, buổi, `log_type` IN/OUT, trạng thái, phương thức face/manual, khoảng cách |
| `schema_migrations` | Phiên bản migration (1–3) |

Ràng buộc chống trùng: chỉ mục duy nhất có điều kiện `idx_student_attendance_session (student_code, attendance_date, session_name, log_type)` cho bản ghi face/manual.

Migration tự động tạo bản sao DB trong `database_backups/` trước khi nâng cấp schema.

## Luồng điểm danh tự động (trang Điểm danh tự động)

1. Giáo viên chọn chế độ ĐIỂM DANH VÀO hoặc ĐIỂM DANH RA VỀ → tạo phiên quét mới (`AutoAttendanceSession`, `core/auto_attendance.py`) và tự bật camera.
2. Mỗi kết quả nhận diện mới đi qua `ConsensusTracker`: chỉ xác nhận khi cùng một mã học sinh xuất hiện ở 2 lần nhận diện liên tiếp trong 8 giây và khung hình có đúng 1 khuôn mặt.
3. Mã đã xác nhận được bỏ qua 10 giây (cooldown) để không truy vấn, ghi lặp.
4. `auto_record()` kiểm tra lịch sử trong buổi (đã có lượt vào/ra, lượt ra cần lượt vào, học sinh đã xác nhận vắng) rồi gọi `record_student_attendance()` – cùng hàm ghi với điểm danh thủ công; chỉ mục duy nhất của SQLite chặn ghi trùng khi có yêu cầu đồng thời.
5. Bảng ghi nhận và thống kê trong buổi đọc trực tiếp từ cơ sở dữ liệu, tự làm mới mỗi 2 giây.

## Luồng điểm danh có xác nhận (trang Điểm danh có xác nhận / thủ công)

1. Component HTML/JS (`ui/live_camera/index.html`) lấy khung hình từ camera trình duyệt, gửi ảnh base64 về Streamlit.
2. `detect_faces` (480 px) → nếu đúng 1 khuôn mặt, `get_or_update_prediction` khởi chạy thread nền gọi `predict_face` (được bọc `logged_predictor` để ghi nhật ký).
3. Kết quả lưu trong `PredictionStore` (an toàn luồng), giãn cách thử lại 1,5 s khi Unknown.
4. Giáo viên bấm “Điểm danh vào/ra” → `record_student_attendance` kiểm tra hợp lệ → ghi DB → ghi `teacher_decisions.csv`.

## Cấu hình đường dẫn

`core/paths.py` cố định mọi đường dẫn theo thư mục dự án (trước đây phụ thuộc thư mục làm việc hiện hành) và cho phép ghi đè:

- `SMART_ATTENDANCE_DATA_ROOT` – thư mục gốc dữ liệu;
- `SMART_ATTENDANCE_DB` – tệp SQLite.

Nhờ đó kiểm thử chạy trên bản sao dữ liệu (`tests/run_all.py`) và có thể đặt dữ liệu ngoài thư mục mã nguồn khi triển khai.

## Tên kỹ thuật kế thừa

Một số định danh nội bộ giữ tên lịch sử để không phá vỡ dữ liệu và migration đã có: bảng `employees`, cột `attendance_logs.employee_code`, lớp ORM `Employee`, các hàm `get_employee_codes`, `ensure_employee_folder`… Trong mọi trường hợp, giá trị lưu ở đây là **mã học sinh**. Giao diện, tài liệu và mã học sinh (`HSxxx`) dùng thuật ngữ học sinh.

Đổi tên bảng/cột (dự kiến migration v4) cần dựng lại `attendance_logs` trên SQLite (khóa ngoại, chỉ mục duy nhất có điều kiện, cột NOT NULL), cập nhật migration v1–3 và kiểm thử; chưa thực hiện vì rủi ro cao hơn lợi ích và không ảnh hưởng tới người dùng.

Đổi mã một học sinh (vd chuẩn hóa mã cũ) dùng `scripts/rename_student_code.py`: tự sao lưu, chạy thử trước, cập nhật đồng bộ `students`, `employees`, `attendance_logs`, thư mục ảnh mẫu và nhật ký.

## Khả năng mở rộng (định hướng, chưa thực hiện)

- Đăng nhập/phân quyền giáo viên.
- Mã hóa ảnh mẫu và tệp mô hình khi lưu.
- Thay Haar Cascade bằng bộ phát hiện học sâu (ví dụ CNN của dlib hoặc YuNet của OpenCV) – cần thực nghiệm so sánh trước.
