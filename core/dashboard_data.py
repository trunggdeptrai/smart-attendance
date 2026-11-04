from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import pandas as pd

from core.dataframes import records_to_dataframe

ATTENDANCE_COLUMNS = [
    "id",
    "student_code",
    "student_name",
    "class_name",
    "attendance_date",
    "session_name",
    "attendance_status",
    "attendance_type",
    "attendance_method",
    "log_time",
]
ATTENDANCE_STATUSES = ("Có mặt", "Đi muộn", "Vắng mặt")
LATEST_TABLE_COLUMNS = [
    "Mã học sinh",
    "Họ và tên",
    "Lớp",
    "Buổi học",
    "Trạng thái",
    "Phương thức",
    "Thời gian",
]


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if text.casefold() in {"", "nan", "nat", "none", "<na>"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def normalize_attendance_records(
    records: Any,
) -> tuple[list[dict[str, Any]], int, int]:
    if isinstance(records, pd.DataFrame):
        source_rows = records.to_dict(orient="records")
    elif isinstance(records, Mapping):
        source_rows = [records]
    elif isinstance(records, (list, tuple)):
        source_rows = list(records)
    elif records is None:
        source_rows = []
    else:
        return [], 1, 0

    normalized_rows = []
    malformed_count = 0
    invalid_date_count = 0
    for source_row in source_rows:
        if isinstance(source_row, Mapping):
            values = source_row
        elif isinstance(source_row, (list, tuple)):
            values = dict(zip(ATTENDANCE_COLUMNS, source_row))
        else:
            malformed_count += 1
            continue

        row = {column: values.get(column) for column in ATTENDANCE_COLUMNS}
        if any(not pd.api.types.is_scalar(value) for value in row.values()):
            malformed_count += 1
            continue
        row = {
            column: None if pd.isna(value) else value
            for column, value in row.items()
        }

        parsed_date = _parse_date(row["attendance_date"])
        if parsed_date is None:
            parsed_date = _parse_date(row["log_time"])
            if parsed_date is None:
                invalid_date_count += 1
        row["attendance_date"] = (
            parsed_date.isoformat() if parsed_date is not None else None
        )
        normalized_rows.append(row)

    return normalized_rows, malformed_count, invalid_date_count


def attendance_for_date(
    records: list[dict[str, Any]],
    attendance_date: date,
) -> list[dict[str, Any]]:
    attendance_date_text = attendance_date.isoformat()
    seen = set()
    matching_rows = []
    for row in records:
        if row["attendance_date"] != attendance_date_text:
            continue
        key = (row["student_code"], row["session_name"])
        if key in seen:
            continue
        seen.add(key)
        matching_rows.append(row)
    return matching_rows


def attendance_trend_counts(
    records: list[dict[str, Any]],
    days: list[date],
) -> dict[date, dict[str, int]]:
    counts = {
        day: {status: 0 for status in ATTENDANCE_STATUSES}
        for day in days
    }
    valid_days = set(counts)
    seen = set()
    for row in records:
        attendance_date = _parse_date(row["attendance_date"])
        status = row["attendance_status"]
        student_code = row["student_code"]
        if (
            attendance_date is None
            or attendance_date not in valid_days
            or status not in ATTENDANCE_STATUSES
            or student_code is None
        ):
            continue
        key = (attendance_date, student_code, row["session_name"])
        if key in seen:
            continue
        seen.add(key)
        counts[attendance_date][status] += 1
    return counts


def class_attendance_counts(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str], int]:
    students_by_class_and_status: dict[tuple[str, str], set[str]] = {}
    for row in records:
        student_code = row["student_code"]
        status = row["attendance_status"]
        if student_code is None or status not in ATTENDANCE_STATUSES:
            continue
        class_name = row["class_name"] or "Chưa phân lớp"
        key = (class_name, status)
        students_by_class_and_status.setdefault(key, set()).add(str(student_code))
    return {
        key: len(student_codes)
        for key, student_codes in students_by_class_and_status.items()
    }


def latest_attendance_table(records: list[dict[str, Any]]) -> pd.DataFrame:
    sorted_rows = sorted(
        records,
        key=lambda row: str(row["log_time"] or ""),
        reverse=True,
    )[:10]
    display_rows = [
        {
            "Mã học sinh": row["student_code"],
            "Họ và tên": row["student_name"],
            "Lớp": row["class_name"],
            "Buổi học": row["session_name"],
            "Trạng thái": row["attendance_status"],
            "Phương thức": row["attendance_method"],
            "Thời gian": row["log_time"],
        }
        for row in sorted_rows
    ]
    return records_to_dataframe(
        display_rows,
        columns=LATEST_TABLE_COLUMNS,
    )
