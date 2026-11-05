"""Kiểm thử công cụ đổi mã học sinh trên dữ liệu tạm (không chạm DB thật)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

if not os.environ.get("SMART_ATTENDANCE_DATA_ROOT"):
    os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_rename_test_")
os.environ["SMART_ATTENDANCE_RESEARCH_LOG"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sqlite3  # noqa: E402

from core import paths  # noqa: E402
from core.research_log import log_teacher_decision  # noqa: E402
from db.attendance_repo import record_student_attendance  # noqa: E402
from db.database import create_class, create_student  # noqa: E402
from scripts import rename_student_code as tool  # noqa: E402


class RenameStudentCodeTests(unittest.TestCase):
    def test_rename_updates_all_locations(self):
        self.assertNotEqual(paths.DATA_ROOT, paths.PROJECT_ROOT)
        class_row = create_class("Lớp kiểm thử đổi mã")
        class_id = class_row["id"] if isinstance(class_row, dict) else class_row
        student = create_student("Học sinh đổi mã", class_id, student_code="XX901")
        code = student["student_code"] if isinstance(student, dict) else "XX901"
        record_student_attendance(code, class_id, "2026-11-01", "Buổi sáng", "Có mặt", method="manual")
        face_dir = paths.FACE_DATASET_DIR / code
        face_dir.mkdir(parents=True, exist_ok=True)
        (face_dir / "1.jpg").write_bytes(b"x")
        log_teacher_decision("unit", "manual", "IN", "manual", final_code=code)

        with self.assertRaises(SystemExit):  # sai định dạng mã mới
            tool.main([code, "AB12", "--no-backup"])
        dry = tool.main([code, "HS901"])
        self.assertEqual(dry["students"], 1)
        conn = sqlite3.connect(paths.DB_PATH)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM students WHERE student_code=?", (code,)).fetchone()[0], 1)
        conn.close()

        tool.main([code, "HS901", "--apply", "--no-backup"])
        conn = sqlite3.connect(paths.DB_PATH)
        for table, column in (("students", "student_code"), ("employees", "employee_code")):
            self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column}='HS901'").fetchone()[0], 1)
            self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column}=?", (code,)).fetchone()[0], 0)
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE employee_code='HS901' AND student_code='HS901'").fetchone()[0], 1)
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE employee_code=? OR student_code=?", (code, code)).fetchone()[0], 0)
        conn.close()
        self.assertTrue((paths.FACE_DATASET_DIR / "HS901" / "1.jpg").exists())
        self.assertFalse(face_dir.exists())
        log_text = (paths.RESEARCH_LOG_DIR / "teacher_decisions.csv").read_text(encoding="utf-8-sig")
        self.assertIn("HS901", log_text)
        self.assertNotIn(code, log_text)

        with self.assertRaises(SystemExit):  # mã mới đã tồn tại
            tool.main(["HS901", "HS901"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
