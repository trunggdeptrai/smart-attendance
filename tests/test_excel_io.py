"""Kiểm thử xuất báo cáo Excel và định dạng tệp nhập danh sách học sinh."""

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from core.attendance_export import EXPORT_COLUMNS, build_attendance_excel  # noqa: E402


class ExcelExportTests(unittest.TestCase):
    def test_export_contains_student_rows(self):
        records = pd.DataFrame([
            {"Mã học sinh": "HS001", "Họ và tên": "Học sinh A", "Lớp": "10A1", "Ngày": "2026-11-02",
             "Giờ vào": "07:01:00", "Giờ ra": None, "Trạng thái": "Có mặt"},
            {"Mã học sinh": "HS002", "Họ và tên": "Học sinh B", "Lớp": "10A1", "Ngày": "2026-11-02",
             "Giờ vào": None, "Giờ ra": None, "Trạng thái": "Vắng mặt"},
        ])
        workbook = load_workbook(io.BytesIO(build_attendance_excel(records, "BÁO CÁO THỬ")))
        sheet = workbook.active
        self.assertEqual([c.value for c in sheet[3]], EXPORT_COLUMNS)
        self.assertEqual(sheet["B4"].value, "HS001")
        self.assertEqual(sheet["B5"].value, "HS002")
        self.assertEqual(sheet["G4"].value, "Chưa ghi nhận")  # giờ ra trống
        self.assertEqual(sheet["H5"].value, "Vắng mặt")

    def test_export_rejects_empty(self):
        with self.assertRaises(ValueError):
            build_attendance_excel(pd.DataFrame(columns=EXPORT_COLUMNS[1:]), "Trống")


class ExcelImportFormatTests(unittest.TestCase):
    def test_import_template_has_required_columns(self):
        buffer = io.BytesIO()
        pd.DataFrame({"Họ và tên": ["Học sinh C"], "Mã lớp": ["L001"], "Ngày sinh": ["2010-05-01"]}).to_excel(
            buffer, index=False)
        buffer.seek(0)
        frame = pd.read_excel(buffer)  # giống cách trang Quản lý học sinh đọc tệp
        self.assertTrue({"Họ và tên", "Mã lớp"}.issubset(frame.columns))
        self.assertEqual(frame.loc[0, "Họ và tên"], "Học sinh C")


if __name__ == "__main__":
    unittest.main(verbosity=2)
