from datasets import load_dataset
import os

print("Đang kết nối và tải dataset từ Hugging Face... Quá trình này có thể mất vài phút.")
dataset = load_dataset("fptudsc/face-celeb-vietnamese")

# Tạo thư mục gốc chứa dữ liệu ảnh
base_dir = "dataset_faces"
os.makedirs(base_dir, exist_ok=True)

train_data = dataset['train']
print(f"Đã lấy được thông tin của {len(train_data)} bức ảnh. Bắt đầu giải nén và lưu ảnh...")

# Kiểm tra xem label có phải dạng ClassLabel (ánh xạ từ số sang tên ca sĩ) hay không
label_feature = train_data.features.get('label')
has_int2str = hasattr(label_feature, 'int2str')

# Lặp qua từng dòng dữ liệu để lưu
for i, item in enumerate(train_data):
    try:
        img = item['image']
        raw_label = item['label']
        
        # Nếu label là số ID thì đổi sang tên ca sĩ, ngược lại giữ nguyên chuỗi
        if has_int2str and isinstance(raw_label, int):
            label_name = str(label_feature.int2str(raw_label)).strip()
        else:
            label_name = str(raw_label).strip()
        
        # Xóa các ký tự đặc biệt trong tên để làm tên thư mục an toàn
        safe_label = "".join([c for c in label_name if c.isalnum() or c.isspace() or c in ('_', '-')]).strip()
        if not safe_label:
            safe_label = f"unknown_{raw_label}"
            
        # Tạo thư mục cho từng ca sĩ
        person_dir = os.path.join(base_dir, safe_label)
        os.makedirs(person_dir, exist_ok=True)
        
        # Chuyển sang hệ màu RGB để tránh lỗi khi lưu định dạng .jpg (nếu ảnh gốc là RGBA/PNG)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Lưu ảnh
        img_path = os.path.join(person_dir, f"{safe_label}_{i}.jpg")
        img.save(img_path, "JPEG", quality=95)
        
        # In tiến độ mỗi 100 ảnh để biết chương trình vẫn đang chạy mượt
        if (i + 1) % 100 == 0:
            print(f"Đã lưu {i + 1}/{len(train_data)} ảnh...")
            
    except Exception as e:
        print(f"Lỗi ở ảnh số {i}: {e}")

print(f"Hoàn tất! Toàn bộ ảnh đã được phân loại gọn gàng vào thư mục '{base_dir}'.")