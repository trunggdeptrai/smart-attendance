# Mô tả thuật toán nhận diện

Tài liệu mô tả đúng những gì mã nguồn đang làm (kiểm tra ngày 04/11/2026). Các giá trị tham số được chọn thủ công và **chưa được kiểm chứng bằng thực nghiệm có hệ thống**.

## 1. Quy trình tổng thể

```text
Ảnh/khung hình (BGR)
  └─(1) Phát hiện khuôn mặt – Haar Cascade (core/face_detect.py)
        thu nhỏ về rộng ≤ 640 px (camera trực tiếp: 480 px), xám hóa,
        detectMultiScale(scaleFactor=1.1, minNeighbors=4, minSize=60×60 px gốc)
  └─(2) Cắt khuôn mặt – mở rộng 18% mỗi phía, resize 200×200 (core/save_face.py)
  └─(3) Kiểm tra tương phản – độ lệch chuẩn mức xám < 8 → từ chối (low_contrast)
  └─(4) Mã hóa – face_recognition.face_encodings → vector 128 chiều (dlib ResNet)
        vị trí khuôn mặt = toàn bộ ảnh cắt (bỏ bước dò HOG để tiết kiệm thời gian)
  └─(5) Phân loại – K-NN có trọng số + ngưỡng riêng + biên + đa số phiếu
  └─(6) Giáo viên xác nhận → ghi SQLite (chống trùng bằng chỉ mục duy nhất)
```

Khi **huấn luyện** (`core/face_dataset.py`): mỗi ảnh mẫu 200×200 được dò lại bằng HOG; nếu không thấy thì dùng toàn ảnh; mã hóa → lưu `models/face_encodings.pkl` (vector + nhãn), `label_map.json`, `model_metadata.json` (ngưỡng). Đây không phải “huấn luyện mạng nơ-ron” mà là xây dựng thư viện vector tham chiếu; mạng dlib dùng nguyên trọng số đã huấn luyện sẵn.

**Điểm cần nghiên cứu:** bước huấn luyện định vị bằng HOG còn bước nhận diện dùng toàn khung cắt → hai vector có thể lệch nhau. Công cụ đánh giá có cấu hình `app_weighted_knn_hog` để đo ảnh hưởng này.

## 2. Phân loại (`classify_encoding`, chiến lược `weighted_knn`)

Cho vector truy vấn `q`, thư viện `{(e_i, y_i)}`:

1. Khoảng cách Euclid `d_i = ||q − e_i||`.
2. Lấy K = 3 láng giềng gần nhất.
3. Trọng số `w_i = 1 / (d_i + 1e-5)`; ứng viên thắng = mã có tổng trọng số lớn nhất.
4. Ngưỡng `T` = ngưỡng riêng của ứng viên (xem mục 3), điều chỉnh theo hồ sơ camera (`threshold_offset`, `min_threshold`), không vượt 0,48.
5. Chấp nhận khi **đồng thời**:
   - `d_min ≤ T` (ngược lại: `above_threshold`);
   - nếu trong top-K có người khác: `d_người_thứ_2 − d_min ≥ 0,04` (ngược lại: `margin_gap`);
   - ứng viên có ≥ ⌊K/2⌋+1 phiếu trong top-K (ngược lại: `no_majority`).
6. Không thỏa → trả về `Unknown` kèm `reject_reason`.

`confidence` trong kết quả thực chất là **khoảng cách** nhỏ nhất (càng nhỏ càng giống) – giữ tên cũ để tương thích.

## 3. Hiệu chỉnh ngưỡng riêng (`_build_model_metadata`)

Với mỗi học sinh có ≥ 2 ảnh: tính mọi khoảng cách nội lớp; `T = max(max_d + 0,03 ; mean_d + 2·std_d + 0,03)`, kẹp trong `[0,44 ; 0,48]` (nếu cả mô hình chỉ có 1 người: cận dưới 0,50). Học sinh có < 2 ảnh dùng 0,48.

## 4. Nhóm đối chứng (`nearest_1nn`)

Láng giềng gần nhất, một ngưỡng cố định `0,6` – tương đương cách dùng phổ biến `face_recognition.compare_faces(tolerance=0.6)`. Dùng để so sánh trong thực nghiệm.

## 5. Độ phức tạp và thời gian

So khớp là O(N·128) với N vector tham chiếu – không đáng kể với một lớp học (≈ 40 học sinh × 5–10 ảnh). Thời gian chủ yếu nằm ở bước mã hóa dlib. Hàm `predict_face` trả `latency_ms` (mã hóa + so khớp); bước phát hiện đo riêng trong công cụ đánh giá (`detect_ms`). **Chưa có số liệu đo chính thức** – xem kế hoạch thực nghiệm.

## 6. Hạn chế đã biết của phương pháp

- Haar Cascade: chỉ khuôn mặt chính diện; nhạy ánh sáng; dễ phát hiện sai trên nền phức tạp.
- Ảnh độ phân giải thấp / khuôn mặt < 60 px: không phát hiện hoặc vector kém tin cậy.
- Camera trực tiếp chỉ nhận diện khi khung hình có **đúng một** khuôn mặt; chế độ ảnh xử lý nhiều khuôn mặt.
- Không có chống giả mạo (ảnh in, màn hình).
- Trọng số dlib được huấn luyện chủ yếu trên ảnh người trưởng thành; độ chính xác với học sinh Việt Nam cần được đo trực tiếp.
