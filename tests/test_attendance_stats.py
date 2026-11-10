"""Kiểm thử thống kê sĩ số và lượt điểm danh (trang Lịch sử, Báo cáo chuyên cần) trên dữ liệu tạm.

Các con số trong tệp này là dữ liệu kiểm thử tình huống, không phải kết quả thực nghiệm của dự án.
Tệp không chạm cơ sở dữ liệu thật: tự tạo thư mục dữ liệu tạm khi chạy riêng, hoặc dùng bản sao
do tests/run_all.py chuẩn bị (bản sao có thể đã có dữ liệu, nên mọi phép so sánh đều theo lớp
do chính tệp này tạo hoặc đối chiếu với truy vấn SQL độc lập).
"""

import os
import sys
import tempfile
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

if not os.environ.get("SMART_ATTENDANCE_DATA_ROOT"):
    os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_stats_test_")
os.environ.setdefault("SMART_ATTENDANCE_RESEARCH_LOG", "0")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from core.attendance_stats import (  # noqa: E402
    active_roster_codes,
    compute_attendance_stats,
    describe_scope,
    filter_attendance_events,
    filter_attendance_summary,
)
from core.timeutil import today_vn  # noqa: E402
from db.attendance_repo import (  # noqa: E402
    clear_attendance_cache,
    get_student_attendance_dataframe,
    get_student_attendance_summary_dataframe,
    record_student_attendance,
)
from db.database import create_class, create_student, get_students, update_student  # noqa: E402
from db.session import engine  # noqa: E402

TODAY = today_vn()
D1, D2, D3 = TODAY - timedelta(days=3), TODAY - timedelta(days=2), TODAY - timedelta(days=1)
SUFFIX = uuid.uuid4().hex[:6].upper()


def _event(event_id, code, log_type="IN", status="Có mặt", session="Buổi sáng"):
    return {"id": event_id, "student_code": code, "attendance_type": log_type,
            "attendance_status": status, "session_name": session}


def _summary_row(code, status, session="Buổi sáng", check_out=None):
    return {"student_code": code, "session_name": session, "attendance_status": status,
            "check_in_time": None if status in ("Vắng mặt", "Chưa ghi nhận") else "07:00:00",
            "check_out_time": check_out}


