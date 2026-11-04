"""Đường dẫn dữ liệu dùng chung cho toàn bộ ứng dụng.

Đường dẫn được cố định theo thư mục gốc dự án (không phụ thuộc thư mục đang
đứng khi chạy lệnh) và có thể ghi đè bằng biến môi trường (dùng cho kiểm thử
cô lập hoặc khi triển khai) – xem ``.env.example``:
- SMART_ATTENDANCE_DATA_ROOT: thư mục gốc chứa dữ liệu (mặc định = thư mục dự án)
- SMART_ATTENDANCE_DB: đường dẫn tệp SQLite (mặc định = <DATA_ROOT>/attendance.db)
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_path(name, default):
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser().resolve() if value else default


DATA_ROOT = _env_path("SMART_ATTENDANCE_DATA_ROOT", PROJECT_ROOT)
DB_PATH = _env_path("SMART_ATTENDANCE_DB", DATA_ROOT / "attendance.db")
DATA_DIR = DATA_ROOT / "data"
FACE_DATASET_DIR = DATA_DIR / "faces"
MODELS_DIR = DATA_ROOT / "models"
BACKUP_DIR = DATA_ROOT / "backups"
RESEARCH_LOG_DIR = DATA_ROOT / "research_logs"
RESEARCH_RESULT_DIR = DATA_ROOT / "research_results"
STREAMLIT_CONFIG_PATH = PROJECT_ROOT / ".streamlit" / "config.toml"

# Tên dùng trong các module bổ sung ở phiên bản 1.1
FACES_DIR = FACE_DATASET_DIR
MODEL_DIR = MODELS_DIR


def ensure_runtime_directories() -> None:
    for path in (FACE_DATASET_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)
