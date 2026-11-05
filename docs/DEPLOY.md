# Triển khai

Có 2 cách chạy Smart Attendance:

| | Chạy trên máy tính (khuyến nghị) | Streamlit Community Cloud (bản demo trực tuyến) |
|---|---|---|
| Chi phí | 0 | 0 (gói miễn phí) |
| Cần Internet | Không | Có |
| Lưu dữ liệu | Lâu dài, trên ổ cứng | Ổ đĩa tạm – **mất khi app ngủ/khởi động lại** |
| Dữ liệu học sinh thật | Được (có phiếu đồng ý) | **Không** – chỉ dữ liệu demo |
| Trình diễn | Ổn định | Phụ thuộc mạng |

Không dùng Vercel/Cloudflare: Streamlit cần máy chủ Python chạy liên tục.

## 1. Chạy trên máy tính (Windows)

1. Cài Python 3.11 (64-bit).
2. Trong thư mục dự án chạy `setup_windows.bat` một lần (tạo `.venv`, cài thư viện). `dlib` dùng bản dựng sẵn `dlib-bin`, không cần Visual Studio.
3. Đặt tài khoản đăng nhập: `.venv\Scripts\python.exe scripts\set_password.py` (mặc định tên `admin`).
4. Chạy `run.bat`, mở http://localhost:8501 và đăng nhập.

Ứng dụng chỉ mở trên chính máy (`127.0.0.1`). Kiểm tra chạy không cần mạng: tắt Wi-Fi rồi điểm danh bằng ảnh tải lên.

## 2. Streamlit Community Cloud

**Đã triển khai ngày 04/11/2026:** https://smart-attendance-demo.streamlit.app (nhánh `main`, Python 3.11). App tự cập nhật mỗi khi đẩy mã lên `main`.

Tạo lại từ đầu (nếu cần):
1. Đăng nhập share.streamlit.io bằng tài khoản GitHub sở hữu repo.
2. **Create app → Deploy a public app from GitHub**: repo `trunggdeptrai/smart-attendance`, nhánh `main`, tệp `app.py`.
3. **Advanced settings → Python version: 3.11**.
4. **Secrets** (bắt buộc – không có thì app chỉ hiện thông báo chưa cấu hình tài khoản): chạy `python scripts/set_password.py` trên máy, chép 3 dòng `[auth]` in ra màn hình vào ô Secrets.

Đổi mật khẩu bản online: share.streamlit.io → app → ⋮ → **Settings → Secrets** → dán khối `[auth]` mới → Save.

## 3. Đăng nhập và bảo mật

- Một tài khoản quản trị; mật khẩu lưu dạng băm PBKDF2-SHA256 (200.000 vòng, có salt) trong `.streamlit/secrets.toml` (máy cục bộ, đã `.gitignore`) hoặc Secrets (Streamlit Cloud). Mật khẩu không nằm trong mã nguồn hay GitHub.
- Sai 5 lần liên tiếp → khóa form 60 giây (theo phiên trình duyệt).
- Khi chưa đăng nhập, mọi đường dẫn trang (vd `/Settings`) đều chỉ hiện form đăng nhập.
- Nên dùng mật khẩu dài, khó đoán và đổi ngay nếu nghi bị lộ.
- Hạn chế: chưa phân quyền nhiều người dùng; chưa mã hóa ảnh mẫu/mô hình khi lưu.

## 4. Biến môi trường (tùy chọn)

| Biến | Ý nghĩa |
|---|---|
| `SMART_ATTENDANCE_DATA_ROOT` | Thư mục gốc dữ liệu |
| `SMART_ATTENDANCE_DB` | Đường dẫn tệp SQLite |
| `SMART_ATTENDANCE_RESEARCH_LOG` | `1`/`0` bật/tắt nhật ký nghiên cứu |
| `SMART_ATTENDANCE_ADMIN_USER`, `SMART_ATTENDANCE_ADMIN_PASSWORD_HASH` | Tài khoản đăng nhập khi không dùng `secrets.toml` |

## 5. Kiểm tra sau triển khai

- [ ] Mở trang → chỉ thấy form đăng nhập; mở thẳng `/Settings` cũng chỉ thấy form đăng nhập.
- [ ] Đăng nhập đúng → vào được; sai → báo lỗi.
- [ ] Tạo lớp, học sinh thử; đăng ký 3 ảnh; huấn luyện.
- [ ] Điểm danh bằng ảnh tải lên → xác nhận → có trong Lịch sử; thử ghi trùng → bị từ chối.
- [ ] Cài đặt → tạo bản sao lưu.
