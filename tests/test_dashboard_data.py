from datetime import date, timedelta

import pandas as pd

from core.dashboard_data import (
    ATTENDANCE_COLUMNS,
    LATEST_TABLE_COLUMNS,
    attendance_for_date,
    attendance_trend_counts,
    class_attendance_counts,
    latest_attendance_table,
    normalize_attendance_records,
)


def _record(**overrides):
    row = {
        "id": 1,
        "student_code": "HS001",
        "student_name": "Nguyen An",
        "class_name": "10A1",
        "attendance_date": "2026-11-03",
        "session_name": "Sáng",
        "attendance_status": "Có mặt",
        "attendance_type": "IN",
        "attendance_method": "Giáo viên xác nhận",
        "log_time": "2026-11-03 08:00:00",
    }
    row.update(overrides)
    return row


def test_empty_attendance_has_fixed_table_schema():
    rows, malformed, invalid_dates = normalize_attendance_records([])

    assert rows == []
    assert malformed == 0
    assert invalid_dates == 0
    table = latest_attendance_table(rows)
    assert table.empty
    assert table.columns.tolist() == LATEST_TABLE_COLUMNS


def test_records_are_normalized_and_aggregated_across_days():
    source_rows = [
        _record(id=3, student_code="HS001", attendance_status="Đi muộn"),
        _record(
            id=2,
            student_code="HS001",
            attendance_status="Có mặt",
            attendance_type="OUT",
            log_time="2026-11-03 07:55:00",
        ),
        _record(
            id=4,
            student_code="HS002",
            session_name="Chiều",
            attendance_status="Đi muộn",
        ),
        _record(
            id=5,
            student_code="HS001",
            attendance_date="2026-11-02",
            log_time="2026-11-02 08:00:00",
        ),
    ]
    rows, malformed, invalid_dates = normalize_attendance_records(
        pd.DataFrame.from_records(source_rows, columns=ATTENDANCE_COLUMNS)
    )
    today = date(2026, 11, 3)
    today_rows = attendance_for_date(rows, today)
    counts = attendance_trend_counts(
        rows,
        [date(2026, 11, 2), today],
    )

    assert malformed == 0
    assert invalid_dates == 0
    assert len(today_rows) == 2
    assert counts[today] == {"Có mặt": 0, "Đi muộn": 2, "Vắng mặt": 0}
    assert counts[date(2026, 11, 2)] == {
        "Có mặt": 1,
        "Đi muộn": 0,
        "Vắng mặt": 0,
    }
    assert class_attendance_counts(today_rows) == {
        ("10A1", "Đi muộn"): 2,
    }
    assert latest_attendance_table(today_rows).shape == (2, len(LATEST_TABLE_COLUMNS))


def test_trend_counts_many_records_and_keeps_each_day_separate():
    days = [date(2026, 10, 28) + timedelta(days=offset) for offset in range(7)]
    source_rows = []
    for day_index, attendance_day in enumerate(days):
        for status_index, status in enumerate(("Có mặt", "Đi muộn", "Vắng mặt")):
            for student_index in range(2):
                source_rows.append(
                    _record(
                        id=len(source_rows) + 1,
                        student_code=f"HS{status_index * 2 + student_index:03d}",
                        attendance_date=attendance_day.isoformat(),
                        attendance_status=status,
                        session_name=f"Buổi {day_index}",
                        log_time=f"{attendance_day.isoformat()} 08:00:00",
                    )
                )
    rows, malformed, invalid_dates = normalize_attendance_records(source_rows)
    counts = attendance_trend_counts(rows, days)

    assert malformed == 0
    assert invalid_dates == 0
    assert len(rows) == 42
    assert all(
        day_counts == {"Có mặt": 2, "Đi muộn": 2, "Vắng mặt": 2}
        for day_counts in counts.values()
    )


def test_invalid_dates_and_missing_values_are_safe():
    rows, malformed, invalid_dates = normalize_attendance_records(
        [
            _record(attendance_date="not-a-date"),
            _record(
                id=2,
                attendance_date="not-a-date",
                log_time="also-not-a-date",
            ),
            _record(
                id=3,
                attendance_date=float("nan"),
                log_time=pd.NaT,
            ),
        ]
    )

    assert malformed == 0
    assert invalid_dates == 2
    assert rows[0]["attendance_date"] == "2026-11-03"
    assert rows[1]["attendance_date"] is None
    assert rows[2]["attendance_date"] is None
    assert attendance_for_date(rows, date(2026, 11, 3)) == [rows[0]]


def test_inconsistent_rows_are_skipped_without_creating_unequal_columns():
    rows, malformed, invalid_dates = normalize_attendance_records(
        [
            _record(),
            (2, "HS002"),
            _record(student_code=["nested", "value"]),
            "not a record",
        ]
    )

    assert len(rows) == 2
    assert malformed == 2
    assert invalid_dates == 1
    assert list(rows[1]) == ATTENDANCE_COLUMNS
    assert rows[1]["student_code"] == "HS002"
    assert all(len(row) == len(ATTENDANCE_COLUMNS) for row in rows)


def test_unsupported_top_level_data_is_reported_as_malformed():
    rows, malformed, invalid_dates = normalize_attendance_records(object())

    assert rows == []
    assert malformed == 1
    assert invalid_dates == 0


if __name__ == "__main__":
    test_empty_attendance_has_fixed_table_schema()
    test_records_are_normalized_and_aggregated_across_days()
    test_trend_counts_many_records_and_keeps_each_day_separate()
    test_invalid_dates_and_missing_values_are_safe()
    test_inconsistent_rows_are_skipped_without_creating_unequal_columns()
    test_unsupported_top_level_data_is_reported_as_malformed()
    print("Dashboard data checks passed.")
