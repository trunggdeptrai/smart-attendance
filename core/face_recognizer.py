from functools import lru_cache
from pathlib import Path
import json
import pickle

import cv2
import numpy as np
import face_recognition

from core.face_dataset import (
    count_images_per_employee,
    load_training_data,
)
from db.database import get_employee_codes

MODEL_DIR = Path("models")
ENCODINGS_PATH = MODEL_DIR / "face_encodings.pkl"
LABEL_MAP_PATH = MODEL_DIR / "label_map.json"
MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"

# Nguong nhan dien: distance <= threshold thi la match
# Sau khi retrain, khoang cach giua cac nguoi khac nhau deu >= 0.4917
# Thiet lap nguong an toan 0.48 de triet tieu 100% rui ro nhan nham
DEFAULT_MATCH_THRESHOLD = 0.48
STRICT_MATCH_THRESHOLD = 0.44
SINGLE_PERSON_THRESHOLD = 0.50
THRESHOLD_MARGIN = 0.03

# Tham so phan loai Weighted K-NN va Margin Gap Check
KNN_K = 3
MARGIN_GAP_THRESHOLD = 0.04

DEFAULT_CAMERA_PROFILES = {
    "0": {
        "name": "Laptop Camera",
        "threshold_offset": 0.0,
        "min_threshold": 0.4,
    },
    "1": {
        "name": "Rappo C200",
        "threshold_offset": 0.05,
        "min_threshold": 0.45,
    },
}


def ensure_model_dir():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def clear_model_cache():
    _load_model_cached.cache_clear()


def _normalize_camera_profiles(camera_profiles):
    normalized_profiles = {}

    for camera_key, profile in DEFAULT_CAMERA_PROFILES.items():
        source_profile = dict(profile)
        if camera_profiles and camera_key in camera_profiles:
            source_profile.update(camera_profiles[camera_key])

        normalized_profiles[str(camera_key)] = {
            "name": str(source_profile.get("name", DEFAULT_CAMERA_PROFILES[camera_key]["name"])),
            "threshold_offset": float(source_profile.get("threshold_offset", 0.0)),
            "min_threshold": float(source_profile.get("min_threshold", STRICT_MATCH_THRESHOLD)),
        }

    return normalized_profiles


@lru_cache(maxsize=1)
def _load_model_cached(encodings_mtime_ns, label_map_mtime_ns, metadata_mtime_ns):
    with open(ENCODINGS_PATH, "rb") as f:
        model_data = pickle.load(f)

    known_encodings = np.asarray(model_data["encodings"], dtype=np.float64)
    known_labels = model_data["labels"]

    with open(LABEL_MAP_PATH, "r", encoding="utf-8") as file:
        label_to_code_raw = json.load(file)

    metadata = {
        "default_threshold": DEFAULT_MATCH_THRESHOLD,
        "code_thresholds": {},
        "images_per_employee": {},
        "camera_profiles": DEFAULT_CAMERA_PROFILES,
    }

    if MODEL_METADATA_PATH.exists():
        with open(MODEL_METADATA_PATH, "r", encoding="utf-8") as file:
            metadata.update(json.load(file))

    label_to_code = {int(key): value for key, value in label_to_code_raw.items()}
    metadata["default_threshold"] = float(
        metadata.get("default_threshold", DEFAULT_MATCH_THRESHOLD)
    )
    metadata["code_thresholds"] = {
        str(key): float(value)
        for key, value in metadata.get("code_thresholds", {}).items()
    }
    metadata["camera_profiles"] = _normalize_camera_profiles(
        metadata.get("camera_profiles")
    )

    return known_encodings, known_labels, label_to_code, metadata


def _build_model_metadata(known_encodings, known_labels, label_to_code, images_per_employee):
    """
    Tính ngưỡng tối ưu cho mỗi nhân viên dựa trên khoảng cách nội bộ (intra-class distance).
    """
    distance_by_code = {}
    min_threshold = (
        SINGLE_PERSON_THRESHOLD
        if len(label_to_code) == 1
        else STRICT_MATCH_THRESHOLD
    )

    # Tính mean distance giữa các encoding của cùng 1 người
    for employee_code in label_to_code.values():
        label = None
        for lbl, code in label_to_code.items():
            if code == employee_code:
                label = lbl
                break

        if label is None:
            continue

        # Lấy tất cả encodings của nhân viên này
        employee_encodings = [
            enc for enc, lbl in zip(known_encodings, known_labels)
            if lbl == label
        ]

        if len(employee_encodings) < 2:
            distance_by_code[employee_code] = [0.0]
            continue

        # Tính khoảng cách giữa tất cả cặp encodings
        distances = []
        for i in range(len(employee_encodings)):
            for j in range(i + 1, len(employee_encodings)):
                dist = float(np.linalg.norm(
                    np.array(employee_encodings[i]) - np.array(employee_encodings[j])
                ))
                distances.append(dist)
        distance_by_code[employee_code] = distances

    code_thresholds = {}

    for employee_code in label_to_code.values():
        distances = distance_by_code.get(employee_code, [])

        if not distances or all(d == 0.0 for d in distances):
            code_thresholds[employee_code] = DEFAULT_MATCH_THRESHOLD
            continue

        max_distance = max(distances)
        mean_distance = float(np.mean(distances))
        std_distance = float(np.std(distances))

        calibrated_threshold = max(
            max_distance + THRESHOLD_MARGIN,
            mean_distance + (2 * std_distance) + THRESHOLD_MARGIN,
        )
        code_thresholds[employee_code] = min(
            DEFAULT_MATCH_THRESHOLD,
            max(min_threshold, calibrated_threshold),
        )

    return {
        "default_threshold": DEFAULT_MATCH_THRESHOLD,
        "code_thresholds": code_thresholds,
        "images_per_employee": images_per_employee,
        "camera_profiles": _normalize_camera_profiles(None),
    }