class PureStatsTests(unittest.TestCase):
    """Hàm thuần: không cần cơ sở dữ liệu."""

    def test_counts_unique_students_not_rows(self):
        events = pd.DataFrame([_event(1, "HS001"), _event(2, "HS001", "OUT"),
                               _event(3, "HS001", session="Buổi chiều")])
        summary = pd.DataFrame([_summary_row("HS001", "Có mặt", check_out="11:00:00"),
                                _summary_row("HS001", "Có mặt", "Buổi chiều")])
        stats = compute_attendance_stats(["HS001", "HS002", "HS003"], events, summary)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (3, 1, 2))
        self.assertEqual(stats["events"], 3)  # ba lượt nhưng chỉ một học sinh
        self.assertEqual(stats["by_status"]["Có mặt"], 1)

    def test_duplicate_event_ids_are_counted_once(self):
        # Mô phỏng JOIN nhân đôi bản ghi: cùng một id xuất hiện hai lần.
        events = pd.DataFrame([_event(7, "HS001"), _event(7, "HS001"), _event(8, "HS002")])
        stats = compute_attendance_stats(["HS001", "HS002"], events)
        self.assertEqual((stats["checked"], stats["events"]), (2, 2))
        self.assertEqual(len(filter_attendance_events(events)), 2)

    def test_blank_and_outside_codes_never_inflate_headcount(self):
        events = pd.DataFrame([_event(1, "HS001"), _event(2, None), _event(3, "  "),
                               _event(4, float("nan")), _event(5, "NV999"), _event(6, "NV999", "OUT")])
        stats = compute_attendance_stats(["HS001", "HS002"], events)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (2, 1, 1))
        self.assertEqual(stats["events"], 6)
        self.assertEqual((stats["outside_students"], stats["outside_events"]), (1, 5))

    def test_empty_inputs(self):
        stats = compute_attendance_stats([], pd.DataFrame())
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"], stats["events"]), (0, 0, 0, 0))
        stats = compute_attendance_stats(["HS001"], None)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (1, 0, 1))

    def test_roster_counts_only_active_students_in_scope(self):
        students = [
            SimpleNamespace(student_code="HS001", class_id=1, status="Đang học"),
            SimpleNamespace(student_code="HS002", class_id=1, status="Tạm nghỉ"),
            SimpleNamespace(student_code="HS003", class_id=1, status="Đã xóa"),
            SimpleNamespace(student_code="HS004", class_id=2, status="Đang học"),
            SimpleNamespace(student_code="HS001", class_id=1, status="Đang học"),  # dòng lặp
            SimpleNamespace(student_code="HS005", class_id=2),  # không có status: coi như đang học
        ]
        self.assertEqual(active_roster_codes(students), ["HS001", "HS004", "HS005"])
        self.assertEqual(active_roster_codes(students, class_id=1), ["HS001"])
        self.assertEqual(active_roster_codes(students, class_id=2, student_code="HS004"), ["HS004"])
        self.assertEqual(active_roster_codes(students, student_code="HS002"), [])

    def test_filters_by_log_type_session_and_status(self):
        events = pd.DataFrame([_event(1, "HS001"), _event(2, "HS001", "OUT"),
                               _event(3, "HS002", session=None), _event(4, "HS003", session="Buổi chiều")])
        self.assertEqual(len(filter_attendance_events(events, log_type="IN")), 3)
        self.assertEqual(len(filter_attendance_events(events, log_type="OUT")), 1)
        self.assertEqual(len(filter_attendance_events(events, student_code="HS001")), 2)
        self.assertEqual(len(filter_attendance_events(events, session_name="Dữ liệu cũ")), 1)
        self.assertEqual(len(filter_attendance_events(events, session_name="Buổi sáng")), 2)

        summary = pd.DataFrame([
            _summary_row("HS001", "Có mặt", check_out="11:00:00"),
            _summary_row("HS002", "Vắng mặt"),
            _summary_row("HS003", "Chưa ghi nhận", check_out="11:05:00"),  # chỉ có lượt ra
            _summary_row("HS004", "Đi muộn", "Buổi chiều"),
        ])
        self.assertEqual(list(filter_attendance_summary(summary, log_type="IN")["student_code"]),
                         ["HS001", "HS002", "HS004"])
        self.assertEqual(list(filter_attendance_summary(summary, log_type="OUT")["student_code"]),
                         ["HS001", "HS003"])
        self.assertEqual(len(filter_attendance_summary(summary, statuses=["Đi muộn", "Vắng mặt"])), 2)
        self.assertEqual(len(filter_attendance_summary(summary, statuses=[])), 0)
        self.assertEqual(len(filter_attendance_summary(summary, session_name="Buổi chiều")), 1)

    def test_scope_text_names_system_wide_when_no_class_filter(self):
        self.assertEqual(describe_scope(), "toàn hệ thống (tất cả lớp) · toàn bộ thời gian")
        text_value = describe_scope("L001 · 11A8", D1, "HS001 · Học sinh A", "Điểm danh vào")
        self.assertIn("lớp L001 · 11A8", text_value)
        self.assertIn(f"ngày {D1:%d/%m/%Y}", text_value)
        self.assertIn("học sinh HS001", text_value)
        self.assertTrue(text_value.endswith("điểm danh vào"))


def _stats(attendance_date, class_id, log_type=None, student_code=None):
    """Tính như trang Lịch sử: cùng nguồn dữ liệu, cùng điều kiện lọc."""
    events = filter_attendance_events(
        get_student_attendance_dataframe(attendance_date, class_id),
        log_type=log_type, student_code=student_code)
    summary = filter_attendance_summary(
        get_student_attendance_summary_dataframe(attendance_date, class_id),
        log_type=log_type, student_code=student_code)
    roster = active_roster_codes(get_students(active_only=False), class_id, student_code)
    return compute_attendance_stats(roster, events, summary), summary


def _legacy_log(employee_code, student_code, class_id, attendance_date, log_type="IN"):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO attendance_logs (employee_code, log_time, log_type, camera_source, student_code, "
            "class_id, attendance_date, session_name, attendance_status, attendance_method, confirmed) "
            "VALUES (:e, :t, :k, 'legacy', :s, :c, :d, NULL, NULL, 'legacy', 1)"),
            {"e": employee_code, "t": f"{attendance_date.isoformat()} 06:30:00", "k": log_type,
             "s": student_code, "c": class_id, "d": attendance_date.isoformat()})


