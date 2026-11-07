# LỊCH SỬ PHÁT TRIỂN

Ghi nhận các thay đổi của Smart Attendance theo từng phiên bản. Chỉ ghi các chức năng đã có trong mã nguồn và đã được kiểm thử.

## Phiên bản 1.2.0 – 07/11/2026

### Chức năng mới
- **Điểm danh tự động** với hai chế độ ĐIỂM DANH VÀO và ĐIỂM DANH RA VỀ: chọn chế độ là camera tự bật, nhận diện liên tục và tự ghi vào cơ sở dữ liệu, không cần xác nhận từng học sinh.
  - Chỉ ghi khi cùng một học sinh được nhận ra ở 2 lần nhận diện liên tiếp trong 8 giây và khung hình có đúng một khuôn mặt; sau khi xử lý, tạm bỏ qua học sinh đó 10 giây.
  - Mỗi học sinh một lượt vào, một lượt ra trong mỗi buổi; lượt ra cần có lượt vào trước.
  - Bảng học sinh đã điểm danh trong buổi, lọc theo lớp, thống kê lấy trực tiếp từ cơ sở dữ liệu; âm thanh báo tùy chọn.
- Trang điểm danh trước đây được giữ nguyên chức năng với tên **Điểm danh có xác nhận / thủ công**.
- **Bộ cài đặt một lần bấm cho Windows** (thư mục `setup/`): tự xin quyền quản trị, cài Python 3.11 bản chính thức (kiểm tra chữ ký số) khi máy chưa có, cài thư viện, khởi tạo dữ liệu, đặt tài khoản, tạo lối tắt Desktop và mở ứng dụng; báo lỗi rõ ràng khi chưa giải nén, mất mạng hoặc thiếu dung lượng; chạy lại nhiều lần không mất dữ liệu.
- Công cụ đổi mã học sinh đồng bộ trên toàn bộ dữ liệu (`scripts/rename_student_code.py`), có chế độ chạy thử và tự sao lưu.

### Cải tiến
- Thời gian ghi nhận, ngày điểm danh và các trang Tổng quan, Lịch sử, Báo cáo dùng giờ Việt Nam; hiển thị dạng DD/MM/YYYY HH:mm.
- Camera trên điện thoại: khung hình cắt theo tỷ lệ thực của camera (ảnh dọc không còn mất khuôn mặt); chọn camera trước – camera sau; thanh trạng thái nhận diện ngay dưới khung camera; cảnh báo khi mở trong trình duyệt của ứng dụng khác.
- Thống nhất thuật ngữ học sinh, lớp học, mã học sinh trên giao diện và tài liệu.
- Tài liệu giới thiệu, hướng dẫn cài đặt và lịch sử phát triển được viết lại bằng tiếng Việt.

### Sửa lỗi
- Camera trên iPhone: không còn mở video toàn màn hình hoặc dừng hình khi trình duyệt chặn tự phát.
- Biểu mẫu điểm danh thủ công luôn có đủ ba trạng thái, kể cả "Vắng mặt".
- Thông báo lỗi quyền camera hiển thị bằng tiếng Việt kèm hướng dẫn.
- Bộ cài đặt: ô nhập mật khẩu không nhận phím; chữ tiếng Việt hiển thị sai trong cửa sổ cài đặt.
- Tệp `.bat`, `.ps1` giữ đúng định dạng xuống dòng của Windows khi tải mã nguồn dạng ZIP.

### Loại bỏ
- Công cụ tải bộ ảnh khuôn mặt từ Internet (`download_dataset.py`, `requirements-dataset.txt`): không được ứng dụng sử dụng và không phù hợp yêu cầu bảo vệ dữ liệu khuôn mặt.

## Phiên bản 1.1.0 – 05/11/2026

### Chức năng mới
- **Đăng nhập bắt buộc:** một tài khoản quản trị, mật khẩu băm PBKDF2-SHA256 có salt, khóa 60 giây sau 5 lần nhập sai; chưa đăng nhập thì mọi trang chỉ hiển thị biểu mẫu đăng nhập.
- **Công cụ đánh giá độ chính xác nhận diện** (`research/evaluate_recognition.py`): dùng tập ảnh kiểm thử độc lập hoặc phương pháp bỏ-ra-một, so sánh với phương pháp đối chứng, quét ngưỡng, chặn ảnh kiểm thử trùng ảnh huấn luyện.
- **Nhật ký nhận diện** và trang **Đánh giá thực nghiệm**: tỷ lệ khớp, lý do từ chối, thời gian xử lý (không lưu ảnh).
- **Sao lưu và khôi phục** dữ liệu dạng ZIP có kiểm tra SHA-256; luôn tạo bản an toàn trước khi khôi phục.
- Xóa dữ liệu khuôn mặt của từng học sinh và huấn luyện lại mô hình.
- Tài liệu kỹ thuật: kiến trúc, thuật toán, công cụ đánh giá, sao lưu, triển khai.

### Cải tiến
- Dùng bản dựng sẵn của dlib: cài đặt không cần trình biên dịch; vector đặc trưng trùng khớp với bản biên dịch.
- Tách thuật toán phân loại thành hàm độc lập để đánh giá; kết quả mặc định không thay đổi so với bản trước.
- Đường dẫn dữ liệu cố định theo thư mục dự án, có thể thay đổi bằng biến môi trường.

### Sửa lỗi
- Bộ kiểm thử ghi vào cơ sở dữ liệu thật: nay chạy trên bản sao tạm và tự xác nhận dữ liệu thật không đổi.
- Cho phép ghi điểm danh cho ngày tương lai: đã chặn ở giao diện và tầng dữ liệu.

### Loại bỏ
- Cấu hình Docker, Hugging Face Spaces và Dev Container (không sử dụng).

## Phiên bản 1.0.0 – 03/11/2026

- Phiên bản đầu tiên: quản lý lớp học, học sinh, giáo viên; đăng ký khuôn mặt; điểm danh vào và ra về có giáo viên xác nhận; lịch sử điểm danh; báo cáo chuyên cần; xuất Excel.
- Bộ cài đặt Windows (`setup_windows.bat`), hướng dẫn cài đặt, công cụ kiểm tra môi trường; cố định phiên bản thư viện.
