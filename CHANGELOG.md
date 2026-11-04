# Nhật ký thay đổi

## [1.1.0] – 04/11/2026 (chưa phát hành)

Thực hiện bởi người hướng dẫn với sự hỗ trợ của trợ lý AI (Claude Code); đã khai báo trong Phụ lục VI.

### Sửa lỗi
- **Kiểm thử ghi vào cơ sở dữ liệu thật**: các tệp `tests/test_*.py` cũ tạo hồ sơ/lượt điểm danh thử trong `attendance.db`. Thêm `tests/run_all.py` chạy trên bản sao dữ liệu tạm và kiểm tra DB thật không đổi.
- **Cho phép điểm danh cho ngày tương lai**: bổ sung kiểm tra trong `record_student_attendance` và giới hạn ô chọn ngày.
- **Đường dẫn phụ thuộc thư mục làm việc**: `models/`, `data/faces/` trước đây là đường dẫn tương đối → chạy từ thư mục khác sẽ không thấy mô hình. Thêm `core/paths.py`.
- Bình luận trong mã khẳng định ngưỡng 0,48 “triệt tiêu 100% rủi ro nhận nhầm” chưa có căn cứ thực nghiệm → sửa lại thành ghi chú kiểm chứng.

### Bổ sung
- `classify_encoding`, `encode_face_crop`: tách thuật toán phân loại thành hàm thuần, hỗ trợ chiến lược đối chứng 1-NN, chế độ dò lại HOG, ngưỡng thử nghiệm; trả thêm `latency_ms`, `reject_reason`. Hành vi mặc định giữ nguyên (đã đối chiếu 0 sai khác trên 22 ảnh × 2 hồ sơ camera).
- `research/evaluate_recognition.py`: đánh giá offline (tập kiểm thử độc lập hoặc bỏ-ra-một), quét ngưỡng, chặn ảnh trùng ảnh huấn luyện, ghi thông tin tái lập.
- `core/research_log.py` + trang **Đánh giá thực nghiệm**: nhật ký nhận diện và quyết định của giáo viên (không lưu ảnh).
- `core/backup.py`, `scripts/restore_backup.py`, mục sao lưu trong **Cài đặt**: sao lưu ZIP nhất quán, kiểm tra SHA-256, khôi phục có bản an toàn.
- Xóa ảnh mẫu của một học sinh và huấn luyện lại (rút lại sự đồng ý); xóa tệp mô hình khi không còn ảnh mẫu.
- Tài liệu: `docs/ARCHITECTURE.md`, `ALGORITHM.md`, `RESEARCH_TOOLKIT.md`, `BACKUP_RESTORE.md`, `DEPLOY.md`; `.env.example`; `requirements-lock.txt`.
- README viết lại: mô tả trung thực nguồn gốc mã nguồn, hạn chế, quyền riêng tư.

## [1.0.0] – 03/11/2026
- Commit khởi tạo trên GitHub (phiên bản người hướng dẫn phát triển từ đồ án có sẵn).
