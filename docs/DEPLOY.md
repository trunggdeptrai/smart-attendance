# Triển khai

## 1. Đặc điểm kiến trúc ảnh hưởng đến lựa chọn nền tảng

- Streamlit là máy chủ Python **chạy liên tục** với WebSocket → không phù hợp nền tảng serverless (Vercel, Cloudflare Workers/Pages).
- `dlib` dùng bản dựng sẵn `dlib-bin` (không biên dịch). Trước đây biên dịch từ mã nguồn mất > 45 phút trên Streamlit Cloud và không hoàn thành.
- Dữ liệu ghi xuống đĩa (SQLite, ảnh, mô hình) → cần **ổ đĩa bền vững**; đĩa tạm sẽ mất dữ liệu khi khởi động lại.
- Dữ liệu sinh trắc học của học sinh → lưu trên máy chủ bên thứ ba ở nước ngoài làm tăng rủi ro pháp lý (Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân xếp dữ liệu sinh trắc học vào nhóm dữ liệu nhạy cảm).
- Camera trình duyệt cần HTTPS khi truy cập không qua `localhost`.
- Ứng dụng **chưa có đăng nhập** → mọi bản công khai đều ai cũng truy cập được.

## 2. So sánh nền tảng

Thông tin gói miễn phí/chi phí của các nhà cung cấp thay đổi thường xuyên; cần kiểm tra lại trên trang chính thức trước khi chọn.

| Tiêu chí | Máy tính cục bộ (khuyến nghị) | Docker trên máy chủ nội bộ trường | Hugging Face Spaces (Docker) | Render | Railway | VPS | Vercel / Cloudflare |
|---|---|---|---|---|---|---|---|
| Tương thích | Đã kiểm thử | Có Dockerfile | Chạy được Docker | Chạy được Docker | Chạy được Docker | Đầy đủ | **Không** (serverless) |
| Chi phí | 0 | 0 (máy sẵn có) | Gói CPU miễn phí | Gói miễn phí có giới hạn | Trả phí theo dùng | Trả phí hằng tháng | – |
| Lưu trữ bền vững | Có | Có (volume) | Đĩa tạm ở gói miễn phí | Đĩa bền vững là gói trả phí | Có volume | Có | – |
| Hoạt động lâu dài | Phụ thuộc máy | Tốt | Ngủ khi không dùng | Ngủ khi không dùng (gói miễn phí) | Tốt | Tốt | – |
| Bảo mật dữ liệu HS | Tốt nhất | Tốt | Dữ liệu ở bên thứ ba | Dữ liệu ở bên thứ ba | Dữ liệu ở bên thứ ba | Tự quản trị | – |
| Bảo trì | Dễ | Trung bình | Dễ | Dễ | Dễ | Khó | – |
| Demo tại cuộc thi | **Ổn định, không cần mạng** | Cần mạng LAN | Cần Internet, chờ khởi động | Cần Internet, chờ khởi động | Cần Internet | Cần Internet | – |

## 3. Khuyến nghị

1. **Trình diễn tại cuộc thi: chạy cục bộ trên laptop** (không phụ thuộc Internet). Chuẩn bị sẵn: `.venv` đã cài, dữ liệu demo đã đăng ký (chỉ của người đã đồng ý), bản sao lưu ZIP, camera USB dự phòng, ảnh thử in sẵn cho chế độ tải ảnh.
2. **Bản trực tuyến (tùy chọn):** chỉ dùng **dữ liệu demo không phải học sinh thật** (ví dụ ảnh của người hướng dẫn đã đồng ý) trên Hugging Face Spaces hoặc Render; chấp nhận dữ liệu mất khi khởi động lại. Lưu ý: hồ sơ dự thi **không được chèn link/QR** nên bản trực tuyến không đưa vào báo cáo/poster.
3. Không triển khai công khai với dữ liệu học sinh thật khi chưa có đăng nhập và mã hóa.

## 4. Chạy cục bộ (Windows)

Xem README. Kiểm tra chạy không cần Internet: ngắt Wi-Fi → `run.bat` → mở `http://localhost:8501` → điểm danh bằng ảnh tải lên.

## 5. Docker (máy chủ nội bộ)

```bash
# Tạo sẵn tệp DB rỗng để Docker không tạo nhầm thành thư mục khi mount
touch attendance.db          # PowerShell: New-Item attendance.db -ItemType File
mkdir -p data/faces models database_backups backups research_logs
docker compose up --build -d
```

Mặc định cổng chỉ mở trên `127.0.0.1:8501`. Muốn cho máy khác trong LAN truy cập phải đổi ánh xạ cổng **và** đặt sau reverse proxy có HTTPS + xác thực (ví dụ Caddy/Nginx basic auth). Camera USB gắn vào máy chủ không dùng được qua trình duyệt máy khác – dùng camera của máy khách.

## 6. Hugging Face Spaces (bản demo, dữ liệu không thật)

1. Tạo Space loại **Docker** (riêng tư nếu có thể).
2. Đẩy mã nguồn (không có `attendance.db`, `data/faces`, `models`).
3. Trong `Dockerfile`, Spaces yêu cầu cổng 7860: thêm biến môi trường hoặc đổi `--server.port=7860` và `EXPOSE 7860`.
4. Đặt biến `SMART_ATTENDANCE_DATA_ROOT=/tmp/sa_data` (thư mục ghi được).
5. Sau khi chạy: tạo lớp demo, đăng ký khuôn mặt của người đã đồng ý, kiểm tra điểm danh bằng ảnh.

## 7. Streamlit Community Cloud (bản demo, dữ liệu không thật)

1. Đăng nhập share.streamlit.io bằng tài khoản GitHub sở hữu repo.
2. **Create app → Deploy a public app from GitHub**: repo `trunggdeptrai/smart-attendance`, nhánh `main`, tệp chính `app.py`.
3. **Advanced settings → Python version: 3.11** (bắt buộc – các phiên bản khác chưa kiểm thử với dlib/NumPy 2.2.6).
4. Không cần `packages.txt`: `dlib-bin` là bản dựng sẵn; lần build đầu khoảng vài phút.
5. Giới hạn: ổ đĩa tạm (mất dữ liệu khi app ngủ/khởi động lại), tài nguyên hạn chế, app công khai, chưa có đăng nhập → **chỉ dùng dữ liệu demo**.
6. Nếu build thất bại: dùng Hugging Face Spaces (`deploy/huggingface/`) hoặc chạy cục bộ.

## 8. Biến môi trường

| Biến | Ý nghĩa |
|---|---|
| `SMART_ATTENDANCE_DATA_ROOT` | Thư mục gốc dữ liệu (nên đặt ngoài thư mục mã nguồn) |
| `SMART_ATTENDANCE_DB` | Đường dẫn tệp SQLite |
| `SMART_ATTENDANCE_RESEARCH_LOG` | `1`/`0` bật/tắt nhật ký nghiên cứu |

Ứng dụng không dùng mật khẩu/API key nào. Không đưa tệp `.env` lên GitHub.

## 9. Kiểm thử sau triển khai

- [ ] Trang tổng quan hiển thị, không lỗi.
- [ ] Tạo lớp, học sinh thử; đăng ký 3 ảnh; huấn luyện.
- [ ] Điểm danh bằng ảnh tải lên → xác nhận → xuất hiện trong Lịch sử.
- [ ] Thử điểm danh trùng → bị từ chối.
- [ ] Cài đặt → tạo bản sao lưu → `--verify` hợp lệ.
- [ ] Khởi động lại → dữ liệu còn nguyên (nếu có ổ đĩa bền vững).
