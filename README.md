# Smart Attendance

Smart Attendance là ứng dụng web hỗ trợ nhà trường quản lý lớp, học sinh và ghi nhận chuyên cần bằng nhận diện khuôn mặt. Giáo viên có thể kiểm tra và xác nhận từng kết quả trước khi lưu; ứng dụng cũng hỗ trợ ghi nhận thủ công khi cần.

Phần mềm hướng đến giáo viên, nhân viên quản lý nhà trường và người muốn cài đặt, tìm hiểu hoặc phát triển dự án. Ứng dụng giúp tập trung hồ sơ lớp và học sinh, giảm thao tác ghi chép điểm danh, đồng thời hỗ trợ tra cứu lịch sử và tổng hợp báo cáo.

> Nhận diện khuôn mặt chỉ hỗ trợ đối chiếu. Giáo viên cần kiểm tra kết quả; ứng dụng không tự động coi học sinh chưa được nhận diện là vắng mặt.

## Mục lục

- [Giới thiệu dự án](#giới-thiệu-dự-án)
- [Tính năng chính](#tính-năng-chính)
- [Giao diện phần mềm](#giao-diện-phần-mềm)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Lưu trữ và sao lưu dữ liệu](#lưu-trữ-và-sao-lưu-dữ-liệu)
- [Khắc phục lỗi thường gặp](#khắc-phục-lỗi-thường-gặp)
- [Bảo mật và quyền riêng tư](#bảo-mật-và-quyền-riêng-tư)
- [Giới hạn và hướng phát triển](#giới-hạn-và-hướng-phát-triển)
- [Đóng góp và giấy phép](#đóng-góp-và-giấy-phép)

## Giới thiệu dự án

Smart Attendance là sản phẩm do tôi trực tiếp nghiên cứu, xây dựng, phát triển và hoàn thiện nhằm hỗ trợ công tác điểm danh học sinh. Từ việc phân tích yêu cầu thực tế, tôi phát triển các chức năng quản lý lớp, giáo viên và học sinh; tích hợp nhận diện khuôn mặt; điều chỉnh quy trình xác nhận điểm danh; và hoàn thiện chức năng tra cứu, báo cáo. Ứng dụng cung cấp giao diện trên trình duyệt, lưu dữ liệu cục bộ bằng SQLite cùng các tệp ảnh và dữ liệu mô hình nhận diện.

## Tính năng chính

- **Tổng quan:** hiển thị số học sinh, số lớp, số lượt có mặt, đi muộn và vắng đã xác nhận; có biểu đồ theo 7 ngày gần nhất, biểu đồ theo lớp và danh sách lượt điểm danh mới nhất.
- **Quản lý học sinh:** thêm, tìm kiếm, cập nhật hồ sơ và trạng thái học tập; nhập danh sách từ Excel với các cột bắt buộc `Họ và tên`, `Mã lớp` và cột tùy chọn `Ngày sinh`.
- **Quản lý lớp học và giáo viên:** tạo/cập nhật lớp, quản lý hồ sơ giáo viên và phân công giáo viên chủ nhiệm. Trường tên tài khoản trong hồ sơ giáo viên chỉ là thông tin; ứng dụng chưa có đăng nhập.
- **Đăng ký khuôn mặt:** chụp ảnh bằng camera hoặc tải ảnh JPG/PNG lên cho học sinh đã có hồ sơ. Mỗi ảnh đăng ký tải lên phải có đúng một khuôn mặt. Có thể huấn luyện lại dữ liệu nhận diện sau khi thêm ảnh.
- **Điểm danh:** chọn lớp, ngày và buổi học; sử dụng camera trực tiếp, chụp ảnh bằng camera trình duyệt hoặc tải ảnh JPG/PNG. Có lượt vào và lượt ra; kết quả nhận diện cần được giáo viên xác nhận trước khi ghi.
- **Điểm danh thủ công:** ghi nhận có mặt, đi muộn hoặc vắng mặt cho lượt vào; lượt ra cho phép ghi nhận có mặt hoặc đi muộn. Hệ thống yêu cầu có lượt vào trước khi ghi lượt ra.
- **Điều chỉnh kết quả:** trang điểm danh có mục điều chỉnh thủ công các kết quả đã xác nhận.
- **Lịch sử điểm danh:** lọc theo ngày, lớp, học sinh và trạng thái; xem giờ vào/ra và tải dữ liệu CSV hoặc Excel.
- **Báo cáo chuyên cần:** xem sĩ số và trạng thái theo lớp, ngày, buổi và học sinh; phân biệt “Chưa ghi nhận” với “Vắng mặt đã xác nhận”; xuất CSV hoặc Excel.
- **Cài đặt và hướng dẫn:** xem tình trạng kết nối SQLite, tình trạng tệp mô hình và hướng dẫn sử dụng, quyền camera, quyền riêng tư.

## Giao diện phần mềm

Thanh điều hướng gồm các trang chính:

| Nhóm | Trang |
|---|---|
| Tổng quan | Trang tổng quan |
| Quản lý nhà trường | Quản lý học sinh; Quản lý lớp học và giáo viên |
| Điểm danh | Điểm danh nhận diện khuôn mặt; Đăng ký khuôn mặt học sinh; Lịch sử điểm danh; Báo cáo chuyên cần |
| Hệ thống | Cài đặt; Hướng dẫn sử dụng |

Repository hiện chưa có ảnh chụp màn hình giao diện. Nếu bổ sung ảnh, hãy đặt ảnh đã loại bỏ thông tin nhận dạng tại `docs/images/` rồi cập nhật mục này. Không dùng ảnh học sinh, ảnh khuôn mặt hoặc dữ liệu thật.

## Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| Python | Ngôn ngữ ứng dụng |
| Streamlit 1.55.0 | Giao diện web và điều hướng trang |
| OpenCV (`opencv-python` 4.13.0.92) | Đọc và xử lý ảnh, làm việc với camera |
| `face-recognition` và dlib | Phát hiện, mã hóa và đối chiếu khuôn mặt |
| SQLite và SQLAlchemy 2.x | Lưu trữ và truy vấn dữ liệu |
| NumPy, pandas | Xử lý dữ liệu ảnh và bảng điểm danh |
| Plotly | Biểu đồ ở trang tổng quan |
| openpyxl | Đọc tệp Excel và tạo báo cáo `.xlsx` |

Các phiên bản phụ thuộc được khai báo trong [`requirements.txt`](requirements.txt). `dlib` không được ghim phiên bản trong tệp này và có thể cần công cụ biên dịch tùy hệ điều hành.

## Cấu trúc thư mục

```text
.
├── README.md
├── app.py
├── .dockerignore
├── .gitignore
├── requirements.txt
├── run.bat
├── Dockerfile
├── docker-compose.yml
├── download_dataset.py
├── .streamlit/
│   └── config.toml
├── core/
│   ├── attendance_export.py
│   ├── camera_stream.py
│   ├── face_dataset.py
│   ├── face_detect.py
│   ├── face_recognizer.py
│   ├── live_camera.py
│   └── save_face.py
├── db/
│   ├── attendance_repo.py
│   ├── database.py
│   ├── models.py
│   └── session.py
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Employees.py
│   ├── 3_Register_Face.py
│   ├── 4_Attendance.py
│   ├── 5_History.py
│   ├── 6_Face_Detection.py
│   ├── 7_Face_Recognition.py
│   ├── 8_Classes.py
│   ├── 9_Attendance_Report.py
│   ├── 10_Settings.py
│   └── 11_Guide.py
├── ui/
│   ├── live_camera/
│   │   └── index.html
│   └── styles.py
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_df.py
│   ├── test_phase1_attendance_toast.py
│   ├── test_phase1_streaming.py
│   ├── test_phase2.py
│   ├── test_phase2_attendance.py
│   └── test_phase3_face_recognition.py
├── data/
│   └── faces/
├── models/
│   ├── face_encodings.pkl
│   ├── label_map.json
│   └── model_metadata.json
├── database_backups/
└── attendance.db
```

- `app.py` khởi tạo ứng dụng, cơ sở dữ liệu và các trang điều hướng.
- `pages/` chứa các trang giao diện; `core/` chứa xử lý camera, ảnh, nhận diện và xuất báo cáo.
- `db/` chứa mô hình dữ liệu, truy cập cơ sở dữ liệu và các thao tác nghiệp vụ.
- `data/faces/` lưu ảnh mẫu theo mã học sinh; `models/` lưu dữ liệu nhận diện được tạo khi huấn luyện.
- `attendance.db` là cơ sở dữ liệu SQLite. `database_backups/` lưu bản sao được tạo trước một số lần chuyển đổi schema.
- `tests/` chứa các kiểm thử của dự án.

Các thư mục dữ liệu và tệp cơ sở dữ liệu có thể được tạo hoặc cập nhật khi chạy ứng dụng; không đưa dữ liệu cá nhân vào repository công khai.

## Yêu cầu hệ thống

- **Hệ điều hành:** hướng dẫn cài đặt trực tiếp bên dưới dành cho Windows. Dockerfile sử dụng ảnh Python Linux `python:3.11-slim`; dự án chưa công bố ma trận hệ điều hành được kiểm thử.
- **Python:** Python 3.11 là phiên bản được dùng trong Dockerfile và là lựa chọn nên dùng khi cài trực tiếp. `requirements.txt` không khai báo khoảng phiên bản Python được hỗ trợ chính thức.
- **Thư viện:** cài các gói trong `requirements.txt`. Nếu cài `dlib` thất bại, môi trường có thể cần CMake và công cụ biên dịch C++ tương thích.
- **Camera:** cần camera nếu muốn chụp ảnh trực tiếp hoặc dùng camera trực tiếp. Có thể tải ảnh JPG/PNG thay thế ở các luồng có hỗ trợ tải ảnh.
- **Trình duyệt:** cần cho phép quyền camera khi chụp bằng camera của trình duyệt. Quyền truy cập camera trên trình duyệt thường cần `localhost` hoặc HTTPS.
- **Quyền ghi:** tài khoản chạy ứng dụng cần quyền ghi dữ liệu trong thư mục dự án để tạo/cập nhật database, ảnh mẫu và mô hình.

## Cài đặt

### Windows và VS Code

1. Tải mã nguồn dạng ZIP từ trang GitHub hoặc clone bằng URL repository do chủ dự án cung cấp.
2. Giải nén nếu tải ZIP. Trong VS Code, chọn **File → Open Folder...** và mở thư mục chứa `app.py`.
3. Mở terminal PowerShell trong VS Code và tạo môi trường ảo:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Cài dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Khởi chạy ứng dụng từ thư mục dự án:

   ```powershell
   python -m streamlit run app.py
   ```

6. Mở `http://localhost:8501` trong trình duyệt. Theo cấu hình hiện tại, ứng dụng chạy trên máy cục bộ.

Trên Windows, có thể chạy `run.bat` thay cho lệnh khởi chạy ở bước 5. Tập lệnh ưu tiên Python trong `.venv`; nếu không có thì dùng `python` trên `PATH`.

### Chạy bằng Docker (tùy chọn)

Repository có `Dockerfile` và `docker-compose.yml`. Khi đã cài Docker Desktop, chạy từ thư mục dự án:

```powershell
docker compose up --build -d
```

Sau đó mở `http://localhost:8501`. Cấu hình Compose hiện chỉ công bố cổng trên máy cục bộ. Camera OpenCV gắn trực tiếp với máy chủ/container cần cấu hình chuyển tiếp thiết bị; Compose mặc định không bật cấu hình thiết bị camera.

## Hướng dẫn sử dụng

1. **Khởi động:** chạy ứng dụng theo mục [Cài đặt](#cài-đặt), sau đó mở trang tổng quan.
2. **Tạo danh mục:** vào **Quản lý lớp học và giáo viên**, tạo lớp, thêm hồ sơ giáo viên và chọn giáo viên chủ nhiệm. Sau đó vào **Quản lý học sinh** để thêm hồ sơ. Có thể nhập danh sách Excel với cột `Họ và tên`, `Mã lớp`; `Ngày sinh` là tùy chọn.
3. **Đăng ký khuôn mặt:** vào **Đăng ký khuôn mặt học sinh**, chọn học sinh và chụp ảnh hoặc tải ảnh JPG/PNG lên. Với ảnh tải lên, mỗi tệp cần có đúng một khuôn mặt.
4. **Huấn luyện mô hình:** sau khi thêm ảnh, chọn **Huấn luyện mô hình** trên trang đăng ký khuôn mặt để cập nhật dữ liệu nhận diện.
5. **Điểm danh:** vào **Điểm danh nhận diện khuôn mặt**, chọn lớp, ngày và buổi học. Chọn camera trực tiếp, chụp bằng camera trình duyệt hoặc tải ảnh lên. Với chế độ ảnh, chọn lượt vào hoặc lượt ra.
6. **Kiểm tra và xác nhận:** đối chiếu mã học sinh, họ tên, lớp và kết quả nhận diện; chọn trạng thái rồi xác nhận từng học sinh. Nếu nhận diện không phù hợp, có thể ghi nhận thủ công. Chỉ chọn vắng mặt khi đã xác minh; kết quả không nhận diện không tự tạo trạng thái vắng. Lượt ra cần có lượt vào trước.
7. **Tra cứu và xuất:** dùng **Lịch sử điểm danh** để lọc và xuất CSV/Excel; dùng **Báo cáo chuyên cần** để xem danh sách theo lớp, ngày, buổi và học sinh, bao gồm cả trạng thái chưa ghi nhận.
8. **Sao lưu:** dừng ứng dụng và sao lưu các tệp/thư mục nêu tại [Lưu trữ và sao lưu dữ liệu](#lưu-trữ-và-sao-lưu-dữ-liệu).

## Lưu trữ và sao lưu dữ liệu

| Dữ liệu | Vị trí |
|---|---|
| Hồ sơ học sinh, lớp, giáo viên và lịch sử điểm danh | `attendance.db` ở thư mục gốc dự án |
| Ảnh mẫu khuôn mặt | `data/faces/<mã_học_sinh>/` |
| Embeddings, nhãn và metadata của mô hình | `models/` |
| Bản sao trước khi ứng dụng chuyển đổi schema database | `database_backups/` |

Để sao lưu đầy đủ, hãy dừng ứng dụng rồi sao chép `attendance.db`, `data/faces/` và `models/` vào nơi lưu trữ riêng tư, có kiểm soát quyền truy cập. Có thể giữ thêm `database_backups/` để lưu các bản sao schema đã tạo trước đó. Sao lưu database cùng ảnh và mô hình tại cùng một thời điểm để chúng nhất quán.

Ứng dụng tự tạo bản sao database trong `database_backups/` khi phát hiện cần thực hiện một số chuyển đổi schema. Đây không phải chức năng sao lưu định kỳ, không bao gồm ảnh hoặc mô hình và giao diện hiện không có nút khôi phục.

**Khôi phục thủ công:** dừng ứng dụng; giữ riêng bản dữ liệu hiện tại trước khi thay thế; chép `attendance.db`, `data/faces/` và `models/` từ cùng một bộ sao lưu vào đúng vị trí trong thư mục dự án; sau đó khởi động lại và kiểm tra dữ liệu. Không xóa hoặc ghi đè bản duy nhất đang có. Nếu chuyển giữa các phiên bản có schema khác nhau, hãy sao lưu trước và xác minh khả năng tương thích trước khi sử dụng dữ liệu.

## Khắc phục lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| Không mở được camera | Cho phép quyền camera của trình duyệt; kiểm tra camera đang dùng và chọn đúng camera trong ứng dụng. Với camera trực tiếp qua OpenCV, kết nối phải khả dụng trên máy chạy ứng dụng. Đóng ứng dụng khác đang chiếm camera rồi thử lại. |
| Camera trình duyệt không hoạt động | Truy cập qua `localhost` hoặc HTTPS và cấp quyền camera cho trang. Nếu không dùng được camera, tải ảnh JPG/PNG lên ở luồng hỗ trợ tải ảnh. |
| `streamlit` không được nhận diện hoặc thiếu module | Kích hoạt đúng `.venv`, cài lại bằng `python -m pip install -r requirements.txt`, rồi chạy `python -m streamlit run app.py` trong thư mục dự án. |
| Không cài được `dlib` | Kiểm tra phiên bản Python và môi trường biên dịch C++/CMake của hệ điều hành. `dlib` không có phiên bản ghim trong `requirements.txt`; cần dùng bộ công cụ hoặc gói cài tương thích với môi trường của bạn. |
| Chưa có mô hình nhận diện | Đăng ký ảnh khuôn mặt hợp lệ cho học sinh rồi chọn **Huấn luyện mô hình**. Kiểm tra ứng dụng có thể ghi dữ liệu vào `models/`. |
| Không phát hiện hoặc nhận diện sai | Dùng ảnh rõ, đủ sáng, khuôn mặt nhìn thấy rõ; đăng ký ảnh mẫu đúng học sinh và huấn luyện lại. Giáo viên cần xác nhận kết quả hoặc dùng điểm danh thủ công. |
| Không có dữ liệu hoặc lỗi database | Khi khởi động, ứng dụng gọi hàm khởi tạo database và schema. Kiểm tra quyền ghi thư mục dự án và tình trạng `attendance.db`; nếu tệp hiện có bị lỗi, dừng ứng dụng và khôi phục từ một bản sao phù hợp thay vì xóa database. |
| Không xuất được báo cáo | Kiểm tra bộ lọc có dữ liệu phù hợp. Kiểm tra lỗi cài đặt dependencies nếu thao tác đọc Excel hoặc tạo tệp Excel thất bại. |

## Bảo mật và quyền riêng tư

- Ảnh khuôn mặt, embeddings và hồ sơ học sinh là dữ liệu nhạy cảm. Chỉ thu thập và sử dụng khi có căn cứ, sự đồng ý phù hợp và tuân thủ quy định áp dụng tại đơn vị.
- Không commit hoặc công khai `attendance.db`, `data/faces/`, `models/` hay các bản sao lưu chứa dữ liệu thật lên GitHub. Kiểm tra nội dung trước khi chia sẻ repository hoặc bản sao lưu.
- Lưu dữ liệu và bản sao lưu tại nơi riêng tư, giới hạn người có quyền truy cập; không gửi ảnh khuôn mặt hoặc database thật qua kênh công khai.
- Cấu hình Streamlit mặc định giới hạn truy cập mạng ở `127.0.0.1`; Compose cũng ánh xạ cổng vào loopback. Không tự mở ứng dụng ra mạng trường học hoặc Internet nếu chưa có biện pháp triển khai và kiểm soát truy cập phù hợp.
- Ứng dụng **chưa có đăng nhập hoặc phân quyền người dùng/giáo viên**. Không coi trường tên tài khoản trong hồ sơ giáo viên là cơ chế xác thực.
- Kết quả nhận diện có thể sai. Giáo viên cần xác nhận trước khi lưu và duy trì phương án điểm danh thủ công.

## Giới hạn và hướng phát triển

**Giới hạn hiện tại:** nhận diện phụ thuộc vào ảnh mẫu, ánh sáng, góc chụp và khả năng truy cập camera; hệ thống lưu dữ liệu cục bộ; ứng dụng chưa có đăng nhập/phân quyền và chưa có giao diện sao lưu/khôi phục. Không có cơ chế tự suy ra vắng mặt từ việc camera không nhận diện được học sinh.

Các chức năng chưa có trong mã nguồn không được trình bày như đã hoàn thành hoặc là cam kết phát triển.

## Đóng góp và giấy phép

Tôi trực tiếp nghiên cứu, xây dựng, phát triển và hoàn thiện Smart Attendance phục vụ công tác điểm danh học sinh. Tôi phân tích yêu cầu nghiệp vụ, phát triển các chức năng quản lý học sinh, lớp học và giáo viên; đăng ký và nhận diện khuôn mặt; ghi nhận lượt vào/lượt ra có xác nhận; tra cứu lịch sử và lập báo cáo chuyên cần. Tôi cũng tích hợp các công nghệ phù hợp, điều chỉnh quy trình và hoàn thiện hệ thống để đáp ứng nhu cầu sử dụng thực tế. Python, Streamlit, OpenCV, `face-recognition`, dlib và các thư viện liên quan là công nghệ, công cụ nền tảng được sử dụng trong quá trình phát triển sản phẩm.

Vui lòng tuân thủ giấy phép áp dụng của các thư viện và công nghệ bên thứ ba được sử dụng trong dự án.
