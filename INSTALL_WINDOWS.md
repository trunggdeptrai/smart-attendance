# Cài đặt Smart Attendance trên Windows

## Yêu cầu

- Windows 10/11 64-bit.
- Python **3.11.x 64-bit** và Python Launcher (`py`). Phiên bản này được ghim để tránh các bản Python mới chưa tương thích với NumPy, OpenCV và dlib.
- Không cần Visual Studio Build Tools/CMake: `requirements.txt` dùng bản dựng sẵn `dlib-bin` 20.0.1.
- Camera chỉ cần thiết cho các luồng sử dụng camera; một số luồng cho phép tải ảnh thay thế.

## Cài mới từ tệp ZIP

1. Tải ZIP từ GitHub và giải nén vào thư mục người dùng có quyền ghi, ví dụ `C:\Users\<Tên>\Desktop\smart-attendance-main`.
2. Mở PowerShell trong thư mục chứa `app.py`. Có thể mở thư mục trong Explorer, chọn thanh địa chỉ, nhập `powershell`, rồi nhấn Enter.
3. Xác nhận đúng thư mục:

   ```powershell
   Get-Location
   Test-Path .\app.py
   ```

   Lệnh thứ hai phải trả về `True`.

4. Chạy bộ cài tự động. Script tạo `.venv` nếu chưa có, cài dependencies, tạo thư mục dữ liệu và khởi tạo/cập nhật schema bằng cơ chế database hiện có:

   ```powershell
   .\setup_windows.bat
   ```

   Script không xóa môi trường hiện có hoặc dữ liệu. Nếu `.venv` dùng phiên bản Python khác, script yêu cầu đổi tên thư mục đó thay vì tự xóa.

5. Hoặc cài thủ công:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python check_environment.py --create-dirs --init-db
   ```

   Nếu PowerShell chặn kích hoạt môi trường, có thể bỏ qua bước Activate và gọi trực tiếp `.\.venv\Scripts\python.exe` cho các lệnh còn lại. Không cần đổi execution policy.

6. Kiểm tra môi trường và chạy ứng dụng:

   ```powershell
   .\.venv\Scripts\python.exe check_environment.py
   .\run.bat
   ```

   Có thể chạy trực tiếp sau khi đã chuyển terminal vào thư mục dự án:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run .\app.py
   ```

7. Mở `http://localhost:8501`. Tạo lớp, sau đó thêm học sinh. Database mới ban đầu rỗng; mô hình nhận diện chỉ xuất hiện sau khi đăng ký ảnh và huấn luyện.

## Khởi tạo database

Ứng dụng tự gọi hàm khởi tạo database khi mở. Để khởi tạo trước khi chạy:

```powershell
.\.venv\Scripts\python.exe check_environment.py --create-dirs --init-db
```

Hàm `init_db()` dùng `create_all` và các migration đã có; có thể chạy lặp lại. Khi phát hiện database cần migration, ứng dụng tạo backup trong `database_backups/` theo thiết kế hiện tại. Luôn sao lưu `attendance.db` và dừng ứng dụng trước khi chuyển dữ liệu hoặc cập nhật phiên bản. Không xóa database để xử lý lỗi.

## Cài gói tải dataset tùy chọn

`download_dataset.py` không cần để chạy điểm danh. Chỉ khi chủ dự án cần tải bộ dataset phát triển mới cài thêm:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dataset.txt
.\.venv\Scripts\python.exe .\download_dataset.py
```

Dataset tải xuống được lưu trong `dataset_faces/`, không phải thư mục ảnh học sinh `data/faces/`.

## Cập nhật mã nguồn mà không mất dữ liệu

1. Dừng ứng dụng.
2. Sao lưu `attendance.db`, toàn bộ `data/faces/`, `models/` và `database_backups/` vào nơi riêng tư.
3. Giải nén mã nguồn mới vào thư mục mã nguồn. Không chép đè các bản dữ liệu duy nhất; giữ dữ liệu bên ngoài thư mục mã nguồn rồi chép lại nếu cần.
4. Trong thư mục mới, tạo/cài `.venv` bằng `setup_windows.bat` (hoặc cài requirements thủ công).
5. Chép dữ liệu từ backup vào đúng các vị trí, chạy preflight và khởi động:

   ```powershell
   .\.venv\Scripts\python.exe check_environment.py --create-dirs --init-db
   .\run.bat
   ```

Migration hiện có được áp dụng khi khởi tạo. Nếu cập nhật nhiều phiên bản cùng lúc, hãy xác minh migration giữa các phiên bản trước khi dùng database thật.

## Khắc phục lỗi

| Thông báo/tình huống | Cách xử lý |
|---|---|
| Không tìm thấy Python 3.11 | Cài Python 3.11 x64 và Python Launcher; kiểm tra `py -3.11 --version`. |
| `.venv` không đúng Python | Đổi tên `.venv` hiện tại (không cần xóa) rồi chạy lại `setup_windows.bat`. |
| Lỗi khi cài `dlib` | Kiểm tra đang dùng Python 3.11 64-bit (có bản dựng sẵn `dlib-bin`). Nếu môi trường cũ còn gói `dlib` hoặc `face-recognition` cài trước đó, chạy `pip uninstall dlib face-recognition` rồi cài lại `requirements.txt`. |
| Thiếu package / lỗi import | Chạy `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, sau đó `check_environment.py`. |
| `arange: cannot compute length` | Chạy `.\run.bat` để chắc chắn dùng `.venv` của dự án. Kiểm tra chính xác interpreter và NumPy bằng `.\.venv\Scripts\python.exe --version` và `.\.venv\Scripts\python.exe -m pip show numpy`. Cần Python 3.11.x và NumPy 2.2.6; nếu dùng `.venv` khác, đổi tên nó rồi chạy `setup_windows.bat`. |
| Chưa có file mô hình | Trạng thái bình thường với cài đặt mới. Tạo hồ sơ học sinh, đăng ký ảnh rồi huấn luyện ở trang đăng ký khuôn mặt. |
| Không có lớp/học sinh hoặc báo cáo trống | Đây là database mới chưa có dữ liệu. Tạo lớp và hồ sơ học sinh; ứng dụng không tự thêm dữ liệu mẫu. |
| Không mở được camera | Đóng ứng dụng khác đang dùng camera, chọn camera đúng; với camera trình duyệt, cấp quyền và dùng `localhost` hoặc HTTPS. |
| Database không đọc được | Dừng ứng dụng, giữ nguyên tệp hiện tại và khôi phục từ backup đã xác minh. Không xóa hoặc tạo đè database để thử sửa. |
| Không tìm thấy `.streamlit/config.toml` | Khôi phục tệp cấu hình từ mã nguồn; nếu thiếu, Streamlit chạy với cấu hình mặc định. |

`check_environment.py` kiểm tra Python, thư viện runtime, OpenCV Haar Cascade, thư mục, cấu hình, database và tình trạng model; lỗi bắt buộc được in kèm hướng xử lý. `app.py` cũng chặn runtime Python/NumPy không tương thích trước khi mở các trang để báo cách khởi chạy phù hợp.

## Kiểm thử

Từ thư mục dự án, chạy các kiểm thử ổn định độc lập (không cần cài pytest):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_stability.py" -v
.\.venv\Scripts\python.exe tests\test_dashboard_data.py
```

Kiểm thử database dùng SQLite tạm trong thư mục temporary và không ghi dữ liệu kiểm thử vào `attendance.db`.
