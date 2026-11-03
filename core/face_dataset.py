from pathlib import Path

import cv2
import numpy as np
import face_recognition

# Doc toan bo anh trong data/faces, chuyen du lieu anh thanh face encodings
# Tao mapping giua employee_code va list cac face encoding vectors (128D)
DATASET_DIR = Path("data/faces")
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def list_employee_folders(valid_employee_codes=None):
    """
    Tra ve danh sach thu muc nhan vien trong data/faces.
    Chi lay cac thu muc hop le neu co danh sach employee_code tu database.
    """
    if not DATASET_DIR.exists():
        return []

    valid_codes = set(valid_employee_codes or [])
    folders = [folder for folder in DATASET_DIR.iterdir() if folder.is_dir()]

    if valid_codes:
        folders = [folder for folder in folders if folder.name in valid_codes]

    return sorted(folders, key=lambda folder: folder.name)


def list_image_files(folder_path):
    """
    Tra ve danh sach file anh hop le trong 1 thu muc nhan vien.
    """
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


def preprocess_face_image(image, image_size=(200, 200)):
    """
    Chuan hoa anh khuon mat: resize ve kich thuoc chuan.
    Voi face_recognition, khong can chuyen grayscale hay CLAHE nua
    vi model dlib lam viec truc tiep tren anh mau RGB.
    """
    if image is None:
        return None

    resized = cv2.resize(image, image_size)
    return resized


def load_training_data(image_size=(200, 200), valid_employee_codes=None):
    """
    Doc toan bo dataset khuon mat va trich xuat face encodings (128D vectors).

    Tra ve:
    - encodings: list cac 128-dimensional numpy arrays
    - labels: list nhan so tuong ung
    - label_to_code: dict anh xa so -> ma nhan vien
    - code_to_label: dict anh xa ma nhan vien -> so
    """
    encodings = []
    labels = []
    label_to_code = {}
    code_to_label = {}

    employee_folders = list_employee_folders(valid_employee_codes)

    for label_index, employee_folder in enumerate(employee_folders):
        employee_code = employee_folder.name
        label_to_code[label_index] = employee_code
        code_to_label[employee_code] = label_index

        image_files = list_image_files(employee_folder)

        for image_file in image_files:
            image = cv2.imread(str(image_file))

            if image is None:
                print(f"Cannot read image: {image_file}")
                continue

            # Convert BGR to RGB for face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect face locations in the image
            face_locations = face_recognition.face_locations(rgb_image, model="hog")

            if len(face_locations) == 0:
                # If no face detected, try the whole image as a face
                # (because these are already cropped face images)
                face_locations = [(0, rgb_image.shape[1], rgb_image.shape[0], 0)]

            # Get encoding for the first (or only) face
            face_encs = face_recognition.face_encodings(rgb_image, face_locations)

            if len(face_encs) > 0:
                encodings.append(face_encs[0])
                labels.append(label_index)

    return encodings, np.array(labels), label_to_code, code_to_label


def count_images_per_employee(valid_employee_codes=None):
    """
    Thong ke so anh cua tung nhan vien trong dataset hop le.
    """
    stats = {}

    for employee_folder in list_employee_folders(valid_employee_codes):
        employee_code = employee_folder.name
        stats[employee_code] = len(list_image_files(employee_folder))

    return stats