class DatabaseStatsTests(unittest.TestCase):
    """Các tình huống kiểm thử trên cơ sở dữ liệu tạm (lớp A: 3 học sinh, lớp B: 2 học sinh)."""

    @classmethod
    def setUpClass(cls):
        cls.class_a = create_class(f"Lớp thống kê A {SUFFIX}")
        cls.class_b = create_class(f"Lớp thống kê B {SUFFIX}")
        cls.a = [create_student(f"Học sinh A{i} {SUFFIX}", cls.class_a) for i in (1, 2, 3)]
        cls.b = [create_student(f"Học sinh B{i} {SUFFIX}", cls.class_b) for i in (1, 2)]
        a1, a2, a3 = cls.a

        def rec(code, class_id, day, session, status, kind="IN"):
            record_student_attendance(code, class_id, day, session, status, method="manual", attendance_type=kind)

        # D1: lớp A mới có 1 học sinh điểm danh.
        rec(a1, cls.class_a, D1, "Buổi sáng", "Có mặt")
        # D2: cả 3 học sinh lớp A đã điểm danh (1 em đi muộn).
        rec(a1, cls.class_a, D2, "Buổi sáng", "Có mặt")
        rec(a2, cls.class_a, D2, "Buổi sáng", "Đi muộn")
        rec(a3, cls.class_a, D2, "Buổi sáng", "Có mặt")
        # D3: một học sinh có nhiều bản ghi (vào, ra, buổi chiều) + bản ghi cũ trùng + hồ sơ ngoài danh sách.
        rec(a1, cls.class_a, D3, "Buổi sáng", "Có mặt")
        rec(a1, cls.class_a, D3, "Buổi sáng", "Có mặt", "OUT")
        rec(a1, cls.class_a, D3, "Buổi chiều", "Đi muộn")
        rec(a2, cls.class_a, D3, "Buổi sáng", "Vắng mặt")
        cls.legacy_code = f"NV{SUFFIX}"
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO employees (employee_code, name, department) VALUES (:c, 'Hồ sơ cũ thử', 'Cũ')"),
                {"c": cls.legacy_code})
        _legacy_log(a1, a1, cls.class_a, D3)              # bản ghi cũ trùng của a1
        _legacy_log(a1, None, cls.class_a, D3)            # bản ghi cũ thiếu student_code của a1
        _legacy_log(cls.legacy_code, None, cls.class_a, D3)  # hồ sơ không phải học sinh
        # Hôm nay: lớp B có 1 học sinh điểm danh.
        rec(cls.b[0], cls.class_b, TODAY, "Buổi sáng", "Có mặt")
        clear_attendance_cache()

    def test_case1_class_of_three_with_one_checked_in(self):
        stats, summary = _stats(D1, self.class_a)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (3, 1, 2))
        self.assertEqual(stats["events"], 1)
        self.assertEqual(len(summary), 1)  # bảng chỉ có 1 dòng nhưng sĩ số vẫn là 3

    def test_case2_class_of_three_all_checked_in(self):
        stats, _ = _stats(D2, self.class_a)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (3, 3, 0))
        self.assertEqual(stats["events"], 3)
        self.assertEqual(stats["by_status"], {"Có mặt": 2, "Đi muộn": 1, "Vắng mặt": 0})

    def test_case3_many_or_duplicate_records_count_one_student(self):
        stats, summary = _stats(D3, self.class_a)
        # a1 có 5 lượt (3 hợp lệ + 2 bản ghi cũ), a2 có 1 lượt, hồ sơ cũ ngoài danh sách có 1 lượt.
        self.assertEqual(stats["events"], 7)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (3, 2, 1))
        self.assertEqual((stats["outside_students"], stats["outside_events"]), (1, 1))
        self.assertEqual(stats["by_status"], {"Có mặt": 1, "Đi muộn": 1, "Vắng mặt": 1})
        self.assertEqual(summary["student_code"].nunique(), 3)
        self.assertGreater(len(summary), summary["student_code"].nunique())  # nhiều dòng hơn số học sinh

    def test_case4_switching_class_changes_stats(self):
        stats_a, _ = _stats(TODAY, self.class_a)
        stats_b, _ = _stats(TODAY, self.class_b)
        self.assertEqual((stats_a["roster"], stats_a["checked"], stats_a["unchecked"], stats_a["events"]), (3, 0, 3, 0))
        self.assertEqual((stats_b["roster"], stats_b["checked"], stats_b["unchecked"], stats_b["events"]), (2, 1, 1, 1))

    def test_case5_switching_date_changes_stats(self):
        by_day = {day: _stats(day, self.class_a)[0]["checked"] for day in (D1, D2, D3, TODAY)}
        self.assertEqual(by_day, {D1: 1, D2: 3, D3: 2, TODAY: 0})
        all_time, _ = _stats(None, self.class_a)
        self.assertEqual((all_time["roster"], all_time["checked"], all_time["unchecked"]), (3, 3, 0))
        self.assertEqual(all_time["events"], 1 + 3 + 7)

    def test_case6_check_in_and_check_out_modes(self):
        stats_in, summary_in = _stats(D3, self.class_a, log_type="IN")
        stats_out, summary_out = _stats(D3, self.class_a, log_type="OUT")
        self.assertEqual((stats_in["events"], stats_in["checked"], stats_in["unchecked"]), (6, 2, 1))
        self.assertEqual((stats_out["events"], stats_out["checked"], stats_out["unchecked"]), (1, 1, 2))
        self.assertEqual(len(summary_out), 1)
        self.assertEqual(summary_out.iloc[0]["student_code"], self.a[0])
        self.assertTrue((summary_in["attendance_status"] != "Chưa ghi nhận").all())

    def test_case7_no_filter_is_system_wide(self):
        stats, _ = _stats(TODAY, None)
        day = TODAY.isoformat()
        with engine.connect() as connection:
            roster = connection.execute(text("SELECT COUNT(*) FROM students WHERE status = 'Đang học'")).scalar()
            date_clause = ("(attendance_date = :d OR (attendance_date IS NULL AND substr(log_time, 1, 10) = :d)) "
                           "AND (attendance_method IN ('face', 'manual') OR log_type IN ('IN', 'OUT'))")
            events = connection.execute(
                text(f"SELECT COUNT(*) FROM attendance_logs WHERE {date_clause}"), {"d": day}).scalar()
            checked = connection.execute(text(
                "SELECT COUNT(DISTINCT s.student_code) FROM attendance_logs al "
                "JOIN students s ON s.student_code = COALESCE(al.student_code, al.employee_code) "
                f"WHERE s.status = 'Đang học' AND {date_clause}"), {"d": day}).scalar()
        self.assertEqual((stats["roster"], stats["events"], stats["checked"]), (roster, events, checked))
        self.assertEqual(stats["unchecked"], roster - checked)
        self.assertGreaterEqual(stats["roster"], 5)  # ít nhất 5 học sinh của hai lớp thử

    def test_student_filter_scopes_roster_to_one_student(self):
        stats, _ = _stats(D2, self.class_a, student_code=self.a[1])
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"], stats["events"]), (1, 1, 0, 1))
        stats, _ = _stats(D1, self.class_a, student_code=self.a[1])
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"], stats["events"]), (1, 0, 1, 0))

    def test_inactive_student_is_outside_headcount(self):
        class_c = create_class(f"Lớp thống kê C {SUFFIX}")
        c1 = create_student(f"Học sinh C1 {SUFFIX}", class_c)
        c2 = create_student(f"Học sinh C2 {SUFFIX}", class_c)
        record_student_attendance(c1, class_c, D1, "Buổi sáng", "Có mặt", method="manual", attendance_type="IN")
        record_student_attendance(c2, class_c, D1, "Buổi sáng", "Có mặt", method="manual", attendance_type="IN")
        row = next(s for s in get_students(active_only=False) if s.student_code == c2)
        update_student(row.id, row.full_name, class_c, status="Tạm nghỉ")
        stats, _ = _stats(D1, class_c)
        self.assertEqual((stats["roster"], stats["checked"], stats["unchecked"]), (1, 1, 0))
        self.assertEqual((stats["outside_students"], stats["outside_events"], stats["events"]), (1, 1, 2))


