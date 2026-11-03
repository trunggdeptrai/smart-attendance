import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from collections import namedtuple
import sys
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from streamlit.testing.v1 import AppTest

import check_environment
from core.dataframes import records_to_dataframe
from core.face_dataset import list_employee_folders
from core.face_detect import detect_faces
from core.paths import FACE_DATASET_DIR, MODELS_DIR, PROJECT_ROOT
from core.runtime_compat import runtime_compatibility_error


class StabilityTests(unittest.TestCase):
    def test_empty_records_keep_declared_dataframe_columns(self):
        columns = ["Mã lớp", "Tên lớp"]

        for records in ([], None):
            with self.subTest(records=records):
                frame = records_to_dataframe(records, columns)
                self.assertTrue(frame.empty)
                self.assertEqual(frame.columns.tolist(), columns)

    def test_records_with_missing_fields_have_equal_dataframe_columns(self):
        frame = records_to_dataframe(
            [{"Mã lớp": "10A1"}, {"Tên lớp": "Lớp 10A2"}],
            ["Mã lớp", "Tên lớp"],
        )

        self.assertEqual(frame.shape, (2, 2))
        self.assertEqual(frame.iloc[0]["Mã lớp"], "10A1")
        self.assertTrue(pd.isna(frame.iloc[0]["Tên lớp"]))
        self.assertEqual(frame.iloc[1]["Tên lớp"], "Lớp 10A2")

    def test_runtime_guard_reports_unsupported_python_and_broken_numpy(self):
        def broken_arange(*_args, **_kwargs):
            raise ValueError("arange: cannot compute length")

        python_error = runtime_compatibility_error((3, 15, 2), np.arange)
        numpy_error = runtime_compatibility_error(
            (3, 11, 9),
            broken_arange,
        )

        self.assertIn("Python 3.11.x", python_error)
        self.assertIn("arange: cannot compute length", numpy_error)
        self.assertIsNone(runtime_compatibility_error((3, 11, 9), np.arange))

    def test_attendance_summary_handles_legacy_row_without_date(self):
        from db import attendance_repo

        raw_records = pd.DataFrame(
            [
                {
                    "id": 1,
                    "student_code": "HS001",
                    "student_name": "Nguyen An",
                    "class_name": "10A1",
                    "attendance_date": None,
                    "session_name": None,
                    "attendance_status": "Có mặt",
                    "attendance_type": "IN",
                    "log_time": "2026-11-03 08:00:00",
                }
            ]
        )
        with patch.object(
            attendance_repo,
            "get_student_attendance_dataframe",
            return_value=raw_records,
        ):
            summary = (
                attendance_repo.get_student_attendance_summary_dataframe.__wrapped__(
                    None, None
                )
            )

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary.iloc[0]["attendance_date"], "2026-11-03")
        self.assertEqual(summary.iloc[0]["session_name"], "Dữ liệu cũ")
        self.assertEqual(summary.iloc[0]["check_in_time"], "08:00:00")

    def test_database_initialization_is_idempotent_and_preserves_rows(self):
        from db import session as database_session

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "attendance.db"
            test_engine = create_engine(f"sqlite:///{database_path}")
            try:
                with (
                    patch.object(database_session, "DB_PATH", database_path),
                    patch.object(database_session, "engine", test_engine),
                ):
                    database_session.init_db()
                    with test_engine.begin() as connection:
                        connection.execute(
                            text(
                                "INSERT INTO classes (class_code, name, active) "
                                "VALUES ('TEST-001', 'Lớp kiểm thử', 1)"
                            )
                        )

                    database_session.init_db()
                    with test_engine.connect() as connection:
                        class_name = connection.execute(
                            text(
                                "SELECT name FROM classes "
                                "WHERE class_code = 'TEST-001'"
                            )
                        ).scalar_one()
                        migration_versions = connection.execute(
                            text("SELECT version FROM schema_migrations ORDER BY version")
                        ).scalars().all()
                        attendance_count = connection.execute(
                            text("SELECT COUNT(*) FROM attendance_logs")
                        ).scalar_one()

                self.assertEqual(class_name, "Lớp kiểm thử")
                self.assertEqual(migration_versions, [1, 2, 3])
                self.assertEqual(attendance_count, 0)
            finally:
                test_engine.dispose()

    def test_face_dataset_empty_scope_does_not_read_other_folders(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "HS001").mkdir()
            (root / "HS002").mkdir()

            with patch("core.face_dataset.DATASET_DIR", root):
                self.assertEqual(list_employee_folders(valid_employee_codes=[]), [])
                self.assertEqual(
                    [folder.name for folder in list_employee_folders()],
                    ["HS001", "HS002"],
                )

    def test_face_detection_handles_missing_or_empty_image(self):
        self.assertEqual(detect_faces(None), ([], None))
        self.assertEqual(detect_faces(np.empty((0, 0, 3), dtype=np.uint8)), ([], None))

    def test_project_data_paths_do_not_depend_on_current_directory(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                self.assertEqual(FACE_DATASET_DIR, PROJECT_ROOT / "data" / "faces")
                self.assertEqual(MODELS_DIR, PROJECT_ROOT / "models")
                self.assertTrue(PROJECT_ROOT.is_absolute())
            finally:
                os.chdir(original_directory)

    def test_preflight_reports_missing_config_and_directories_without_creating_them(self):
        version_info = namedtuple("version_info", "major minor micro")
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            output = io.StringIO()
            with (
                patch.object(check_environment, "PROJECT_ROOT", project_root),
                patch.object(sys, "version_info", version_info(3, 11, 0)),
                patch.object(sys, "argv", ["check_environment.py"]),
                redirect_stdout(output),
            ):
                exit_code = check_environment.main()

            self.assertEqual(exit_code, 1)
            self.assertIn("Thiếu .streamlit/config.toml", output.getvalue())
            self.assertIn("Thiếu thư mục data", output.getvalue())
            self.assertIn("Thiếu thư mục models", output.getvalue())
            self.assertFalse((project_root / "data").exists())
            self.assertFalse((project_root / "models").exists())
            self.assertFalse((project_root / "attendance.db").exists())

    def test_classes_page_displays_empty_dataframe_and_guidance(self):
        page_path = PROJECT_ROOT / "pages" / "8_Classes.py"
        with (
            patch("db.database.get_classes", return_value=[]),
            patch("db.database.get_teachers", return_value=[]),
        ):
            app = AppTest.from_file(str(page_path), default_timeout=30).run()

        self.assertEqual([str(item.value) for item in app.exception], [])
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(
            app.dataframe[0].value.columns.tolist(),
            ["Mã lớp", "Tên lớp", "Giáo viên chủ nhiệm", "Trạng thái"],
        )
        self.assertTrue(
            any("Chưa có lớp học" in item.value for item in app.info)
        )

    def test_empty_dashboard_displays_guidance_without_exception(self):
        page_path = PROJECT_ROOT / "pages" / "1_Dashboard.py"
        with (
            patch(
                "db.attendance_repo.get_student_attendance_dataframe",
                return_value=pd.DataFrame(),
            ),
            patch(
                "db.database.get_student_dataframe",
                return_value=pd.DataFrame(columns=["Mã học sinh"]),
            ),
            patch("db.database.get_classes", return_value=[]),
        ):
            app = AppTest.from_file(str(page_path), default_timeout=30).run()

        self.assertEqual([str(item.value) for item in app.exception], [])
        self.assertEqual(len(app.dataframe), 0)
        self.assertTrue(
            any("Chưa có dữ liệu chấm công" in item.value for item in app.info)
        )

    def test_history_and_attendance_report_render_records_and_exports(self):
        page_paths = (
            PROJECT_ROOT / "pages" / "5_History.py",
            PROJECT_ROOT / "pages" / "9_Attendance_Report.py",
        )
        records = pd.DataFrame(
            [
                {
                    "student_code": "HS001",
                    "student_name": "Nguyen An",
                    "class_name": "10A1",
                    "attendance_date": "2026-11-03",
                    "session_name": "Buổi sáng",
                    "check_in_time": "08:00:00",
                    "check_out_time": None,
                    "attendance_status": "Có mặt",
                    "attendance_state": "Còn thiếu lượt ra",
                }
            ]
        )
        student = SimpleNamespace(
            student_code="HS001",
            full_name="Nguyen An",
            class_name="10A1",
            class_id=1,
        )

        for page_path in page_paths:
            with (
                self.subTest(page=page_path.name),
                patch(
                    "db.attendance_repo.get_student_attendance_summary_dataframe",
                    return_value=records,
                ),
                patch("db.database.get_classes", return_value=[]),
                patch("db.database.get_students", return_value=[student]),
            ):
                app = AppTest.from_file(str(page_path), default_timeout=30).run()

            self.assertEqual([str(item.value) for item in app.exception], [])
            self.assertEqual(len(app.dataframe), 1)
            self.assertEqual(len(app.get("download_button")), 2)


if __name__ == "__main__":
    unittest.main()
