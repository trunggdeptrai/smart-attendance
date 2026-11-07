# Nhật ký thay đổi

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/).

## [Chưa phát hành]

### Thêm mới
- **Bộ cài 1 lần bấm cho Windows** (`setup/CAI_DAT_SMART_ATTENDANCE.bat`, `setup/install.ps1`): tự xin quyền Administrator, cài Python 3.11.9 từ python.org nếu chưa có (kiểm tra chữ ký số), tạo `.venv`, cài thư viện, khởi tạo dữ liệu, đặt mật khẩu, tạo lối tắt Desktop và mở ứng dụng; báo lỗi rõ khi chưa giải nén ZIP, mất mạng, thiếu dung lượng.
- `.gitattributes`: tệp `.bat`/`.ps1` luôn dùng xuống dòng CRLF, kể cả trong ZIP tải từ GitHub (trước đây `run.bat` trong ZIP dùng LF).
- **Điểm danh tự động** (trang `pages/4_Attendance.py`, logic `core/auto_attendance.py`): hai chế độ ĐIỂM DANH VÀO / ĐIỂM DANH RA VỀ; chọn chế độ là camera tự bật, nhận diện liên tục và tự ghi vào cơ sở dữ liệu, không cần bấm xác nhận từng học sinh.
  - Chỉ ghi khi cùng một học sinh được nhận ra ở 2 lần nhận diện liên tiếp (trong 8 giây) và khung hình có đúng 1 khuôn mặt; sau khi xử lý, bỏ qua học sinh đó 10 giây.
  - Mỗi học sinh một lượt vào, một lượt ra trong mỗi buổi; ra về khi chưa có lượt vào → "CHƯA CÓ DỮ LIỆU ĐIỂM DANH VÀO"; ghi trùng bị chặn bởi kiểm tra trước khi ghi và chỉ mục duy nhất của SQLite.
  - Bảng học sinh đã điểm danh trong buổi (STT, mã, họ tên, lớp, thời gian, trạng thái), lọc theo lớp, thống kê lấy trực tiếp từ cơ sở dữ liệu, tự làm mới 2 giây; âm thanh báo tùy chọn.
  - Trang cũ được giữ nguyên chức năng, đổi tên thành **Điểm danh có xác nhận / thủ công** (`pages/13_Attendance_Manual.py`).
- Giờ Việt Nam (`core/timeutil.py`, Asia/Ho_Chi_Minh) cho thời điểm ghi, ngày điểm danh, Tổng quan, Lịch sử và Báo cáo; hiển thị DD/MM/YYYY HH:mm.
- Kiểm thử điểm danh tự động (`tests/test_auto_attendance.py`, 15 trường hợp).
- `scripts/rename_student_code.py`: đổi mã một học sinh đồng bộ trên `students`, bảng định danh kỹ thuật, `attendance_logs`, thư mục ảnh mẫu và nhật ký; chạy thử mặc định, tự sao lưu khi thực hiện.
- Kiểm thử xuất/nhập Excel (`tests/test_excel_io.py`) và công cụ đổi mã (`tests/test_rename_student_code.py`).

### Sửa lỗi
- Bộ cài `setup/`: ô mật khẩu không nhận phím (getpass của Python đọc bàn phím sai khi chạy lồng trong PowerShell quyền Administrator) → bộ cài tự hỏi mật khẩu bằng PowerShell (hiện dấu `*`), kiểm tra độ dài và gõ lại; `scripts/set_password.py` thêm `--username`, `--password-env` và kiểm tra tên đăng nhập. Chữ tiếng Việt in ra trong bộ cài không còn bị thành dấu `?`.
- **Camera trên điện thoại (iOS/Android):**
  - Khung hình gửi đi nhận diện luôn bị cắt theo tỷ lệ 16:9; camera điện thoại cho ảnh dọc nên chỉ còn một dải ngang và mất khuôn mặt (kiểm chứng trên khung hình iPhone: cũ 0 khuôn mặt, mới phát hiện được). Nay cắt theo tỷ lệ thực của camera (giới hạn 3:4–16:9), khung hiển thị đổi tỷ lệ theo.
  - iOS mở video toàn màn hình hoặc hiện trình phát gốc: thêm `webkit-playsinline`, tắt PiP/điều khiển, chặn chạm vào video.
  - Video đứng khi iOS từ chối tự phát: hiện nút "Chạm để bắt đầu camera", tự phát lại khi quay lại trang, không gửi khung hình lúc video đang dừng.
  - Cảnh báo khi mở trong trình duyệt nhúng của ứng dụng khác (Zalo, Messenger…), khuyên dùng Safari/Chrome.
  - Điện thoại: Camera 1 = camera trước, Camera 2 = camera sau (máy tính giữ cách chọn theo thiết bị).
  - Thanh trạng thái ngay dưới khung camera: đang tìm khuôn mặt / đang nhận diện / kết quả nhận diện / không xác định được danh tính / nhiều khuôn mặt.