def _metrics(app):
    return {item.label: item.value for item in app.metric}


def _select(app, label, value):
    next(item for item in app.selectbox if item.label == label).select(value)


class PageWiringTests(unittest.TestCase):
    """Chạy thật hai trang: thẻ thống kê và bảng phải dùng cùng điều kiện lọc."""

    @classmethod
    def setUpClass(cls):
        cls.class_id = create_class(f"Lớp thống kê trang {SUFFIX}")
        cls.codes = [create_student(f"Học sinh T{i} {SUFFIX}", cls.class_id) for i in (1, 2, 3)]
        t1, t2, _ = cls.codes
        record_student_attendance(t1, cls.class_id, D1, "Buổi sáng", "Có mặt", method="manual", attendance_type="IN")
        for session in ("Buổi sáng", "Buổi chiều", "Buổi tối"):
            record_student_attendance(t1, cls.class_id, D2, session, "Có mặt", method="manual", attendance_type="IN")
        record_student_attendance(t1, cls.class_id, D2, "Buổi sáng", "Có mặt", method="manual", attendance_type="OUT")
        record_student_attendance(t2, cls.class_id, D2, "Buổi sáng", "Đi muộn", method="manual", attendance_type="IN")

    def _history(self, day):
        app = AppTest.from_file(str(ROOT / "pages" / "5_History.py"), default_timeout=60).run()
        _select(app, "Lớp học", self.class_id)
        app.date_input[0].set_value(day)
        return app.run()

    def test_history_headcount_is_class_size_not_row_count(self):
        app = self._history(D1)
        self.assertEqual([str(item.value) for item in app.exception], [])
        metrics = _metrics(app)
        self.assertEqual((metrics["Sĩ số"], metrics["Đã điểm danh"], metrics["Chưa điểm danh"]), ("3", "1", "2"))
        self.assertEqual(metrics["Tổng lượt ghi nhận"], "1")
        self.assertEqual(len(app.dataframe[0].value), 1)
        self.assertNotIn("Tổng học sinh có lịch sử", metrics)

    def test_history_student_with_three_sessions_counts_once(self):
        app = self._history(D2)
        metrics = _metrics(app)
        self.assertEqual(len(app.dataframe[0].value), 4)  # t1 x 3 buổi + t2 x 1 buổi
        self.assertEqual((metrics["Sĩ số"], metrics["Đã điểm danh"], metrics["Chưa điểm danh"]), ("3", "2", "1"))
        self.assertEqual(metrics["Tổng lượt ghi nhận"], "5")
        self.assertEqual((metrics["Có mặt"], metrics["Đi muộn"]), ("1", "1"))

    def test_history_check_out_mode_filters_cards_and_table_together(self):
        app = self._history(D2)
        _select(app, "Loại lượt điểm danh", "Điểm danh ra về")
        app = app.run()
        metrics = _metrics(app)
        self.assertEqual((metrics["Sĩ số"], metrics["Đã điểm danh"], metrics["Chưa điểm danh"]), ("3", "1", "2"))
        self.assertEqual(metrics["Tổng lượt ghi nhận"], "1")
        self.assertEqual(len(app.dataframe[0].value), 1)
        _select(app, "Loại lượt điểm danh", "Điểm danh vào")
        app = app.run()
        metrics = _metrics(app)
        self.assertEqual((metrics["Đã điểm danh"], metrics["Tổng lượt ghi nhận"]), ("2", "4"))
        self.assertEqual(len(app.dataframe[0].value), 4)

    def test_history_without_filters_states_system_wide_scope(self):
        app = AppTest.from_file(str(ROOT / "pages" / "5_History.py"), default_timeout=60).run()
        app.checkbox[0].uncheck()
        app = app.run()
        self.assertEqual([str(item.value) for item in app.exception], [])
        scope = next(item.value for item in app.caption if item.value.startswith("Phạm vi thống kê"))
        self.assertIn("toàn hệ thống (tất cả lớp)", scope)
        self.assertIn("toàn bộ thời gian", scope)
        metrics = _metrics(app)
        self.assertEqual(int(metrics["Sĩ số"]), len(active_roster_codes(get_students(active_only=False))))
        self.assertEqual(int(metrics["Chưa điểm danh"]), int(metrics["Sĩ số"]) - int(metrics["Đã điểm danh"]))

    def test_report_headcount_is_students_not_student_sessions(self):
        app = AppTest.from_file(str(ROOT / "pages" / "9_Attendance_Report.py"), default_timeout=60).run()
        _select(app, "Lớp học", self.class_id)
        app.date_input[0].set_value(D1)
        app = app.run()
        self.assertEqual([str(item.value) for item in app.exception], [])
        metrics = _metrics(app)
        self.assertEqual(len(app.dataframe[0].value), 9)  # 3 học sinh x 3 buổi
        self.assertEqual((metrics["Sĩ số"], metrics["Có mặt"], metrics["Chưa ghi nhận"]), ("3", "1", "2"))
        _select(app, "Buổi học", "Buổi sáng")
        app = app.run()
        metrics = _metrics(app)
        self.assertEqual(len(app.dataframe[0].value), 3)
        self.assertEqual((metrics["Sĩ số"], metrics["Có mặt"], metrics["Chưa ghi nhận"]), ("3", "1", "2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
