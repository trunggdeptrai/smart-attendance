"""Thống kê sĩ số và lượt điểm danh dùng chung cho trang Lịch sử và Báo cáo chuyên cần.

Nguyên tắc:
- Thẻ thống kê đếm HỌC SINH DUY NHẤT, không đếm số dòng của bảng (bảng liệt kê theo
  học sinh – ngày – buổi nên một học sinh có thể chiếm nhiều dòng).
- Sĩ số lấy từ danh sách học sinh đang học trong phạm vi lọc (lớp, học sinh), không suy ra
  từ số bản ghi điểm danh.
- Thẻ thống kê và bảng dùng cùng một nguồn dữ liệu và cùng điều kiện lọc ngày, lớp,
  học sinh, buổi, loại lượt (vào/ra về).

Các hàm ở đây là hàm thuần (không truy vấn cơ sở dữ liệu, không gọi Streamlit) để kiểm thử được.
"""

import pandas as pd

ACTIVE_STUDENT_STATUS = "Đang học"
PRESENCE_STATUSES = ("Có mặt", "Đi muộn", "Vắng mặt")
NOT_RECORDED_STATUS = "Chưa ghi nhận"
LEGACY_SESSION_NAME = "Dữ liệu cũ"

# Nhãn hiển thị -> loại lượt trong cột attendance_type (None = cả hai loại)
LOG_TYPE_OPTIONS = {
    "Tất cả lượt": None,
    "Điểm danh vào": "IN",
    "Điểm danh ra về": "OUT",
}


def _clean_code(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _clean_codes(values):
    return {code for code in (_clean_code(value) for value in values) if code}


def active_roster_codes(students, class_id=None, student_code=None):
    """Mã các học sinh ĐANG HỌC trong phạm vi lọc – đây là sĩ số.

    ``students``: các dòng có thuộc tính student_code, class_id, status
    (kết quả ``db.database.get_students``).
    """
    wanted = _clean_code(student_code)
    codes = []
    seen = set()
    for row in students:
        code = _clean_code(getattr(row, "student_code", None))
        if not code or code in seen:
            continue
        if getattr(row, "status", ACTIVE_STUDENT_STATUS) != ACTIVE_STUDENT_STATUS:
            continue
        if class_id is not None and getattr(row, "class_id", None) != class_id:
            continue
        if wanted is not None and code != wanted:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def filter_attendance_events(events, *, log_type=None, student_code=None, session_name=None):
    """Lọc các lượt điểm danh thô (mỗi dòng một sự kiện) theo loại lượt, học sinh, buổi.

    ``events``: kết quả ``get_student_attendance_dataframe`` (đã lọc ngày, lớp ở truy vấn).
    Bản ghi trùng mã ``id`` (nếu có) chỉ được giữ một lần.
    """
    if events is None or events.empty:
        return events if events is not None else pd.DataFrame()
    result = events
    if "id" in result.columns:
        result = result.drop_duplicates(subset="id")
    if log_type is not None:
        result = result[result["attendance_type"] == log_type]
    if student_code is not None:
        result = result[result["student_code"] == student_code]
    if session_name is not None:
        sessions = result["session_name"].fillna(LEGACY_SESSION_NAME)
        result = result[sessions == session_name]
    return result


def filter_attendance_summary(
        summary,
        *,
        log_type=None,
        student_code=None,
        session_name=None,
        statuses=None,
):
    """Lọc bảng tổng hợp (mỗi dòng: học sinh – ngày – buổi) theo cùng điều kiện với các lượt thô.

    - ``log_type="IN"``: chỉ giữ dòng có lượt vào (trạng thái khác "Chưa ghi nhận").
    - ``log_type="OUT"``: chỉ giữ dòng có lượt ra về (có giờ ra).
    - ``statuses``: danh sách trạng thái được hiển thị; danh sách rỗng trả về bảng rỗng.
    """
    if summary is None or summary.empty:
        return summary if summary is not None else pd.DataFrame()
    result = summary
    if student_code is not None:
        result = result[result["student_code"] == student_code]
    if session_name is not None:
        result = result[result["session_name"] == session_name]
    if log_type == "IN":
        result = result[result["attendance_status"] != NOT_RECORDED_STATUS]
    elif log_type == "OUT":
        result = result[result["check_out_time"].notna()]
    if statuses is not None:
        result = result[result["attendance_status"].isin(list(statuses))]
    return result


def compute_attendance_stats(roster_codes, events, summary=None):
    """Tính các chỉ số thống kê từ sĩ số và các lượt điểm danh ĐÃ LỌC theo cùng phạm vi.

    Trả về dict:
    - ``roster``: sĩ số – số học sinh đang học trong phạm vi lọc.
    - ``checked``: số học sinh duy nhất thuộc sĩ số có ít nhất một lượt ghi nhận.
    - ``unchecked``: sĩ số trừ số đã điểm danh (không âm).
    - ``events``: tổng lượt ghi nhận trong phạm vi (số sự kiện, không phải số học sinh).
    - ``outside_students`` / ``outside_events``: hồ sơ và lượt ghi nhận không thuộc sĩ số
      (dữ liệu cũ, học sinh đã nghỉ hoặc đã chuyển lớp) – có trong lịch sử nhưng không tính
      vào sĩ số và số đã điểm danh.
    - ``by_status``: số học sinh duy nhất thuộc sĩ số theo từng trạng thái (cần ``summary``).
    """
    roster = _clean_codes(roster_codes)
    if events is None or events.empty:
        event_codes = []
    else:
        frame = events.drop_duplicates(subset="id") if "id" in events.columns else events
        event_codes = [_clean_code(value) for value in frame["student_code"]]

    recorded = {code for code in event_codes if code}
    checked = recorded & roster
    outside_events = sum(1 for code in event_codes if code not in roster)

    by_status = {status: 0 for status in PRESENCE_STATUSES}
    if summary is not None and not summary.empty:
        codes = summary["student_code"].map(_clean_code)
        in_roster = summary[codes.isin(roster)]
        for status in PRESENCE_STATUSES:
            matched = in_roster.loc[in_roster["attendance_status"] == status, "student_code"]
            by_status[status] = len(_clean_codes(matched))

    return {
        "roster": len(roster),
        "checked": len(checked),
        "unchecked": max(0, len(roster) - len(checked)),
        "events": len(event_codes),
        "outside_students": len(recorded - roster),
        "outside_events": outside_events,
        "by_status": by_status,
    }


def describe_scope(class_label=None, attendance_date=None, student_label=None, log_type_label=None,
                   session_label=None):
    """Câu mô tả phạm vi thống kê để hiển thị cạnh các thẻ (không lọc lớp = toàn hệ thống)."""
    parts = [f"lớp {class_label}" if class_label else "toàn hệ thống (tất cả lớp)"]
    if student_label:
        parts.append(f"học sinh {student_label}")
    if attendance_date is not None:
        formatted = (
            attendance_date.strftime("%d/%m/%Y")
            if hasattr(attendance_date, "strftime") else str(attendance_date)
        )
        parts.append(f"ngày {formatted}")
    else:
        parts.append("toàn bộ thời gian")
    if session_label:
        parts.append(session_label.lower())
    if log_type_label:
        parts.append(log_type_label.lower())
    return " · ".join(parts)
