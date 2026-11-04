"""Đường dẫn dữ liệu dùng chung cho toàn bộ ứng dụng.

Trước đây các module dùng đường dẫn tương đối (``Path("models")``,
``Path("data/faces")``) nên phụ thuộc vào thư mục đang đứng khi chạy lệnh.
Module này cố định đường dẫn theo thư mục gốc dự án và cho phép ghi đè
bằng biến môi trường (dùng cho kiểm thử cô lập hoặc khi triển khai).

Biến môi trường hỗ trợ (xem ``.env.example``):
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
FACES_DIR = DATA_ROOT / "data" / "faces"
MODEL_DIR = DATA_ROOT / "models"
BACKUP_DIR = DATA_ROOT / "backups"
RESEARCH_LOG_DIR = DATA_ROOT / "research_logs"
RESEARCH_RESULT_DIR = DATA_ROOT / "research_results"
