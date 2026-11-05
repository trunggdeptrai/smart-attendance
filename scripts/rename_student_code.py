"""Đổi mã một học sinh, đồng bộ trên toàn bộ dữ liệu.

Cập nhật trong một giao dịch SQLite:
  students.student_code, employees.employee_code (bảng định danh kỹ thuật),
  attendance_logs.employee_code, attendance_logs.student_code
và ngoài cơ sở dữ liệu:
  thư mục ảnh mẫu data/faces/<mã>/, các tệp CSV trong research_logs/.

Mặc định chỉ CHẠY THỬ (in ra những gì sẽ thay đổi). Thêm --apply để thực hiện;
khi đó luôn tạo bản sao lưu ZIP trước (khôi phục bằng scripts/restore_backup.py).
Dừng ứng dụng trước khi chạy. Sau khi đổi mã cần huấn luyện lại mô hình (--retrain).

Ví dụ:
    python scripts/rename_student_code.py NV001 HS047            # chạy thử
    python scripts/rename_student_code.py NV001 HS047 --apply --retrain
"""

import argparse
import csv
import re
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.paths import DB_PATH, FACE_DATASET_DIR, RESEARCH_LOG_DIR  # noqa: E402

CODE_PATTERN = re.compile(r"^HS\d{3,}$")
CSV_CODE_FIELDS = ("predicted_code", "display_code", "final_code")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def plan(connection, old, new):
    counts = {
        "students": connection.execute("SELECT COUNT(*) FROM students WHERE student_code=?", (old,)).fetchone()[0],
        "employees": connection.execute("SELECT COUNT(*) FROM employees WHERE employee_code=?", (old,)).fetchone()[0],
        "attendance_logs.employee_code": connection.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE employee_code=?", (old,)).fetchone()[0],
        "attendance_logs.student_code": connection.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE student_code=?", (old,)).fetchone()[0],
    }
    old_dir = FACE_DATASET_DIR / old
    counts["ảnh mẫu"] = len([p for p in old_dir.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS]) if old_dir.exists() else 0
    return counts


def validate(connection, old, new, allow_any_format=False):
    if old == new:
        raise SystemExit("Mã cũ và mã mới giống nhau.")
    if not allow_any_format and not CODE_PATTERN.match(new):
        raise SystemExit("Mã mới phải có dạng HS + ít nhất 3 chữ số (vd HS047).")
    if connection.execute("SELECT 1 FROM students WHERE student_code=?", (old,)).fetchone() is None:
        raise SystemExit(f"Không tìm thấy học sinh mã {old}.")
    for table, column in (("students", "student_code"), ("employees", "employee_code")):
        if connection.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (new,)).fetchone():
            raise SystemExit(f"Mã {new} đã tồn tại trong bảng {table}.")
    if connection.execute(
        "SELECT 1 FROM attendance_logs WHERE employee_code=? OR student_code=?", (new, new)
    ).fetchone():
        raise SystemExit(f"Mã {new} đã xuất hiện trong lịch sử điểm danh.")
    new_dir = FACE_DATASET_DIR / new
    if new_dir.exists() and any(new_dir.iterdir()):
        raise SystemExit(f"Thư mục ảnh {new_dir} đã có tệp – kiểm tra thủ công trước.")


def rename_database(connection, old, new):
    with connection:  # một giao dịch: lỗi ở bất kỳ bước nào sẽ hoàn tác toàn bộ
        connection.execute("UPDATE employees SET employee_code=? WHERE employee_code=?", (new, old))
        connection.execute("UPDATE students SET student_code=? WHERE student_code=?", (new, old))
        connection.execute("UPDATE attendance_logs SET employee_code=? WHERE employee_code=?", (new, old))
        connection.execute("UPDATE attendance_logs SET student_code=? WHERE student_code=?", (new, old))


def rename_face_folder(old, new):
    old_dir, new_dir = FACE_DATASET_DIR / old, FACE_DATASET_DIR / new
    if not old_dir.exists():
        return False
    if new_dir.exists():
        new_dir.rmdir()  # đã kiểm tra là thư mục rỗng
    shutil.move(str(old_dir), str(new_dir))
    return True


def rename_in_logs(old, new):
    changed = 0
    for path in sorted(RESEARCH_LOG_DIR.glob("*.csv")) if RESEARCH_LOG_DIR.exists() else []:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            rows = list(reader)
        file_changed = 0
        for row in rows:
            for field in CSV_CODE_FIELDS:
                if row.get(field) == old:
                    row[field] = new
                    file_changed += 1
        if file_changed:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            changed += file_changed
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old_code")
    parser.add_argument("new_code")
    parser.add_argument("--apply", action="store_true", help="Thực hiện (mặc định chỉ chạy thử)")
    parser.add_argument("--retrain", action="store_true", help="Huấn luyện lại mô hình sau khi đổi mã")
    parser.add_argument("--no-backup", action="store_true", help="Bỏ qua sao lưu (chỉ dùng trong kiểm thử)")
    args = parser.parse_args(argv)
    old, new = args.old_code.strip().upper(), args.new_code.strip().upper()

    connection = sqlite3.connect(str(DB_PATH))
    try:
        validate(connection, old, new)
        counts = plan(connection, old, new)
        print(f"Đổi mã học sinh {old} -> {new} trong {DB_PATH}")
        for name, value in counts.items():
            print(f"  {name:<32} {value}")
        if not args.apply:
            print("\nChạy thử – chưa thay đổi gì. Thêm --apply để thực hiện.")
            return counts

        if not args.no_backup:
            from core.backup import create_backup

            print(f"Đã sao lưu: {create_backup(label=f'before-rename-{old}-{new}')}")
        rename_database(connection, old, new)
    finally:
        connection.close()

    moved = rename_face_folder(old, new)
    log_rows = rename_in_logs(old, new)
    print(f"Đã cập nhật cơ sở dữ liệu; thư mục ảnh: {'đã đổi tên' if moved else 'không có'}; "
          f"nhật ký CSV: {log_rows} ô.")

    if args.retrain:
        from core.face_recognizer import train_model

        result = train_model()
        print(f"Đã huấn luyện lại: {result['num_images']} ảnh, {result['num_people']} học sinh.")
    else:
        print("Nhớ huấn luyện lại mô hình (trang Đăng ký khuôn mặt hoặc --retrain).")
    return counts


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
