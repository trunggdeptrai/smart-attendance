# SMART ATTENDANCE

**Hệ thống hỗ trợ quản lý và điểm danh học sinh bằng công nghệ nhận diện khuôn mặt ứng dụng trí tuệ nhân tạo.**

Phiên bản 1.2.0 · Python 3.11 · Streamlit · OpenCV · dlib · SQLite

## Mục lục

1. [Giới thiệu sản phẩm](#1-giới-thiệu-sản-phẩm)
2. [Mục tiêu xây dựng](#2-mục-tiêu-xây-dựng)
3. [Chức năng chính](#3-chức-năng-chính)
4. [Đối tượng sử dụng](#4-đối-tượng-sử-dụng)
5. [Công nghệ phát triển](#5-công-nghệ-phát-triển)
6. [Kiến trúc hệ thống](#6-kiến-trúc-hệ-thống)
7. [Cấu trúc thư mục](#7-cấu-trúc-thư-mục)
8. [Quy trình nhận diện khuôn mặt](#8-quy-trình-nhận-diện-khuôn-mặt)
9. [Quy trình điểm danh vào và ra về](#9-quy-trình-điểm-danh-vào-và-ra-về)
10. [Quản lý học sinh và lớp học](#10-quản-lý-học-sinh-và-lớp-học)
11. [Quản lý dữ liệu](#11-quản-lý-dữ-liệu)
12. [Cài đặt trên Windows](#12-cài-đặt-trên-windows)
13. [Khởi chạy ứng dụng](#13-khởi-chạy-ứng-dụng)
14. [Hướng dẫn sử dụng](#14-hướng-dẫn-sử-dụng)
15. [Sao lưu và khôi phục](#15-sao-lưu-và-khôi-phục)
16. [Khắc phục sự cố](#16-khắc-phục-sự-cố)
17. [Hướng phát triển](#17-hướng-phát-triển)

---

## 1. Giới thiệu sản phẩm

Smart Attendance là ứng dụng web hỗ trợ giáo viên điểm danh học sinh bằng nhận diện khuôn mặt. Học sinh chỉ cần đứng trước camera trong 1–2 giây; hệ thống nhận diện, ghi nhận lượt điểm danh vào hoặc ra về và cập nhật ngay vào lịch sử điểm danh, thống kê chuyên cần.

Ứng dụng chạy trên một máy tính phổ thông có webcam, không cần Internet trong quá trình sử dụng. Toàn bộ dữ liệu học sinh và ảnh khuôn mặt được lưu trên máy của nhà trường. Hệ thống có đăng nhập, sao lưu – khôi phục dữ liệu và bộ công cụ đánh giá độ chính xác nhận diện.

## 2. Mục tiêu xây dựng

- Rút ngắn thời gian điểm danh đầu và cuối buổi học so với gọi tên thủ công.
- Hạn chế ghi nhận sai: chỉ ghi khi kết quả nhận diện ổn định qua nhiều khung hình, không tự ghi vắng cho học sinh chưa được nhận diện.
- Hoạt động được với thiết bị sẵn có của nhà trường (máy tính, webcam, điện thoại).
- Bảo vệ dữ liệu cá nhân: dữ liệu lưu cục bộ, có cơ chế xóa dữ liệu khuôn mặt và sao lưu có kiểm tra toàn vẹn.
- Cung cấp số liệu đo được về độ tin cậy của nhận diện trong điều kiện lớp học thực tế.

## 3. Chức năng chính

| Phân hệ | Chức năng |
|---|---|
| Đăng nhập | Tài khoản quản trị, mật khẩu băm PBKDF2-SHA256, khóa tạm sau 5 lần nhập sai |
| Trang tổng quan | Số học sinh, số lớp, tình hình điểm danh trong ngày; biểu đồ 7 ngày và theo lớp |
| Quản lý học sinh | Thêm, sửa, tìm kiếm; nhập danh sách từ Excel; ngừng theo dõi hồ sơ |
| Quản lý lớp học và giáo viên | Tạo, cập nhật lớp; hồ sơ giáo viên; giáo viên chủ nhiệm |
| Đăng ký khuôn mặt | Chụp bằng camera hoặc tải ảnh (mỗi ảnh đúng một khuôn mặt); huấn luyện mô hình; xóa dữ liệu khuôn mặt của từng học sinh |
| Điểm danh tự động | Hai chế độ **ĐIỂM DANH VÀO** và **ĐIỂM DANH RA VỀ**; camera tự bật, nhận diện liên tục, tự ghi kết quả; bảng học sinh đã điểm danh trong buổi; lọc theo lớp; âm thanh báo tùy chọn |
| Điểm danh có xác nhận / thủ công | Nhận diện qua camera, chụp ảnh hoặc tải ảnh; giáo viên xác nhận từng học sinh; điểm danh thủ công và điều chỉnh kết quả |
| Lịch sử điểm danh | Lọc theo ngày, lớp, học sinh, trạng thái; xuất CSV, Excel |
| Báo cáo chuyên cần | Thống kê theo lớp, ngày, buổi; phân biệt "chưa ghi nhận" và "vắng mặt đã xác nhận"; xuất CSV, Excel |
| Đánh giá thực nghiệm | Thống kê từ nhật ký nhận diện: tỷ lệ khớp, lý do từ chối, thời gian xử lý |
| Cài đặt | Tình trạng cơ sở dữ liệu và mô hình; tạo, tải bản sao lưu |
| Hướng dẫn sử dụng | Hướng dẫn thao tác, cấp quyền camera, lưu ý về quyền riêng tư |

Camera hoạt động trên trình duyệt máy tính và điện thoại (Safari trên iPhone, Chrome trên Android), có lựa chọn camera trước – camera sau.

## 4. Đối tượng sử dụng

- **Giáo viên chủ nhiệm, giáo viên bộ môn:** điểm danh, theo dõi chuyên cần, xuất báo cáo.
- **Cán bộ quản lý, văn phòng nhà trường:** quản lý danh sách lớp, học sinh, tổng hợp số liệu.
- **Học sinh tham gia nghiên cứu:** cài đặt, vận hành và đánh giá hệ thống theo kế hoạch nghiên cứu.

## 5. Công nghệ phát triển

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.11 (64-bit) |
| Giao diện web | Streamlit 1.55 (ứng dụng đa trang) và component camera HTML/JavaScript |
| Phát hiện khuôn mặt | OpenCV 4.13 – bộ phân loại Haar Cascade |
| Trích xuất đặc trưng | dlib 20.0.1 (bản dựng sẵn `dlib-bin`) và thư viện `face_recognition` – vector đặc trưng 128 chiều |
| Phân loại | K-NN có trọng số khoảng cách (K = 3), ngưỡng riêng cho từng học sinh, kiểm tra khoảng cách biên, đa số phiếu |
| Lưu trữ | SQLite, SQLAlchemy 2 |
| Báo cáo, biểu đồ | pandas, openpyxl, Plotly |
| Múi giờ | Giờ Việt Nam (Asia/Ho_Chi_Minh) |

## 6. Kiến trúc hệ thống

```text
Trình duyệt (camera máy tính / điện thoại)
        │  khung hình JPEG
        ▼
Streamlit  ── pages/   (giao diện: điểm danh, quản lý, báo cáo, cài đặt)
        │
        ├── core/      (phát hiện, mã hóa, phân loại khuôn mặt; điểm danh tự động;
        │               xác thực; xuất báo cáo; sao lưu; nhật ký đánh giá)
        └── db/        (SQLAlchemy: lớp, học sinh, giáo viên, lượt điểm danh)
                │
                ▼
Dữ liệu cục bộ: attendance.db · data/faces/ · models/ · backups/ · research_logs/
```

Tài liệu chi tiết: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (kiến trúc, mô hình dữ liệu), [docs/ALGORITHM.md](docs/ALGORITHM.md) (thuật toán nhận diện).

## 7. Cấu trúc thư mục

```text
smart-attendance/
├── app.py                  Điểm khởi chạy: đăng nhập, khởi tạo dữ liệu, menu
├── pages/                  Các trang giao diện
├── core/                   Xử lý nghiệp vụ
│   ├── auto_attendance.py  Điểm danh tự động (đồng thuận nhiều khung hình, chống ghi trùng)
│   ├── face_detect.py      Phát hiện khuôn mặt
│   ├── face_recognizer.py  Huấn luyện, hiệu chỉnh ngưỡng, phân loại
│   ├── camera_stream.py    Xử lý luồng camera, nhận diện nền
│   ├── live_camera.py      Component camera trên trình duyệt
│   ├── auth.py             Đăng nhập
│   ├── backup.py           Sao lưu, khôi phục
│   ├── research_log.py     Nhật ký đánh giá (không lưu ảnh)
│   └── ...                 Đường dẫn, múi giờ, xuất báo cáo, dữ liệu tổng quan
├── db/                     Mô hình dữ liệu, kết nối, nâng cấp cấu trúc, truy vấn điểm danh
├── ui/                     Giao diện dùng chung và component camera
├── research/               Công cụ đánh giá độ chính xác nhận diện
├── scripts/                Đặt mật khẩu, khôi phục sao lưu, đổi mã học sinh
├── tests/                  Bộ kiểm thử tự động
├── docs/                   Tài liệu kỹ thuật
├── face_recognition/       Mã nguồn thư viện face_recognition (giấy phép MIT)
├── setup/                  Bộ cài đặt một lần bấm cho Windows
├── data/faces/             Ảnh mẫu khuôn mặt (chỉ lưu trên máy, không đưa lên GitHub)
├── requirements.txt        Danh sách thư viện (đã cố định phiên bản)
├── check_environment.py    Kiểm tra môi trường
├── setup_windows.bat       Cài đặt khi máy đã có Python 3.11
├── run.bat                 Khởi chạy ứng dụng
├── INSTALL_WINDOWS.md      Hướng dẫn cài đặt chi tiết
└── CHANGELOG.md            Lịch sử phát triển
```

Các tệp sinh ra khi sử dụng (`attendance.db`, `data/faces/<mã>/`, `models/`, `backups/`, `research_logs/`, `.streamlit/secrets.toml`) chỉ nằm trên máy và được loại trừ khỏi GitHub.

## 8. Quy trình nhận diện khuôn mặt

1. **Thu nhận ảnh:** khung hình từ camera trình duyệt, tự cắt theo tỷ lệ thực của camera (hỗ trợ ảnh dọc trên điện thoại).
2. **Phát hiện khuôn mặt:** Haar Cascade xác định vị trí khuôn mặt trong khung hình.
3. **Chuẩn hóa:** cắt vùng mặt kích thước 200×200, loại ảnh quá tối hoặc thiếu tương phản.
4. **Trích xuất đặc trưng:** mạng ResNet của dlib tạo vector 128 chiều.
5. **Phân loại:** so sánh với vector của học sinh đã đăng ký bằng K-NN có trọng số. Kết quả chỉ được chấp nhận khi đồng thời thỏa mãn ba điều kiện:
   - khoảng cách nhỏ hơn ngưỡng riêng của học sinh đó (giới hạn 0,44–0,48);
   - học sinh gần thứ hai cách xa ít nhất 0,04;
   - đạt đa số phiếu K-NN.
6. **Kết luận:** thỏa mãn → trả về mã học sinh; không thỏa mãn → "Không nhận diện được", không tạo bản ghi.

## 9. Quy trình điểm danh vào và ra về

| Bước | Điểm danh vào | Điểm danh ra về |
|---|---|---|
| 1 | Chọn buổi học, bấm **ĐIỂM DANH VÀO** | Bấm **ĐIỂM DANH RA VỀ** |
| 2 | Camera tự bật, nhận diện liên tục | Camera tự bật, nhận diện liên tục |
| 3 | Cùng một học sinh được nhận ra ở 2 lần liên tiếp (trong 8 giây, khung hình có đúng 1 khuôn mặt) | Như điểm danh vào |
| 4 | Ghi lượt vào → "ĐIỂM DANH VÀO THÀNH CÔNG" | Kiểm tra đã có lượt vào → ghi lượt ra → "ĐIỂM DANH RA VỀ THÀNH CÔNG" |

Quy tắc bảo đảm dữ liệu:

- Mỗi học sinh có tối đa một lượt vào và một lượt ra trong mỗi buổi. Lượt lặp lại hiển thị "HỌC SINH ĐÃ ĐIỂM DANH" và không tạo bản ghi mới.
- Lượt ra chỉ được ghi khi đã có lượt vào; nếu chưa có, hệ thống báo "CHƯA CÓ DỮ LIỆU ĐIỂM DANH VÀO".
- Chống ghi trùng ở hai lớp: kiểm tra trước khi ghi và chỉ mục duy nhất trong cơ sở dữ liệu `(mã học sinh, ngày, buổi, lượt vào/ra)`.
- Không ghi điểm danh cho ngày tương lai; học sinh chưa được nhận diện không bị tự động tính vắng.
- Thời gian ghi theo giờ Việt Nam, hiển thị dạng DD/MM/YYYY HH:mm.

Trang **Điểm danh có xác nhận / thủ công** là phương án dự phòng: giáo viên xác nhận từng kết quả nhận diện, ghi thủ công cho học sinh không nhận diện được và điều chỉnh kết quả đã lưu.

## 10. Quản lý học sinh và lớp học

- **Lớp học:** mã lớp, tên lớp, giáo viên chủ nhiệm.
- **Học sinh:** mã học sinh tự sinh (`HS001`, `HS002`…), họ tên, ngày sinh, lớp, trạng thái học tập.
- **Nhập từ Excel:** tệp có cột `Họ và tên`, `Mã lớp` và `Ngày sinh` (tùy chọn).
- **Dữ liệu khuôn mặt:** mỗi học sinh 5–10 ảnh mẫu; có thể xóa ảnh mẫu của một học sinh và huấn luyện lại để loại học sinh đó khỏi mô hình.

## 11. Quản lý dữ liệu

| Dữ liệu | Vị trí lưu |
|---|---|
| Lớp, học sinh, giáo viên, lượt điểm danh | `attendance.db` (SQLite) |
| Ảnh mẫu khuôn mặt | `data/faces/<mã học sinh>/` |
| Vector đặc trưng, ngưỡng nhận diện | `models/` |
| Nhật ký đánh giá nhận diện (không lưu ảnh) | `research_logs/` |
| Bản sao lưu | `backups/` |
| Tài khoản đăng nhập (mật khẩu đã băm) | `.streamlit/secrets.toml` |

Ảnh khuôn mặt và hồ sơ học sinh là dữ liệu cá nhân nhạy cảm. Chỉ thu thập khi có sự đồng ý bằng văn bản của học sinh và cha mẹ hoặc người giám hộ, và chỉ dùng cho mục đích điểm danh, nghiên cứu. Các dữ liệu trên không được đưa lên GitHub hoặc kênh công khai.

## 12. Cài đặt trên Windows

**Yêu cầu:** Windows 10/11 64-bit, kết nối Internet ở lần cài đầu, ổ đĩa trống ít nhất 3 GB. Camera là tùy chọn (có thể tải ảnh thay thế).

**Cách 1 – Bộ cài một lần bấm (khuyến nghị):**

1. Tải mã nguồn dạng ZIP, giải nén vào `C:\SmartAttendance`.
2. Mở thư mục `setup`, chạy `CAI_DAT_SMART_ATTENDANCE.bat`, chọn **Yes** khi Windows hỏi quyền quản trị.
3. Bộ cài tự cài Python 3.11 (bản chính thức, có kiểm tra chữ ký số) nếu máy chưa có, cài thư viện, khởi tạo dữ liệu, đặt tài khoản đăng nhập, tạo lối tắt **Smart Attendance** trên Desktop và mở ứng dụng.

**Cách 2 – Máy đã có Python 3.11:** chạy `setup_windows.bat` một lần.

**Cách 3 – Cài thủ công:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_environment.py --create-dirs --init-db
.\.venv\Scripts\python.exe scripts\set_password.py
```

Hướng dẫn chi tiết và các lỗi thường gặp: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).

## 13. Khởi chạy ứng dụng

- Bấm đúp lối tắt **Smart Attendance** trên Desktop hoặc tệp `run.bat`.
- Trình duyệt mở địa chỉ `http://localhost:8501`; đăng nhập bằng tài khoản đã đặt khi cài.
- Giữ cửa sổ dòng lệnh mở trong khi sử dụng; đóng cửa sổ này để tắt ứng dụng.

Biến môi trường tùy chọn (xem `.env.example`): `SMART_ATTENDANCE_DATA_ROOT`, `SMART_ATTENDANCE_DB`, `SMART_ATTENDANCE_RESEARCH_LOG`.

## 14. Hướng dẫn sử dụng

1. **Quản lý lớp học và giáo viên:** tạo lớp, thêm giáo viên, chọn giáo viên chủ nhiệm.
2. **Quản lý học sinh:** thêm hồ sơ hoặc nhập danh sách từ Excel.
3. **Đăng ký khuôn mặt học sinh:** chọn học sinh, chụp hoặc tải 5–10 ảnh rõ mặt, góc nghiêng nhẹ khác nhau → **Huấn luyện mô hình**.
4. **Điểm danh tự động:** chọn buổi học và camera → **ĐIỂM DANH VÀO** → từng học sinh đứng trước camera 1–2 giây. Cuối buổi chọn **ĐIỂM DANH RA VỀ**. Bấm **Dừng camera** khi kết thúc.
5. **Điểm danh có xác nhận / thủ công:** dùng cho học sinh không nhận diện được hoặc khi cần điều chỉnh kết quả.
6. **Lịch sử điểm danh, Báo cáo chuyên cần:** lọc dữ liệu và xuất CSV, Excel.
7. **Cài đặt:** tạo bản sao lưu định kỳ.

## 15. Sao lưu và khôi phục

- **Trên giao diện:** Cài đặt → **Tạo bản sao lưu ngay**. Bản sao lưu là tệp ZIP gồm cơ sở dữ liệu (chụp nhất quán), ảnh mẫu, mô hình và nhật ký, kèm mã kiểm tra SHA-256.
- **Bằng dòng lệnh:**

  ```powershell
  .\.venv\Scripts\python.exe scripts\restore_backup.py --create
  .\.venv\Scripts\python.exe scripts\restore_backup.py --list
  .\.venv\Scripts\python.exe scripts\restore_backup.py --verify <tệp zip>
  .\.venv\Scripts\python.exe scripts\restore_backup.py <tệp zip>
  ```

- Khôi phục khi ứng dụng đã dừng; hệ thống luôn tạo bản an toàn của dữ liệu hiện tại trước khi khôi phục.
- Khi nâng cấp phiên bản, cấu trúc cơ sở dữ liệu được cập nhật tự động và có bản sao trong `database_backups/`.

Chi tiết: [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## 16. Khắc phục sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Camera không mở, báo chưa được cấp quyền | Cho phép camera trên thanh địa chỉ trình duyệt; đóng ứng dụng khác đang dùng camera; thử Camera 2 |
| Camera trên iPhone không hiện hình | Mở bằng Safari (không mở trong Zalo, Messenger); chạm vào khung camera để bắt đầu |
| Luôn báo "Không nhận diện được" | Kiểm tra học sinh đã có ảnh mẫu và đã huấn luyện mô hình; bảo đảm đủ sáng, mặt nhìn thẳng |
| Báo "Nhiều khuôn mặt" | Chỉ để một học sinh trong khung hình |
| Trình duyệt không tự mở | Mở `http://localhost:8501` bằng Chrome hoặc Edge |
| Quên mật khẩu | Chạy `.\.venv\Scripts\python.exe scripts\set_password.py` để đặt mật khẩu mới |
| Lỗi cài thư viện, lỗi `dlib` | Kiểm tra đang dùng Python 3.11 64-bit; chạy lại bộ cài khi mạng ổn định |
| Lỗi `arange: cannot compute length` | Ứng dụng đang chạy bằng Python khác; luôn khởi chạy bằng `run.bat` |

Kiểm tra môi trường: `.\.venv\Scripts\python.exe check_environment.py`. Danh sách lỗi đầy đủ: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).

## 17. Hướng phát triển

- Phân quyền nhiều tài khoản giáo viên.
- Mã hóa ảnh mẫu và tệp mô hình khi lưu trữ.
- Chống giả mạo bằng ảnh in hoặc màn hình (kiểm tra chuyển động, chớp mắt).
- Tự động xác định đi muộn theo khung giờ của từng buổi học.
- Thử nghiệm bộ phát hiện khuôn mặt dựa trên học sâu, so sánh bằng công cụ đánh giá hiện có.
- Mở rộng thực nghiệm ở nhiều lớp, nhiều điều kiện ánh sáng và thiết bị.

---

### Kiểm thử

```powershell
.\.venv\Scripts\python.exe tests\run_all.py
```

Bộ kiểm thử chạy trên bản sao dữ liệu tạm và tự xác nhận cơ sở dữ liệu thật không bị thay đổi.

### Hạn chế hiện tại

- Một tài khoản quản trị; ảnh mẫu và mô hình chưa được mã hóa.
- Haar Cascade nhạy với góc nghiêng lớn, ánh sáng yếu và khuôn mặt nhỏ ở xa.
- Chưa có chống giả mạo bằng ảnh.
- Các ngưỡng nhận diện được chọn từ thử nghiệm ban đầu, đang được đánh giá có hệ thống bằng công cụ trong `research/`.
- Thiết kế cho quy mô một lớp học với một máy tính; chưa kiểm chứng ở quy mô toàn trường.

### Tác giả và giấy phép

Phạm Hoàng Trung – giáo viên Tin học, Trường THPT Tiên Lữ, tỉnh Hưng Yên. Quá trình phát triển có sử dụng công cụ hỗ trợ lập trình ứng dụng trí tuệ nhân tạo; các thay đổi có công cụ tham gia được ghi nhận trong lịch sử Git.

Tài liệu tham khảo: Viola & Jones (2001), *Rapid object detection using a boosted cascade of simple features*, CVPR; King (2009), *Dlib-ml: A Machine Learning Toolkit*, JMLR 10.

Thư viện bên thứ ba: `face_recognition` (MIT, xem `face_recognition/README_VENDORED.md`), OpenCV (Apache 2.0), Streamlit (Apache 2.0), dlib (Boost Software License), SQLAlchemy (MIT).

© 2026 Phạm Hoàng Trung. Kho mã chưa áp dụng giấy phép mã nguồn mở; việc sử dụng lại cần liên hệ tác giả.
