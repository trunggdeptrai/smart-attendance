from functools import lru_cache
import json
import pickle
import time

import cv2
import numpy as np
import face_recognition

from core.face_dataset import (
    count_images_per_employee,
    load_training_data,
)
from core.paths import MODELS_DIR
from db.database import get_employee_codes

MODEL_DIR = MODELS_DIR
ENCODINGS_PATH = MODEL_DIR / "face_encodings.pkl"
LABEL_MAP_PATH = MODEL_DIR / "label_map.json"
MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"

# Nguong nhan dien: distance <= threshold thi la match.
# Ghi chu kiem chung: gia tri 0.48 duoc chon thu cong tren tap anh mau ban dau;
# CHUA duoc kiem chung bang thuc nghiem co he thong. Dung research/evaluate_recognition.py
# de do ty le nhan dung / nhan nham theo tung nguong truoc khi ket luan.
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
    Tính ngưỡng tối ưu cho mỗi học sinh dựa trên khoảng cách nội bộ (intra-class distance).
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

        # Lấy tất cả encodings của học sinh này
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
    if not valid_employee_codes:
        raise ValueError("Chưa có học sinh trong cơ sở dữ liệu để huấn luyện mô hình.")

    encodings, labels, label_to_code, code_to_label = load_training_data(
        valid_employee_codes=valid_employee_codes,
    )

    if len(encodings) == 0:
        raise ValueError(
            "Chưa có ảnh khuôn mặt hợp lệ cho học sinh đang học. "
            "Hãy đăng ký ảnh trước khi huấn luyện."
        )

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


def remove_model_files():
    """Xóa tệp mô hình (dùng khi không còn ảnh mẫu nào, tránh giữ lại vector cũ)."""
    removed = []
    for path in (ENCODINGS_PATH, LABEL_MAP_PATH, MODEL_METADATA_PATH):
        if path.exists():
            path.unlink()
            removed.append(path.name)
    clear_model_cache()
    return removed


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


# Chiến lược phân loại hỗ trợ (dùng cho thực nghiệm so sánh):
# - "weighted_knn": thuật toán đang dùng trong ứng dụng (mặc định).
# - "nearest_1nn": đối chứng — láng giềng gần nhất, một ngưỡng cố định,
#   tương đương cách dùng phổ biến face_recognition.compare_faces (tolerance 0.6).
STRATEGY_WEIGHTED_KNN = "weighted_knn"
STRATEGY_NEAREST_1NN = "nearest_1nn"
BASELINE_TOLERANCE = 0.6
STD_MIN_CONTRAST = 8.0


def _unknown_result(match_threshold=DEFAULT_MATCH_THRESHOLD, reason="", **extra):
    result = {
        "predicted_code": "Unknown",
        "display_code": "Unknown",
        "confidence": 1.0,
        "match_threshold": match_threshold,
        "base_match_threshold": match_threshold,
        "is_match": False,
        "camera_profile": None,
        "reject_reason": reason,
    }
    result.update(extra)
    return result


