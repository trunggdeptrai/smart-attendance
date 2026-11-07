# Smart Attendance

Ứng dụng web hỗ trợ giáo viên điểm danh học sinh bằng nhận diện khuôn mặt. Có hai cách điểm danh: **tự động** (chọn ĐIỂM DANH VÀO hoặc ĐIỂM DANH RA VỀ, camera tự bật, nhận diện liên tục và tự ghi khi cùng một học sinh được nhận ra ở nhiều khung hình liên tiếp) và **có xác nhận** (kết quả nhận diện là gợi ý, giáo viên xác nhận từng học sinh). Luôn có phương án điểm danh thủ công và điều chỉnh kết quả. Học sinh không được camera nhận diện **không** bị tự động tính là vắng mặt.

Ứng dụng chạy cục bộ trên một máy tính phổ thông với webcam, không cần Internet; dữ liệu học sinh và ảnh khuôn mặt được lưu trên máy, có đăng nhập, sao lưu/khôi phục và công cụ đánh giá độ chính xác nhận diện.

## Mục lục

- [Tính năng](#tính-năng)
- [Công nghệ và kiến trúc](#công-nghệ-và-kiến-trúc)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt và chạy](#cài-đặt-và-chạy)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Công cụ nghiên cứu và đánh giá](#công-cụ-nghiên-cứu-và-đánh-giá)
- [Sao lưu và khôi phục](#sao-lưu-và-khôi-phục)
- [Kiểm thử](#kiểm-thử)
- [Triển khai](#triển-khai)
- [Cập nhật phiên bản](#cập-nhật-phiên-bản)
- [Bảo mật và quyền riêng tư](#bảo-mật-và-quyền-riêng-tư)
- [Hạn chế hiện tại](#hạn-chế-hiện-tại)
- [Tác giả](#tác-giả)
- [Tài liệu tham khảo và giấy phép](#tài-liệu-tham-khảo-và-giấy-phép)

## Tính năng

| Phân hệ (menu) | Chức năng đã kiểm tra trong mã nguồn |
|---|---|
| Trang tổng quan | Số học sinh, số lớp, có mặt/đi muộn/vắng đã xác nhận; biểu đồ 7 ngày và theo lớp (Plotly) |
| Quản lý học sinh | Thêm/sửa/tìm kiếm, nhập Excel (`Họ và tên`, `Mã lớp`, `Ngày sinh` tùy chọn), xóa mềm hồ sơ |
| Quản lý lớp học và giáo viên | Tạo/cập nhật lớp, hồ sơ giáo viên, giáo viên chủ nhiệm |
| Đăng ký khuôn mặt | Chụp bằng camera trình duyệt hoặc tải ảnh (mỗi ảnh đúng 1 khuôn mặt), lưu ảnh cắt 200×200 vào `data/faces/<mã>/`, huấn luyện lại mô hình; **xóa dữ liệu khuôn mặt của một học sinh** |
| Điểm danh tự động | Hai chế độ ĐIỂM DANH VÀO / ĐIỂM DANH RA VỀ; camera tự bật, nhận diện liên tục, tự ghi vào cơ sở dữ liệu (cần 2 lần nhận diện liên tiếp cùng một học sinh); bảng học sinh đã điểm danh trong buổi, lọc theo lớp, thống kê; âm thanh báo tùy chọn |
| Điểm danh có xác nhận / thủ công | Camera trực tiếp / chụp ảnh / tải ảnh; giáo viên xác nhận từng học sinh; điều chỉnh kết quả; điểm danh thủ công (dự phòng) |
| Lịch sử điểm danh | Lọc theo ngày, lớp, học sinh, trạng thái; xuất CSV/Excel |
| Báo cáo chuyên cần | Theo lớp/ngày/buổi; phân biệt “Chưa ghi nhận” và “Vắng mặt đã xác nhận”; xuất CSV/Excel |
| Đánh giá thực nghiệm | Thống kê từ nhật ký nhận diện thực tế: tỷ lệ khớp, lý do từ chối, thời gian xử lý, quyết định của giáo viên; xem kết quả đánh giá offline |
| Cài đặt | Tình trạng SQLite và mô hình; **tạo/tải bản sao lưu ZIP** |
| Hướng dẫn sử dụng | Hướng dẫn thao tác, quyền camera, quyền riêng tư |

Cơ chế đảm bảo dữ liệu điểm danh:

- **Chống điểm danh trùng:** kiểm tra trước khi ghi và chỉ mục duy nhất `(student_code, attendance_date, session_name, log_type)` trong SQLite.
- **Mỗi học sinh một lượt vào và một lượt ra trong mỗi buổi**; lượt ra cần lượt vào trước; học sinh đã xác nhận vắng không thể ghi lượt ra.
- **Không cho ghi điểm danh cho ngày tương lai** (bổ sung ở phiên bản 1.1).
- **Người không nhận diện được** hiển thị “KHÔNG NHẬN DIỆN ĐƯỢC”, không tạo bản ghi; khung hình có nhiều khuôn mặt không được ghi.
- **Giờ Việt Nam** (Asia/Ho_Chi_Minh) cho thời điểm ghi và ngày điểm danh, kể cả khi máy chủ (Streamlit Cloud) chạy giờ UTC.

Hai trang `pages/6_Face_Detection.py` và `pages/7_Face_Recognition.py` là trang kiểm tra cũ dùng camera phía máy chủ (OpenCV); hiện **không có trong menu**.

## Công nghệ và kiến trúc

| Thành phần | Công nghệ (phiên bản đã kiểm thử) |
|---|---|
| Ngôn ngữ | Python 3.11.x 64-bit (phiên bản triển khai được ghim) |
| Giao diện web | Streamlit 1.55.0 (đa trang, `st.navigation`) + component camera HTML/JS (`ui/live_camera/`) |
| Phát hiện khuôn mặt | OpenCV 4.13 – Haar Cascade `haarcascade_frontalface_default.xml` |
| Trích xuất đặc trưng | `face_recognition` 1.3.0 (mã MIT sao chép trong `face_recognition/`) / dlib 20.0.1 bản dựng sẵn `dlib-bin` – vector 128 chiều (ResNet của dlib) |
| Phân loại | K-NN có trọng số khoảng cách (K=3) + ngưỡng riêng từng học sinh + kiểm tra khoảng cách biên + đa số phiếu (`core/face_recognizer.py`) |
| Lưu trữ | SQLite + SQLAlchemy 2.x; ảnh mẫu dạng tệp; mô hình dạng `pickle` + JSON |
| Báo cáo | pandas 2.3.3, openpyxl 3.1.5, Plotly; NumPy 2.2.6 (giữ bản tương thích OpenCV/Python 3.11) |

```text
Trình duyệt (camera)  ->  Streamlit pages/  ->  core/ (phát hiện, mã hóa, phân loại, xuất báo cáo, sao lưu, nhật ký)
                                         \->  db/   (SQLAlchemy: lớp, học sinh, giáo viên, lượt điểm danh)
Dữ liệu: attendance.db · data/faces/<mã>/ · models/ · backups/ · research_logs/ · research_results/
```

Chi tiết: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · thuật toán: [docs/ALGORITHM.md](docs/ALGORITHM.md).

### Mô hình dữ liệu

Cấu trúc dữ liệu được tổ chức theo nghiệp vụ quản lý học sinh trong nhà trường:

| Nhóm dữ liệu | Lưu trữ |
|---|---|
| Học sinh | Bảng `students` – mã học sinh dạng `HS001`, `HS002`… (tự sinh), họ tên, ngày sinh, lớp, trạng thái học tập |
| Lớp học, giáo viên | Bảng `classes` (mã lớp, tên lớp, GVCN) và `teachers` |
| Dữ liệu khuôn mặt | Ảnh mẫu `data/faces/<mã học sinh>/`; vector đặc trưng và ngưỡng nhận diện trong `models/` |
| Điểm danh và lịch sử | Bảng `attendance_logs` – học sinh, lớp, ngày, buổi, lượt vào/ra, trạng thái, phương thức (nhận diện/thủ công), khoảng cách nhận diện |
| Tài khoản hệ thống | Một tài khoản quản trị, mật khẩu băm trong `.streamlit/secrets.toml` hoặc Secrets của Streamlit Cloud |

Các thành phần dữ liệu kế thừa từ phiên bản nền đã được rà soát và điều chỉnh để phù hợp với mô hình quản lý học sinh; chi tiết từng bảng (kể cả bảng kỹ thuật dùng cho khóa ngoại) trong [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Cấu trúc thư mục

```text
.
├── app.py                    # Điểm khởi chạy: đăng nhập, khởi tạo DB, menu điều hướng
├── core/
│   ├── auth.py               # Đăng nhập (mật khẩu băm PBKDF2)
│   ├── paths.py              # Đường dẫn dữ liệu (ghi đè bằng biến môi trường)
│   ├── dataframes.py         # Bảng có schema cột ổn định
│   ├── dashboard_data.py     # Dữ liệu trang tổng quan
│   ├── face_detect.py        # Phát hiện khuôn mặt (Haar Cascade)
│   ├── face_dataset.py       # Đọc ảnh mẫu, tạo vector đặc trưng khi huấn luyện
│   ├── face_recognizer.py    # Huấn luyện, hiệu chỉnh ngưỡng, phân loại, đo thời gian
│   ├── save_face.py          # Cắt/lưu/xóa ảnh mẫu
│   ├── camera_stream.py      # Luồng camera, nhận diện nền, làm mượt khung
│   ├── live_camera.py        # Component camera trình duyệt
│   ├── attendance_export.py  # Xuất Excel
│   ├── backup.py             # Sao lưu/khôi phục ZIP
│   └── research_log.py       # Nhật ký nghiên cứu (không lưu ảnh)
├── db/                       # models.py, session.py (migration), database.py, attendance_repo.py
├── pages/                    # Các trang giao diện
├── research/
│   └── evaluate_recognition.py   # Đánh giá offline: độ chính xác, nhận nhầm, thời gian, quét ngưỡng
├── scripts/
│   ├── set_password.py       # Đặt tài khoản đăng nhập
│   ├── rename_student_code.py # Đổi mã học sinh đồng bộ toàn bộ dữ liệu (có sao lưu)
│   └── restore_backup.py     # Tạo/kiểm tra/khôi phục bản sao lưu
├── face_recognition/         # Mã nguồn thư viện face_recognition (MIT, bên thứ ba)
├── tests/                    # Kiểm thử; chạy bằng tests/run_all.py (cô lập dữ liệu)
├── docs/                     # Tài liệu kiến trúc, thuật toán, nghiên cứu, sao lưu, triển khai
├── ui/                       # CSS và component camera
├── requirements.txt          # Phụ thuộc (đã ghim phiên bản)
├── requirements-dataset.txt  # Chỉ cho script tải dataset tùy chọn
├── check_environment.py      # Kiểm tra môi trường trước khi chạy
├── setup/                    # Bộ cài 1 lần bấm cho Windows (tự cài Python, thư viện, lối tắt)
├── setup_windows.bat         # Cài đặt một lần trên Windows (khi đã có Python 3.11)
├── INSTALL_WINDOWS.md        # Hướng dẫn cài đặt Windows chi tiết
├── .env.example              # Biến môi trường tùy chọn
├── run.bat                   # Chạy ứng dụng trên Windows
└── (sinh ra khi chạy, đã .gitignore) attendance.db, data/faces/, models/, backups/, research_logs/, research_results/
```

## Yêu cầu hệ thống

- Windows 10/11 (đã kiểm thử Windows 11).
- Python **3.11.x 64-bit** (các phiên bản khác chưa được xác nhận). `dlib` dùng bản dựng sẵn `dlib-bin` nên **không cần** Visual Studio Build Tools hay CMake.
- Camera (tùy chọn – có thể tải ảnh lên thay thế). Camera trình duyệt cần `localhost` hoặc HTTPS.
- Không cần Internet khi chạy: mọi xử lý nhận diện thực hiện cục bộ.

## Cài đặt và chạy

```powershell
git clone https://github.com/trunggdeptrai/smart-attendance.git
cd smart-attendance
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python check_environment.py
python -m streamlit run app.py
```

Cách nhanh nhất trên Windows (dành cho học sinh): giải nén ZIP → mở thư mục `setup` → bấm đúp `CAI_DAT_SMART_ATTENDANCE.bat` → chọn **Yes** khi Windows hỏi quyền Administrator. Bộ cài tự cài Python 3.11 (bản chính thức từ python.org, có kiểm tra chữ ký số) nếu máy chưa có, cài thư viện, tạo cơ sở dữ liệu, hỏi mật khẩu, tạo lối tắt **Smart Attendance** trên Desktop và mở ứng dụng. Xem `setup/HUONG_DAN_CAI_DAT.txt`.

Nếu đã có Python 3.11: chạy `setup_windows.bat` một lần rồi `run.bat`. Hướng dẫn chi tiết (Python 3.11, môi trường ảo, lỗi `dlib`, lỗi `arange: cannot compute length` do sai phiên bản NumPy): [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).

**Đặt tài khoản đăng nhập** (bắt buộc, một lần): `python scripts/set_password.py` → nhập tên (mặc định `admin`) và mật khẩu. Mật khẩu được lưu dạng băm trong `.streamlit/secrets.toml` (không đưa lên GitHub).

Mở `http://localhost:8501` và đăng nhập. Lần chạy đầu ứng dụng tự tạo `attendance.db` rỗng; tạo lớp → thêm học sinh → đăng ký khuôn mặt → huấn luyện mô hình.

Biến môi trường tùy chọn (xem `.env.example`; đặt trong PowerShell bằng `$env:TEN="giá trị"` trước khi chạy): `SMART_ATTENDANCE_DATA_ROOT`, `SMART_ATTENDANCE_DB`, `SMART_ATTENDANCE_RESEARCH_LOG`.

## Hướng dẫn sử dụng

0. **Đăng nhập** bằng tài khoản quản trị; bấm **Đăng xuất** ở thanh bên khi dùng xong.
1. **Quản lý lớp học và giáo viên:** tạo lớp, thêm giáo viên, chọn GVCN.
2. **Quản lý học sinh:** thêm hồ sơ hoặc nhập Excel.
3. **Đăng ký khuôn mặt:** chọn học sinh, chụp/tải 5–10 ảnh rõ mặt, nhiều góc nhẹ → **Huấn luyện mô hình**.
4. **Điểm danh tự động:** chọn buổi, camera → bấm **ĐIỂM DANH VÀO** (hoặc **ĐIỂM DANH RA VỀ** khi tan học) → từng học sinh đứng trước camera 1–2 giây, hệ thống tự ghi và báo kết quả. Bấm **Dừng camera** khi xong. Học sinh không nhận diện được → dùng trang **Điểm danh có xác nhận / thủ công**.
5. **Lịch sử / Báo cáo:** lọc và xuất CSV/Excel.
6. **Đánh giá thực nghiệm:** xem số liệu được ghi tự động trong quá trình sử dụng.
7. **Cài đặt:** tạo bản sao lưu định kỳ.

## Công cụ nghiên cứu và đánh giá

- **Nhật ký tự động** (`research_logs/`): mỗi lần nhận diện ghi mã dự đoán, khoảng cách, ngưỡng, lý do từ chối, thời gian xử lý; mỗi lần giáo viên xác nhận/ghi thủ công/điều chỉnh. Không lưu ảnh hay vector.
- **Đánh giá offline** (`research/evaluate_recognition.py`): so sánh thuật toán của ứng dụng với nhóm đối chứng 1-NN ngưỡng 0,6 trên cùng tập ảnh kiểm thử; tính tỷ lệ nhận đúng, nhận nhầm, từ chối sai, chấp nhận sai, thời gian; quét ngưỡng 0,30–0,70; tự chặn ảnh kiểm thử trùng ảnh huấn luyện.

```powershell
python -m research.evaluate_recognition --loo                         # bỏ-ra-một trên ảnh mẫu đã đăng ký
python -m research.evaluate_recognition --eval-dir D:\anh_kiem_thu --tag lan1
```

Hướng dẫn tổ chức ảnh kiểm thử và ý nghĩa chỉ số: [docs/RESEARCH_TOOLKIT.md](docs/RESEARCH_TOOLKIT.md).

## Sao lưu và khôi phục

- Giao diện: **Cài đặt → Tạo bản sao lưu ngay** → tệp `backups/smart_attendance_backup_<thời điểm>.zip` (DB chụp nhất quán bằng SQLite Backup API + ảnh mẫu + mô hình + nhật ký, kèm SHA-256).
- Dòng lệnh: `python scripts/restore_backup.py --create` · `--list` · `--verify <zip>` · `<zip>` (khôi phục; luôn tạo bản an toàn trước).
- Khôi phục khi **ứng dụng đã dừng**. Chi tiết: [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## Kiểm thử

```powershell
python tests/run_all.py
```

Trình chạy sao chép dữ liệu sang thư mục tạm và đặt `SMART_ATTENDANCE_DATA_ROOT`, nên kiểm thử **không ghi vào `attendance.db` thật**. Kết quả gần nhất: 13/13 tệp đạt (05/11/2026, Windows 11, Python 3.11.9).

## Triển khai

Khuyến nghị: chạy **cục bộ trên máy tính của giáo viên** (không cần Internet, dữ liệu sinh trắc học không rời khỏi máy). Bản demo trực tuyến chạy trên Streamlit Community Cloud. Hướng dẫn: [docs/DEPLOY.md](docs/DEPLOY.md).

## Cập nhật phiên bản

1. Tạo bản sao lưu (Cài đặt hoặc `python scripts/restore_backup.py --create`).
2. Dừng ứng dụng, `git pull`, `python -m pip install -r requirements.txt`.
3. Khởi động lại; schema DB được nâng cấp tự động (có bản sao DB trong `database_backups/`).
4. Xem [CHANGELOG.md](CHANGELOG.md).

## Bảo mật và quyền riêng tư

- Ảnh khuôn mặt, vector đặc trưng và hồ sơ học sinh là **dữ liệu cá nhân nhạy cảm**. Chỉ thu thập khi có sự đồng ý bằng văn bản (với học sinh chưa thành niên: cha mẹ/người giám hộ) và đúng mục đích điểm danh/nghiên cứu.
- `attendance.db`, `data/faces/`, `models/`, `backups/`, `research_logs/`, `research_results/` đã được loại trừ trong `.gitignore`. **Không** đưa lên GitHub hoặc kênh công khai.
- Có chức năng xóa ảnh mẫu của từng học sinh và huấn luyện lại để loại vector khỏi mô hình.
- **Đăng nhập bắt buộc**: một tài khoản quản trị, mật khẩu băm PBKDF2-SHA256 có salt, khóa 60 giây sau 5 lần sai; chưa đăng nhập thì mọi đường dẫn trang chỉ hiện form đăng nhập. Mật khẩu không có trong mã nguồn (đặt bằng `scripts/set_password.py` hoặc Secrets của Streamlit Cloud).
- Streamlit mặc định chỉ nghe `127.0.0.1`. Chưa có phân quyền nhiều người dùng – không mở ra mạng trường khi chưa cần thiết.
- Mô hình lưu bằng `pickle`: chỉ nạp tệp mô hình do chính ứng dụng tạo.

## Hạn chế hiện tại

- Chỉ có một tài khoản quản trị, chưa phân quyền nhiều giáo viên; tệp mô hình và ảnh mẫu chưa được mã hóa khi lưu.
- Phát hiện khuôn mặt bằng Haar Cascade nhạy với góc nghiêng lớn, ánh sáng yếu, khuôn mặt nhỏ.
- Chưa có chống giả mạo (ảnh in, màn hình điện thoại).
- Ngưỡng 0,48 và các tham số K-NN được chọn thủ công; **chưa được kiểm chứng bằng thực nghiệm có hệ thống** – đang được đánh giá bằng công cụ trong `research/`.
- Chỉ thiết kế cho một máy, một camera, dữ liệu cục bộ; chưa kiểm chứng ở quy mô toàn trường.

## Tác giả

Phạm Hoàng Trung – giáo viên Tin học, Trường THPT Tiên Lữ (Hưng Yên).

Phần mềm được phát triển với sự hỗ trợ của trợ lý lập trình AI Claude (Anthropic); từ phiên bản 1.1, các commit có AI tham gia được ghi nhận bằng dòng `Co-Authored-By` trong lịch sử Git.
## Tài liệu tham khảo và giấy phép

- King, D. E. (2009). Dlib-ml: A Machine Learning Toolkit. *Journal of Machine Learning Research*, 10, 1755–1758.
- Viola, P., & Jones, M. (2001). Rapid object detection using a boosted cascade of simple features. *CVPR 2001*.
- Thư viện `face_recognition` (Adam Geitgey, giấy phép MIT – 2 tệp được sao chép nguyên bản vào `face_recognition/` kèm LICENSE, xem `face_recognition/README_VENDORED.md`); OpenCV (Apache 2.0); Streamlit (Apache 2.0); dlib (Boost Software License); SQLAlchemy (MIT).

© 2026 Phạm Hoàng Trung. Kho mã chưa áp dụng giấy phép mã nguồn mở; muốn sử dụng lại, vui lòng liên hệ tác giả. Các thư viện bên thứ ba tuân theo giấy phép riêng của từng thư viện.
