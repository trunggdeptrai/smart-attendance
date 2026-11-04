"""Khôi phục dữ liệu Smart Attendance từ tệp ZIP sao lưu.

Cách dùng (DỪNG ỨNG DỤNG TRƯỚC):
    python scripts/restore_backup.py backups/smart_attendance_backup_YYYYMMDD-HHMMSS.zip
    python scripts/restore_backup.py --list
    python scripts/restore_backup.py --verify <tệp.zip>

Trước khi ghi đè, công cụ tự tạo bản sao lưu an toàn "..._before-restore.zip".
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.backup import create_backup, list_backups, restore_backup, verify_backup  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip_path", nargs="?")
    parser.add_argument("--list", action="store_true", help="Liệt kê bản sao lưu")
    parser.add_argument("--verify", action="store_true", help="Chỉ kiểm tra tính toàn vẹn")
    parser.add_argument("--create", action="store_true", help="Tạo bản sao lưu mới")
    parser.add_argument("--yes", action="store_true", help="Không hỏi xác nhận")
    args = parser.parse_args()

    if args.create:
        print(f"Đã tạo: {create_backup()}")
        return
    if args.list:
        for path in list_backups():
            print(path)
        return
    if not args.zip_path:
        parser.error("Cần đường dẫn tệp sao lưu.")
    manifest = verify_backup(args.zip_path)
    print(f"Bản sao lưu hợp lệ: tạo lúc {manifest.get('created_at')}, "
          f"{manifest.get('face_files')} ảnh mẫu, {manifest.get('model_files')} tệp mô hình.")
    if args.verify:
        return
    if not args.yes:
        answer = input("Dữ liệu hiện tại sẽ bị thay thế (đã có sao lưu an toàn). Gõ 'dong y' để tiếp tục: ")
        if answer.strip().lower() not in {"dong y", "đồng ý"}:
            print("Đã huỷ.")
            return
    safety = restore_backup(args.zip_path)
    print(f"Đã khôi phục. Bản sao lưu an toàn trước khi khôi phục: {safety}")


if __name__ == "__main__":
    main()
