"""Kiểm thử nhập ngày sinh học sinh (3 ô chọn) trên dữ liệu tạm – không chạm DB thật."""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

if not os.environ.get("SMART_ATTENDANCE_DATA_ROOT"):
    os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_birth_test_")
os.environ.setdefault("SMART_ATTENDANCE_RESEARCH_LOG", "0")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import paths  # noqa: E402
from core.birth_date import (  # noqa: E402
    DEFAULT_BIRTH_DATE,
    EMPTY,
    MIN_BIRTH_DATE,
    compose_birth_date,
    year_options,
)
from core.timeutil import today_vn  # noqa: E402
from db.database import create_class, create_student, get_students, update_student  # noqa: E402

TODAY = date(2026, 11, 7)


class ComposeBirthDateTests(unittest.TestCase):
    def test_valid_dates(self):
        for d, m, y in ((23, 8, 2010), (15, 9, 2008), (1, 1, 2011), (29, 2, 2012)):
            self.assertEqual(compose_birth_date(d, m, y, today=TODAY), date(y, m, d))

    def test_invalid_calendar_dates(self):
        for d, m, y in ((29, 2, 2011), (31, 4, 2010), (31, 2, 2012), (32, 1, 2010)):
            with self.assertRaises(ValueError):
                compose_birth_date(d, m, y, today=TODAY)

    def test_future_date_rejected(self):
        with self.assertRaises(ValueError):
            compose_birth_date(8, 11, 2026, today=TODAY)
        self.assertEqual(compose_birth_date(7, 11, 2026, today=TODAY), TODAY)

    def test_before_minimum_rejected(self):
        with self.assertRaises(ValueError):
            compose_birth_date(31, 12, 1989, today=TODAY)
        self.assertEqual(compose_birth_date(1, 1, 1990, today=TODAY), MIN_BIRTH_DATE)

    def test_empty_and_partial(self):
        self.assertIsNone(compose_birth_date(EMPTY, EMPTY, EMPTY, today=TODAY))
        with self.assertRaises(ValueError):
            compose_birth_date(23, EMPTY, 2010, today=TODAY)

    def test_year_options(self):
        years = year_options(today=TODAY)
        self.assertEqual(years[0], 2026)
        self.assertEqual(years[-1], 1990)
        self.assertIn(DEFAULT_BIRTH_DATE.year, years)
        self.assertEqual(len(years), 37)


class StudentBirthDatePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert paths.DATA_ROOT != paths.PROJECT_ROOT, "Kiểm thử phải chạy trên dữ liệu tạm"
        row = create_class("Lớp kiểm thử ngày sinh")
        cls.class_id = row["id"] if isinstance(row, dict) else row

    def _find(self, code):
        get_students.clear()
        return next(r for r in get_students(active_only=False) if r.student_code == code)

    def test_save_read_and_edit(self):
        code = create_student("Học sinh ngày sinh", self.class_id, compose_birth_date(23, 8, 2010), student_code="BD901")
        code = code["student_code"] if isinstance(code, dict) else code
        stored = self._find(code)
        self.assertEqual(stored.date_of_birth, date(2010, 8, 23))
        self.assertIsInstance(stored.date_of_birth, date)

        update_student(stored.id, stored.full_name, self.class_id, "Đang học", compose_birth_date(29, 2, 2012))
        self.assertEqual(self._find(code).date_of_birth, date(2012, 2, 29))

        update_student(stored.id, stored.full_name, self.class_id, "Đang học", None)
        self.assertIsNone(self._find(code).date_of_birth)

    def test_database_rejects_future_and_accepts_text(self):
        with self.assertRaises(ValueError):
            create_student("Tương lai", self.class_id, today_vn() + timedelta(days=1), student_code="BD902")
        code = create_student("Nhập Excel", self.class_id, "15/09/2008", student_code="BD903")
        code = code["student_code"] if isinstance(code, dict) else code
        self.assertEqual(self._find(code).date_of_birth, date(2008, 9, 15))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