def classify_encoding(
    face_encoding,
    known_encodings,
    known_labels,
    label_to_code,
    metadata,
    camera_index=None,
    strategy=STRATEGY_WEIGHTED_KNN,
    threshold_override=None,
):
    """Phân loại một vector đặc trưng 128 chiều.

    Hàm thuần (không đọc tệp, không gọi camera) để có thể kiểm thử và chạy
    thực nghiệm so sánh giữa các chiến lược với cùng dữ liệu đầu vào.

    ``confidence`` trong kết quả là KHOẢNG CÁCH Euclid nhỏ nhất (càng nhỏ càng
    giống), giữ tên cũ để tương thích với giao diện và cơ sở dữ liệu.
    """
    known_encodings = np.asarray(known_encodings, dtype=np.float64)
    if known_encodings.size == 0:
        return _unknown_result(reason="empty_model")

    distances = np.linalg.norm(known_encodings - np.asarray(face_encoding), axis=1)
    if len(distances) == 0:
        return _unknown_result(reason="empty_model")

    if strategy == STRATEGY_NEAREST_1NN:
        best_index = int(np.argmin(distances))
        best_distance = float(distances[best_index])
        best_code = label_to_code.get(known_labels[best_index], "Unknown")
        threshold = float(BASELINE_TOLERANCE if threshold_override is None else threshold_override)
        is_match = best_code != "Unknown" and best_distance <= threshold
        return {
            "predicted_code": best_code,
            "display_code": best_code if is_match else "Unknown",
            "confidence": best_distance,
            "match_threshold": threshold,
            "base_match_threshold": threshold,
            "is_match": is_match,
            "camera_profile": None,
            "reject_reason": "" if is_match else "above_threshold",
            "strategy": strategy,
        }

    if strategy != STRATEGY_WEIGHTED_KNN:
        raise ValueError(f"Chiến lược phân loại không hợp lệ: {strategy}")

    # === THUAT TOAN PHAN LOAI DISTANCE-WEIGHTED K-NN & MARGIN GAP CHECK ===
    num_samples = len(distances)
    effective_k = min(KNN_K, num_samples)

    # 1. Tim K lang gieng gan nhat
    top_k_indices = np.argsort(distances)[:effective_k]
    top_k_distances = [float(distances[idx]) for idx in top_k_indices]
    top_k_labels = [known_labels[idx] for idx in top_k_indices]
    top_k_codes = [label_to_code.get(lbl, "Unknown") for lbl in top_k_labels]

    best_distance = float(top_k_distances[0])
    best_candidate_code = top_k_codes[0]

    # 2. Tong trong so: weight = 1 / (distance + 1e-5)
    code_weights = {}
    code_vote_counts = {}
    for code, dist in zip(top_k_codes, top_k_distances):
        w = 1.0 / (dist + 1e-5)
        code_weights[code] = code_weights.get(code, 0.0) + w
        code_vote_counts[code] = code_vote_counts.get(code, 0) + 1

    winning_code = max(code_weights.keys(), key=lambda c: code_weights[c])

    # 3. Nguong rieng cho tung hoc sinh (hieu chinh khi huan luyen) + ho so camera
    default_threshold = float(metadata.get("default_threshold", DEFAULT_MATCH_THRESHOLD))
    code_thresholds = metadata.get("code_thresholds", {})
    base_match_threshold = float(code_thresholds.get(winning_code, default_threshold))

    match_threshold, camera_profile = _apply_camera_profile(
        base_match_threshold,
        metadata,
        camera_index,
    )
    if threshold_override is not None:
        match_threshold = float(threshold_override)

    # 4. Margin Gap Check: nguoi thu hai phai cach xa du MARGIN_GAP_THRESHOLD
    margin_satisfied = True
    other_code_distances = [
        dist for code, dist in zip(top_k_codes, top_k_distances)
        if code != winning_code and code != "Unknown"
    ]
    if other_code_distances:
        second_best_dist = min(other_code_distances)
        if (second_best_dist - best_distance) < MARGIN_GAP_THRESHOLD:
            margin_satisfied = False

    # 5. Da so phieu: can it nhat K // 2 + 1 phieu (K=3 -> 2/3)
    min_required_votes = (effective_k // 2) + 1
    has_majority = code_vote_counts.get(winning_code, 0) >= min_required_votes

    # 6. Phan quyet cuoi cung
    within_threshold = best_distance <= match_threshold
    is_match = (
        winning_code != "Unknown"
        and within_threshold
        and margin_satisfied
        and has_majority
    )

    if is_match:
        reject_reason = ""
    elif not within_threshold:
        reject_reason = "above_threshold"
    elif not margin_satisfied:
        reject_reason = "margin_gap"
    elif not has_majority:
        reject_reason = "no_majority"
    else:
        reject_reason = "unknown_label"

    predicted_code = winning_code if (has_majority or margin_satisfied) else best_candidate_code

    return {
        "predicted_code": predicted_code,
        "display_code": predicted_code if is_match else "Unknown",
        "confidence": best_distance,
        "match_threshold": match_threshold,
        "base_match_threshold": base_match_threshold,
        "is_match": is_match,
        "camera_profile": camera_profile,
        "reject_reason": reject_reason,
        "strategy": strategy,
    }


def encode_face_crop(face_image, locate_mode="full_crop"):
    """Tạo vector đặc trưng 128D từ ảnh khuôn mặt đã cắt (BGR hoặc xám).

    locate_mode:
    - "full_crop": dùng toàn bộ khung ảnh cắt làm vị trí khuôn mặt (mặc định
      của ứng dụng, nhanh hơn vì bỏ qua bước dò HOG).
    - "hog_redetect": dò lại khuôn mặt bằng HOG trong ảnh cắt (giống bước huấn
      luyện); nếu không thấy thì quay về toàn khung. Dùng cho thực nghiệm.
    Trả về (encoding hoặc None, lý do từ chối).
    """
    if face_image is None or getattr(face_image, "size", 0) == 0:
        return None, "invalid_image"
    if len(face_image.shape) == 2:
        rgb_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2RGB)
    else:
        rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

    # Anh qua dong nhat (den, trang, nhieu deu) -> tu choi som
    gray_img = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    if float(np.std(gray_img)) < STD_MIN_CONTRAST:
        return None, "low_contrast"

    face_locations = [(0, rgb_image.shape[1], rgb_image.shape[0], 0)]
    if locate_mode == "hog_redetect":
        detected = face_recognition.face_locations(rgb_image, model="hog")
        if detected:
            face_locations = [detected[0]]
    elif locate_mode != "full_crop":
        raise ValueError(f"Chế độ định vị không hợp lệ: {locate_mode}")

    face_encs = face_recognition.face_encodings(rgb_image, face_locations)
    if len(face_encs) == 0:
        return None, "no_encoding"
    return face_encs[0], ""


def predict_face(
    face_image,
    camera_index=None,
    strategy=STRATEGY_WEIGHTED_KNN,
    locate_mode="full_crop",
    threshold_override=None,
):
    """
    Nhận diện khuôn mặt bằng cách so sánh face encoding 128D.
    face_image: ảnh BGR của khuôn mặt đã crop.
    Trả về dict tương thích với giao diện cũ, bổ sung:
    - latency_ms: thời gian mã hóa + so khớp (mili giây)
    - reject_reason: lý do trả về Unknown (rỗng nếu khớp)
    """
    started = time.perf_counter()
    known_encodings, known_labels, label_to_code, metadata = load_model()

    face_encoding, reason = encode_face_crop(face_image, locate_mode=locate_mode)
    if face_encoding is None:
        result = _unknown_result(reason=reason)
    else:
        result = classify_encoding(
            face_encoding,
            known_encodings,
            known_labels,
            label_to_code,
            metadata,
            camera_index=camera_index,
            strategy=strategy,
            threshold_override=threshold_override,
        )
    result["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
    return result
