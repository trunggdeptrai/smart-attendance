# Bộ công cụ nghiên cứu

## 1. Nguyên tắc

- Không tạo, ước lượng hay “làm đẹp” số liệu. Mọi chỉ số được tính từ ảnh thật hoặc nhật ký thật.
- Chỉ dùng ảnh của người đã ký phiếu đồng ý tham gia (học sinh chưa thành niên cần cha mẹ/người giám hộ ký).
- Ảnh kiểm thử phải **khác** ảnh dùng để đăng ký (công cụ tự chặn ảnh trùng theo mã SHA-256).
- Lưu ảnh kiểm thử ngoài thư mục mã nguồn (hoặc trong `data/eval/` – đã .gitignore). Không đưa ảnh khuôn mặt vào tài liệu công khai.

## 2. Tổ chức ảnh kiểm thử

```text
D:\anh_kiem_thu\
├── sang_tu_nhien\          # điều kiện 1
│   ├── HS003\  01.jpg 02.jpg ...
│   ├── HS004\  ...
│   └── NGOAI01\ ...         # người KHÔNG đăng ký trong hệ thống (kiểm tra nhận nhầm)
├── thieu_sang\             # điều kiện 2
├── nghieng_30\             # điều kiện 3
└── xa_3m\                  # điều kiện 4
```

Thư mục mã phải trùng mã học sinh trong hệ thống. Người ngoài đặt mã bắt đầu bằng `NGOAI`. Có thể dùng `--manifest` (CSV: `file,true_code,condition`).

## 3. Chạy

```powershell
# Kiểm định bỏ-ra-một trên ảnh mẫu đã đăng ký (không cần chụp thêm)
python -m research.evaluate_recognition --loo --tag loo_lan1

# Tập kiểm thử độc lập theo điều kiện
python -m research.evaluate_recognition --eval-dir D:\anh_kiem_thu --tag thuc_nghiem_lan1
```

Kết quả: `research_results/<thời điểm>_<tag>/`

| Tệp | Nội dung |
|---|---|
| `per_image.csv` | Từng ảnh × cấu hình: mã thật, mã dự đoán, khoảng cách, ngưỡng, kết quả, lý do, kích thước khuôn mặt, độ sáng TB, thời gian |
| `summary.csv` | Tổng hợp theo cấu hình × điều kiện |
| `threshold_sweep.csv` | Quét ngưỡng 0,30–0,70 cho 1-NN |
| `run_info.json` | Phiên bản phần mềm, cấu hình máy, tham số – để tái lập |

## 4. Định nghĩa chỉ số (nhận dạng tập mở)

| Kết quả | Người thật có đăng ký | Người ngoài (`NGOAI…`) |
|---|---|---|
| Hệ thống trả đúng mã | correct_accept | – |
| Hệ thống trả mã người khác | wrong_accept (nhận nhầm) | false_accept |
| Hệ thống trả Unknown | false_reject (bỏ sót) | correct_reject |
| Không phát hiện khuôn mặt | no_face (tính vào bỏ sót) | no_face |

- `identification_rate` = correct_accept / số ảnh người thật
- `misidentification_rate` = wrong_accept / số ảnh người thật  ← **lỗi nghiêm trọng nhất với điểm danh**
- `false_reject_rate` = (false_reject + no_face) / số ảnh người thật
- `false_accept_rate` = false_accept / số ảnh người ngoài
- `accuracy` = (correct_accept + correct_reject) / tổng ảnh

## 5. Nhật ký trong quá trình sử dụng

`research_logs/recognition_events.csv` và `teacher_decisions.csv` – xem trực tiếp ở trang **Đánh giá thực nghiệm** hoặc mở bằng Excel. Dùng để đo trong buổi điểm danh thật: thời gian xử lý, tỷ lệ Unknown, số lần giáo viên phải điều chỉnh.

## 6. Bấm giờ quy trình điểm danh

Thời gian điểm danh thủ công và bằng hệ thống được đo bằng đồng hồ bấm giờ và ghi vào bảng tính riêng (ngày, phương án, số học sinh, thời gian, số lỗi).
