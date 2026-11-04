from pathlib import Path
import shutil

import cv2

from core.paths import FACE_DATASET_DIR

# Cat anh, chinh kich thuoc va luu vao dung o cung
DATASET_DIR = FACE_DATASET_DIR
FACE_SIZE = (200, 200)
FACE_PADDING_RATIO = 0.18
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


# Kiem tra xem thu muc data/face co ma NV da ton tai, neu chua thi tao

def ensure_employee_folder(employee_code):
    employee_folder = DATASET_DIR / str(employee_code)
    ensure_dir(employee_folder)
    return employee_folder


def get_employee_folder(employee_code):
    return ensure_employee_folder(employee_code)


def delete_employee_folder(employee_code):
    employee_folder = DATASET_DIR / str(employee_code)

    if employee_folder.exists():
        shutil.rmtree(employee_folder)


def _list_image_files(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        return []

    return sorted(
        [
            file_path
            for file_path in folder.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS
        ],
        key=lambda file_path: file_path.name.lower(),
    )


def get_next_image_number(employee_code):
    employee_folder = get_employee_folder(employee_code)
    image_numbers = []

    for file_path in _list_image_files(employee_folder):
        if file_path.stem.isdigit():
            image_numbers.append(int(file_path.stem))

    if not image_numbers:
        return 1

    return max(image_numbers) + 1


def sync_employee_face_folders(employee_rows):
    ensure_dir(DATASET_DIR)

    for employee_id, employee_code in employee_rows:
        if not employee_code:
            continue

        target_folder = ensure_employee_folder(employee_code)
        legacy_folder = DATASET_DIR / str(employee_id)

        if not legacy_folder.exists() or legacy_folder == target_folder:
            continue

        for file_path in _list_image_files(legacy_folder):
            next_number = get_next_image_number(employee_code)
            target_path = target_folder / f"{next_number}{file_path.suffix.lower()}"
            shutil.move(str(file_path), target_path)

        if legacy_folder.exists() and not any(legacy_folder.iterdir()):
            legacy_folder.rmdir()


def expand_face_box(face_box, image_shape, padding_ratio=FACE_PADDING_RATIO):
    image_height, image_width = image_shape[:2]
    x, y, w, h = face_box
    pad_x = int(w * padding_ratio)
    pad_y = int(h * padding_ratio)

    left = max(0, x - pad_x)
    top = max(0, y - pad_y)
    right = min(image_width, x + w + pad_x)
    bottom = min(image_height, y + h + pad_y)

    return left, top, right, bottom


# Cat o chua khuon mat va ep ve kich thuoc

def crop_and_resize_face(image, face_box, padding_ratio=FACE_PADDING_RATIO):
    left, top, right, bottom = expand_face_box(
        face_box,
        image.shape,
        padding_ratio=padding_ratio,
    )
    face_crop = image[top:bottom, left:right]

    if face_crop.size == 0:
        x, y, w, h = face_box
        face_crop = image[y:y + h, x:x + w]

    face_crop = cv2.resize(face_crop, FACE_SIZE)
    return face_crop


# Luu xuong o cung

def save_face_image(employee_code, face_image):
    if face_image is None or face_image.size == 0:
        raise ValueError("Ảnh khuôn mặt không hợp lệ.")
    employee_folder = get_employee_folder(employee_code)
    next_number = get_next_image_number(employee_code)
    save_path = employee_folder / f"{next_number}.jpg"
    if not cv2.imwrite(str(save_path), face_image):
        raise OSError("Không thể lưu ảnh mẫu vào thư mục dữ liệu khuôn mặt.")
    return str(save_path)