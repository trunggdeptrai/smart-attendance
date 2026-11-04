"""Sao lưu và khôi phục dữ liệu ứng dụng.

Bản sao lưu là một tệp ZIP gồm:
- attendance.db  (chụp nhất quán bằng SQLite Online Backup API, an toàn khi app đang chạy)
- data/faces/... (ảnh mẫu khuôn mặt)
- models/...     (embeddings, nhãn, metadata)
- research_logs/... (nhật ký thực nghiệm, nếu có)
- manifest.json  (thời điểm, số lượng tệp, kiểm tra toàn vẹn SHA-256 của DB)

CẢNH BÁO: bản sao lưu chứa dữ liệu sinh trắc học và thông tin cá nhân.
Chỉ lưu ở nơi riêng tư, không đưa lên GitHub hoặc kênh công khai.
"""

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from core.paths import BACKUP_DIR, DATA_ROOT, DB_PATH, FACES_DIR, MODEL_DIR, RESEARCH_LOG_DIR

BACKUP_PREFIX = "smart_attendance_backup_"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_database(target_path):
    """Sao chép DB nhất quán (kể cả khi đang có kết nối khác)."""
    source = sqlite3.connect(str(DB_PATH))
    try:
        destination = sqlite3.connect(str(target_path))
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


def _add_tree(archive, folder, arc_root):
    count = 0
    folder = Path(folder)
    if not folder.exists():
        return 0
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            archive.write(path, f"{arc_root}/{path.relative_to(folder).as_posix()}")
            count += 1
    return count


def create_backup(destination_dir=None, label=""):
    """Tạo bản sao lưu ZIP và trả về đường dẫn tệp."""
    destination_dir = Path(destination_dir or BACKUP_DIR)
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"_{label}" if label else ""
    zip_path = destination_dir / f"{BACKUP_PREFIX}{stamp}{suffix}.zip"

    with tempfile.TemporaryDirectory() as tmp:
        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "app": "smart-attendance",
            "format_version": 1,
            "has_database": False,
        }
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if DB_PATH.exists():
                db_copy = Path(tmp) / "attendance.db"
                _snapshot_database(db_copy)
                archive.write(db_copy, "attendance.db")
                manifest["has_database"] = True
                manifest["database_sha256"] = _sha256(db_copy)
            manifest["face_files"] = _add_tree(archive, FACES_DIR, "data/faces")
            manifest["model_files"] = _add_tree(archive, MODEL_DIR, "models")
            manifest["research_log_files"] = _add_tree(archive, RESEARCH_LOG_DIR, "research_logs")
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return zip_path


def list_backups(directory=None):
    directory = Path(directory or BACKUP_DIR)
    if not directory.exists():
        return []
    return sorted(directory.glob(f"{BACKUP_PREFIX}*.zip"), reverse=True)


def read_manifest(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        return json.loads(archive.read("manifest.json").decode("utf-8"))


def verify_backup(zip_path):
    """Kiểm tra tệp ZIP đọc được, có manifest và DB khớp SHA-256."""
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Tệp sao lưu bị hỏng tại: {bad}")
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        if manifest.get("has_database"):
            digest = hashlib.sha256(archive.read("attendance.db")).hexdigest()
            if digest != manifest.get("database_sha256"):
                raise ValueError("Cơ sở dữ liệu trong bản sao lưu không khớp mã kiểm tra.")
    return manifest


def restore_backup(zip_path, make_safety_backup=True):
    """Khôi phục dữ liệu từ ZIP. LUÔN tạo bản sao lưu an toàn trước khi ghi đè.

    Chỉ nên chạy khi ứng dụng đã dừng (xem scripts/restore_backup.py).
    Trả về đường dẫn bản sao lưu an toàn (hoặc None).
    """
    zip_path = Path(zip_path)
    manifest = verify_backup(zip_path)
    safety = create_backup(label="before-restore") if make_safety_backup else None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.namelist():
                target = (tmp_root / member).resolve()
                if not str(target).startswith(str(tmp_root.resolve())):
                    raise ValueError(f"Đường dẫn không an toàn trong bản sao lưu: {member}")
            archive.extractall(tmp_root)

        if manifest.get("has_database"):
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp_root / "attendance.db", DB_PATH)
        for arc_dir, live_dir in (
            ("data/faces", FACES_DIR),
            ("models", MODEL_DIR),
            ("research_logs", RESEARCH_LOG_DIR),
        ):
            source_dir = tmp_root / arc_dir
            if source_dir.exists():
                if live_dir.exists():
                    shutil.rmtree(live_dir)
                shutil.copytree(source_dir, live_dir)
    return safety


__all__ = [
    "create_backup",
    "list_backups",
    "read_manifest",
    "verify_backup",
    "restore_backup",
    "DATA_ROOT",
]