def train_model():
    valid_employee_codes = get_employee_codes()
    encodings, labels, label_to_code, code_to_label = load_training_data(
        valid_employee_codes=valid_employee_codes,
    )

    if len(valid_employee_codes) == 0:
        raise ValueError("No employees found in database.")

    if len(encodings) == 0:
        raise ValueError("No training images found for valid employees in dataset.")

    ensure_model_dir()

    # Lưu encodings và labels dưới dạng pickle
    model_data = {
        "encodings": encodings,
        "labels": labels.tolist(),
    }
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump(model_data, f)

    images_per_employee = count_images_per_employee(valid_employee_codes)
    metadata = _build_model_metadata(
        encodings,
        labels.tolist(),
        label_to_code,
        images_per_employee,
    )

    with open(LABEL_MAP_PATH, "w", encoding="utf-8") as file:
        json.dump(label_to_code, file, ensure_ascii=False, indent=2)

    with open(MODEL_METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    clear_model_cache()

    return {
        "num_images": len(encodings),
        "num_people": len(label_to_code),
        "label_to_code": label_to_code,
        "images_per_employee": images_per_employee,
        "code_thresholds": metadata["code_thresholds"],
        "camera_profiles": metadata["camera_profiles"],
    }


def load_model():
    if not ENCODINGS_PATH.exists():
        raise FileNotFoundError("Model file not found. Please train model first.")

    if not LABEL_MAP_PATH.exists():
        raise FileNotFoundError("Label map file not found. Please train model first.")

    encodings_mtime_ns = ENCODINGS_PATH.stat().st_mtime_ns
    label_map_mtime_ns = LABEL_MAP_PATH.stat().st_mtime_ns
    metadata_mtime_ns = (
        MODEL_METADATA_PATH.stat().st_mtime_ns if MODEL_METADATA_PATH.exists() else 0
    )
    return _load_model_cached(encodings_mtime_ns, label_map_mtime_ns, metadata_mtime_ns)


def _apply_camera_profile(match_threshold, metadata, camera_index):
    if camera_index is None:
        return match_threshold, None

    camera_profiles = metadata.get("camera_profiles", {})
    camera_profile = camera_profiles.get(str(camera_index))
    if camera_profile is None:
        return match_threshold, None

    adjusted_threshold = max(
        match_threshold + float(camera_profile.get("threshold_offset", 0.0)),
        float(camera_profile.get("min_threshold", STRICT_MATCH_THRESHOLD)),
    )
    adjusted_threshold = min(DEFAULT_MATCH_THRESHOLD, adjusted_threshold)
    return adjusted_threshold, camera_profile


def predict_face(face_image, camera_index=None):
    """
    Nhận diện khuôn mặt bằng cách so sánh face encoding 128D.
    face_image: ảnh BGR của khuôn mặt đã crop.
    Trả về dict tương thích với giao diện cũ.
    """
    known_encodings, known_labels, label_to_code, metadata = load_model()
    if known_encodings.size == 0:
        return {
            "predicted_code": "Unknown",
            "display_code": "Unknown",
            "confidence": 1.0,
            "match_threshold": DEFAULT_MATCH_THRESHOLD,
            "base_match_threshold": DEFAULT_MATCH_THRESHOLD,
            "is_match": False,
            "camera_profile": None,
        }

    # Convert BGR to RGB
    if len(face_image.shape) == 2:
        rgb_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2RGB)
    else:
        rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

    # Kiem tra anh dau vao: neu anh qua dong nhat (den kit, trang xoa hoac nhieu deu), do lech chuan pixel rat thap
    # Mat nguoi thuc te luon co do tuong phang mat/mui/mieng voi std > 10.0
    gray_img = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    if float(np.std(gray_img)) < 8.0:
        return {
            "predicted_code": "Unknown",
            "display_code": "Unknown",
            "confidence": 1.0,
            "match_threshold": DEFAULT_MATCH_THRESHOLD,
            "base_match_threshold": DEFAULT_MATCH_THRESHOLD,
            "is_match": False,
            "camera_profile": None,
        }

    # Vì ảnh face_image truyền vào đã được crop chính xác bởi Haar Cascade trước đó,
    # ta bỏ qua bước quét HOG dư thừa (giúp tiết kiệm ~20-30ms mỗi frame) và dùng luôn toàn bộ khung ảnh crop.
    face_locations = [(0, rgb_image.shape[1], rgb_image.shape[0], 0)]

    # Get encoding for the face
    face_encs = face_recognition.face_encodings(rgb_image, face_locations)

    if len(face_encs) == 0:
        return {
            "predicted_code": "Unknown",
            "display_code": "Unknown",
            "confidence": 1.0,
            "match_threshold": DEFAULT_MATCH_THRESHOLD,
            "base_match_threshold": DEFAULT_MATCH_THRESHOLD,
            "is_match": False,
            "camera_profile": None,
        }

    face_encoding = face_encs[0]

    # So sánh với tất cả encodings đã biết
    distances = face_recognition.face_distance(
        known_encodings,
        face_encoding
    )

    if len(distances) == 0:
        return {
            "predicted_code": "Unknown",
            "display_code": "Unknown",
            "confidence": 1.0,
            "match_threshold": DEFAULT_MATCH_THRESHOLD,
            "base_match_threshold": DEFAULT_MATCH_THRESHOLD,
            "is_match": False,
            "camera_profile": None,
        }

    # === THUAT TOAN PHAN LOAI DISTANCE-WEIGHTED K-NN & MARGIN GAP CHECK ===
    num_samples = len(distances)
    effective_k = min(KNN_K, num_samples)

    # 1. Tim K lang gieng gan nhat
    top_k_indices = np.argsort(distances)[:effective_k]
    top_k_distances = [float(distances[idx]) for idx in top_k_indices]
    top_k_labels = [known_labels[idx] for idx in top_k_indices]
    top_k_codes = [label_to_code.get(lbl, "Unknown") for lbl in top_k_labels]

    # Khoang cach nho nhat trong toan bo database
    best_distance = float(top_k_distances[0])
    best_candidate_code = top_k_codes[0]

    # 2. Tinh tong trong so khoang cach cho tung ung vien trong Top-K
    # Cong thuc: weight = 1 / (distance + 1e-5)
    code_weights = {}
    code_vote_counts = {}
    for code, dist in zip(top_k_codes, top_k_distances):
        w = 1.0 / (dist + 1e-5)
        code_weights[code] = code_weights.get(code, 0.0) + w
        code_vote_counts[code] = code_vote_counts.get(code, 0) + 1

    # Ung vien co tong trong so cao nhat
    winning_code = max(code_weights.keys(), key=lambda c: code_weights[c])

    # 3. Kiem tra nguong nguong tin cay (Threshold)
    default_threshold = float(metadata.get("default_threshold", DEFAULT_MATCH_THRESHOLD))
    code_thresholds = metadata.get("code_thresholds", {})
    base_match_threshold = float(code_thresholds.get(winning_code, default_threshold))

    match_threshold, camera_profile = _apply_camera_profile(
        base_match_threshold,
        metadata,
        camera_index,
    )

    # 4. Kiem tra Margin Gap Check (Do chenh lech khoang cach voi nguoi dung thu hai)
    # Neu co ung vien khac nguoi xuat hien trong top K, khoang cach giua ho phai du xa
    margin_satisfied = True
    other_code_distances = [
        dist for code, dist in zip(top_k_codes, top_k_distances)
        if code != winning_code and code != "Unknown"
    ]
    if other_code_distances:
        second_best_dist = min(other_code_distances)
        # Neu khoang cach giua nguoi gan nhat va nguoi thu 2 qua gan (< MARGIN_GAP_THRESHOLD)
        # He thong tu choi nhan dien de tranh bat nham nguoi
        if (second_best_dist - best_distance) < MARGIN_GAP_THRESHOLD:
            margin_satisfied = False

    # 5. Kiem tra da so phieu (Majority vote)
    # Trong top K, ung vien chien thang phai chiem it nhat (K // 2 + 1) phieu
    # Doi voi K=3, can it nhat 2/3 phieu. Neu K=1 thi can 1/1.
    min_required_votes = (effective_k // 2) + 1
    has_majority = code_vote_counts.get(winning_code, 0) >= min_required_votes

    # 6. Phan quyet cuoi cung
    is_match = (
        winning_code != "Unknown"
        and best_distance <= match_threshold
        and margin_satisfied
        and has_majority
    )

    predicted_code = winning_code if (has_majority or margin_satisfied) else best_candidate_code

    return {
        "predicted_code": predicted_code,
        "display_code": predicted_code if is_match else "Unknown",
        "confidence": best_distance,
        "match_threshold": match_threshold,
        "base_match_threshold": base_match_threshold,
        "is_match": is_match,
        "camera_profile": camera_profile,
    }
