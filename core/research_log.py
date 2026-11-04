"""Ghi nhật ký phục vụ nghiên cứu/thực nghiệm (không lưu ảnh).

Mỗi lần nhận diện và mỗi lần giáo viên xác nhận/điều chỉnh được ghi thành
một dòng CSV trong ``research_logs/``. Dữ liệu chỉ gồm mã học sinh (định danh
giả), khoảng cách, ngưỡng, thời gian xử lý — KHÔNG lưu ảnh hay vector khuôn mặt.

Mục đích: đo trong điều kiện sử dụng thực tế (Hướng B, C của kế hoạch nghiên cứu):
- thời gian xử lý mỗi lần nhận diện (latency_ms),
- tỷ lệ trả về Unknown và lý do (above_threshold, margin_gap, ...),
- tỷ lệ kết quả nhận diện được giáo viên chấp nhận hoặc phải điều chỉnh.

Tắt ghi log: đặt biến môi trường SMART_ATTENDANCE_RESEARCH_LOG=0.
"""

import csv
import os
import threading
from datetime import datetime

from core.paths import RESEARCH_LOG_DIR

RECOGNITION_LOG = "recognition_events.csv"
DECISION_LOG = "teacher_decisions.csv"

RECOGNITION_FIELDS = [
    "timestamp",
    "source",
    "camera_index",
    "strategy",
    "predicted_code",
    "display_code",
    "is_match",
    "distance",
    "match_threshold",
    "reject_reason",
    "latency_ms",
]
DECISION_FIELDS = [
    "timestamp",
    "source",
    "action",
    "attendance_type",
    "method",
    "predicted_code",
    "final_code",
    "distance",
    "note",
]

_lock = threading.Lock()


def is_enabled():
    return os.environ.get("SMART_ATTENDANCE_RESEARCH_LOG", "1").strip() not in {"0", "false", "no"}


def _append(filename, fields, row):
    if not is_enabled():
        return
    try:
        RESEARCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = RESEARCH_LOG_DIR / filename
        with _lock:
            new_file = not path.exists()
            with open(path, "a", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                if new_file:
                    writer.writeheader()
                writer.writerow(row)
    except OSError as error:
        # Ghi log không được làm hỏng luồng điểm danh chính
        print(f"[research_log] Không thể ghi log: {error}")


def _now():
    return datetime.now().isoformat(timespec="milliseconds")


def log_recognition_event(result, source, camera_index=None):
    if not result:
        return
    distance = result.get("confidence")
    _append(
        RECOGNITION_LOG,
        RECOGNITION_FIELDS,
        {
            "timestamp": _now(),
            "source": source,
            "camera_index": "" if camera_index is None else camera_index,
            "strategy": result.get("strategy", ""),
            "predicted_code": result.get("predicted_code", ""),
            "display_code": result.get("display_code", ""),
            "is_match": int(bool(result.get("is_match"))),
            "distance": "" if distance is None else round(float(distance), 4),
            "match_threshold": result.get("match_threshold", ""),
            "reject_reason": result.get("reject_reason", result.get("error", "")),
            "latency_ms": result.get("latency_ms", ""),
        },
    )


def log_teacher_decision(
    source,
    action,
    attendance_type="",
    method="",
    predicted_code="",
    final_code="",
    distance=None,
    note="",
):
    """action: confirm (xác nhận kết quả nhận diện), manual (ghi thủ công),
    correct (điều chỉnh kết quả đã lưu)."""
    _append(
        DECISION_LOG,
        DECISION_FIELDS,
        {
            "timestamp": _now(),
            "source": source,
            "action": action,
            "attendance_type": attendance_type,
            "method": method,
            "predicted_code": predicted_code or "",
            "final_code": final_code or "",
            "distance": "" if distance is None else round(float(distance), 4),
            "note": note,
        },
    )


def logged_predictor(predict_fn, source):
    """Bọc hàm nhận diện để tự động ghi log mỗi lần gọi (an toàn luồng)."""

    def _predict(face_image, **kwargs):
        result = predict_fn(face_image, **kwargs)
        log_recognition_event(result, source, kwargs.get("camera_index"))
        return result

    return _predict


def read_log(filename):
    """Đọc log thành DataFrame (rỗng nếu chưa có)."""
    import pandas as pd

    path = RESEARCH_LOG_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")
