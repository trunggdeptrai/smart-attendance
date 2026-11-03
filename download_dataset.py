from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "Thiếu gói datasets. Cài tùy chọn bằng lệnh: "
            "python -m pip install -r requirements-dataset.txt"
        )
        return 1

    print("Đang kết nối và tải dataset từ Hugging Face... Quá trình này có thể mất vài phút.")
    dataset = load_dataset("fptudsc/face-celeb-vietnamese")

    base_dir = PROJECT_ROOT / "dataset_faces"
    base_dir.mkdir(parents=True, exist_ok=True)

    train_data = dataset["train"]
    print(
        f"Đã lấy được thông tin của {len(train_data)} bức ảnh. "
        "Bắt đầu giải nén và lưu ảnh..."
    )

    label_feature = train_data.features.get("label")
    has_int2str = hasattr(label_feature, "int2str")

    for index, item in enumerate(train_data):
        try:
            image = item["image"]
            raw_label = item["label"]
            if has_int2str and isinstance(raw_label, int):
                label_name = str(label_feature.int2str(raw_label)).strip()
            else:
                label_name = str(raw_label).strip()

            safe_label = "".join(
                character
                for character in label_name
                if character.isalnum()
                or character.isspace()
                or character in ("_", "-")
            ).strip()
            if not safe_label:
                safe_label = f"unknown_{raw_label}"

            person_dir = base_dir / safe_label
            person_dir.mkdir(parents=True, exist_ok=True)

            if image.mode != "RGB":
                image = image.convert("RGB")
            image_path = person_dir / f"{safe_label}_{index}.jpg"
            image.save(image_path, "JPEG", quality=95)

            if (index + 1) % 100 == 0:
                print(f"Đã lưu {index + 1}/{len(train_data)} ảnh...")
        except (KeyError, OSError, TypeError, ValueError) as error:
            print(f"Lỗi ở ảnh số {index}: {error}")

    print(f"Hoàn tất! Dataset được lưu trong '{base_dir}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())