# Sao lưu và khôi phục

## Dữ liệu cần bảo vệ

| Dữ liệu | Vị trí | Ghi chú |
|---|---|---|
| Hồ sơ, lượt điểm danh | `attendance.db` | SQLite |
| Ảnh mẫu khuôn mặt | `data/faces/<mã>/` | Dữ liệu sinh trắc học |
| Mô hình | `models/` | Vector đặc trưng – cũng là dữ liệu sinh trắc học |
| Nhật ký nghiên cứu | `research_logs/` | Không có ảnh |

## Tạo bản sao lưu

- **Giao diện:** Cài đặt → *Tạo bản sao lưu ngay* → *Tải tệp sao lưu đã chọn*.
- **Dòng lệnh:** `python scripts/restore_backup.py --create`

Tệp ZIP lưu tại `backups/`, gồm `manifest.json` (thời điểm, số tệp, SHA-256 của DB). DB được chụp bằng SQLite Online Backup API nên an toàn khi ứng dụng đang chạy.

Khuyến nghị: sao lưu sau mỗi buổi thực nghiệm và trước mỗi lần cập nhật; giữ ít nhất 2 bản ở 2 nơi riêng tư (ví dụ ổ cứng ngoài có mật khẩu). Không gửi qua mạng xã hội, không đưa lên GitHub.

## Kiểm tra bản sao lưu

```powershell
python scripts/restore_backup.py --verify backups\smart_attendance_backup_YYYYMMDD-HHMMSS.zip
```

## Khôi phục

1. Dừng ứng dụng (đóng cửa sổ Streamlit / Ctrl+C).
2. `python scripts/restore_backup.py backups\<tệp>.zip` → gõ `dong y`.
3. Công cụ tự tạo `..._before-restore.zip` trước khi ghi đè, rồi thay DB, `data/faces/`, `models/`, `research_logs/` bằng nội dung bản sao lưu.
4. Khởi động lại và kiểm tra Trang tổng quan, Lịch sử điểm danh.

## Cài đặt lại trên máy mới

1. Cài đặt theo README.
2. Chép tệp ZIP sang máy mới → chạy bước Khôi phục.

## Xóa dữ liệu khi kết thúc nghiên cứu

- Từng học sinh: trang Đăng ký khuôn mặt → *Xóa ảnh mẫu và huấn luyện lại*.
- Toàn bộ: dừng ứng dụng, tạo bản sao lưu cuối (nếu cần lưu trữ theo quy định), xóa `data/faces/`, `models/`, các tệp ZIP trong `backups/` không còn cần thiết. Ghi việc xóa vào nhật ký nghiên cứu.