- Form điểm danh thủ công: khi đầu trang đang chọn "Điểm danh ra", đổi sang "Điểm danh vào" trong form vẫn không có lựa chọn "Vắng mặt" (form không chạy lại trang) → luôn hiển thị đủ 3 trạng thái; lượt ra + vắng mặt vẫn bị từ chối ở tầng dữ liệu.
- Camera bị trình duyệt chặn quyền chỉ hiện "Permission denied" → hiển thị hướng dẫn tiếng Việt (cấp quyền hoặc dùng chế độ tải ảnh).

### Thay đổi
- Thống nhất thuật ngữ học sinh: trang Quản lý học sinh đổi tên tệp thành `pages/2_Students.py` (đường dẫn `/Students`); thông báo và chú thích trong mã dùng "học sinh".
- README bổ sung mục Mô hình dữ liệu; `docs/ARCHITECTURE.md` mô tả rõ các tên kỹ thuật kế thừa (bảng `employees`, cột `employee_code`) chỉ lưu mã học sinh.

## [1.1.0] – 2026-11-05

### Thêm mới
- **Đăng nhập** (`core/auth.py`, `scripts/set_password.py`): một tài khoản quản trị, mật khẩu băm PBKDF2-SHA256 có salt, khóa 60 giây sau 5 lần sai; khi chưa đăng nhập, mọi đường dẫn trang chỉ hiển thị form đăng nhập.
- **Công cụ đánh giá offline** (`research/evaluate_recognition.py`): tập kiểm thử độc lập hoặc bỏ-ra-một, so sánh với phương pháp đối chứng 1-NN, quét ngưỡng, chặn ảnh kiểm thử trùng ảnh huấn luyện, ghi thông tin tái lập.
- **Nhật ký nhận diện** (`core/research_log.py`) và trang **Đánh giá thực nghiệm**: thống kê tỷ lệ khớp, lý do từ chối, thời gian xử lý, quyết định của giáo viên (không lưu ảnh).
- **Sao lưu/khôi phục** (`core/backup.py`, `scripts/restore_backup.py`, mục sao lưu trong trang Cài đặt): ZIP nhất quán, kiểm tra SHA-256, luôn tạo bản an toàn trước khi khôi phục.
- Xóa ảnh mẫu của từng học sinh và huấn luyện lại; xóa tệp mô hình khi không còn ảnh mẫu.
- `classify_encoding`, `encode_face_crop`: tách thuật toán phân loại thành hàm thuần, hỗ trợ chiến lược đối chứng và trả thêm `latency_ms`, `reject_reason`. Hành vi mặc định giữ nguyên (0 sai khác so với bản trước trên 22 ảnh × 2 hồ sơ camera).
- Tài liệu: `docs/ARCHITECTURE.md`, `ALGORITHM.md`, `RESEARCH_TOOLKIT.md`, `BACKUP_RESTORE.md`, `DEPLOY.md`; `.env.example`.

### Thay đổi
- Dùng bản dựng sẵn `dlib-bin` 20.0.1 thay cho biên dịch `dlib`; mã nguồn `face_recognition` (MIT) được đưa vào thư mục `face_recognition/` kèm giấy phép. Cài đặt không còn cần Visual Studio Build Tools/CMake; vector đặc trưng trùng khớp với bản biên dịch.
- Đường dẫn dữ liệu cố định theo thư mục dự án và có thể ghi đè bằng biến môi trường (`core/paths.py`).
- `setup_windows.bat` hỏi đặt tài khoản đăng nhập khi cài lần đầu.

### Sửa lỗi
- Kiểm thử ghi vào cơ sở dữ liệu thật: thêm `tests/run_all.py` chạy trên bản sao dữ liệu tạm và xác nhận DB thật không đổi.
- Cho phép ghi điểm danh cho ngày tương lai: bổ sung kiểm tra ở tầng dữ liệu và giới hạn ô chọn ngày.
- Bình luận trong mã khẳng định ngưỡng nhận diện không có căn cứ thực nghiệm được sửa thành ghi chú kiểm chứng.

### Gỡ bỏ
- Cấu hình Docker, Hugging Face Spaces và `.devcontainer` (không sử dụng). Triển khai: máy cục bộ hoặc Streamlit Community Cloud.

## [1.0.0] – 2026-11-03
- Phiên bản đầu trên GitHub: quản lý lớp, học sinh, giáo viên; đăng ký khuôn mặt; điểm danh vào/ra có giáo viên xác nhận; lịch sử và báo cáo chuyên cần; xuất Excel.
- Sửa ổn định, bộ cài Windows (`setup_windows.bat`, `INSTALL_WINDOWS.md`, `check_environment.py`), ghim phiên bản phụ thuộc.
