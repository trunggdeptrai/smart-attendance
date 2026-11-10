from datetime import date

import streamlit as st

from core.attendance_export import build_attendance_excel
from core.attendance_stats import (
    LOG_TYPE_OPTIONS,
    active_roster_codes,
    compute_attendance_stats,
    describe_scope,
    filter_attendance_events,
    filter_attendance_summary,
)
from db.attendance_repo import (
    get_student_attendance_dataframe,
    get_student_attendance_summary_dataframe,
)
from db.database import get_classes, get_students
from core.timeutil import today_vn

STATUS_OPTIONS = ["Có mặt", "Đi muộn", "Vắng mặt", "Chưa ghi nhận"]

st.title("Lịch sử điểm danh")
st.caption("Tra cứu lượt vào, lượt ra và tình trạng chuyên cần theo bộ lọc.")

classes = get_classes(active_only=False)
class_map = {row.id: row for row in classes}
all_students = get_students(active_only=False)
filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    use_date_filter = st.checkbox("Lọc theo ngày", value=True)
    selected_date = (
        st.date_input(
            "Ngày điểm danh",
            value=today_vn(),
            format="DD/MM/YYYY",
        )
        if use_date_filter else None
    )
with filter_col2:
    class_options = [None] + [row.id for row in classes]
    selected_class_id = st.selectbox(
        "Lớp học",
        class_options,
        format_func=lambda value: (
            "Tất cả lớp" if value is None
            else f"{class_map[value].class_code} · {class_map[value].name}"
        ),
    )
with filter_col3:
    students = all_students
    if selected_class_id is not None:
        students = [row for row in students if row.class_id == selected_class_id]
    student_options = [None] + [row.student_code for row in students]
    student_map = {row.student_code: row for row in students}
    selected_student_code = st.selectbox(
        "Học sinh",
        student_options,
        format_func=lambda value: (
            "Tất cả học sinh" if value is None
            else f"{value} · {student_map[value].full_name}"
        ),
    )
filter_col4, filter_col5 = st.columns(2)
with filter_col4:
    log_type_label = st.selectbox(
        "Loại lượt điểm danh",
        list(LOG_TYPE_OPTIONS),
        help="Chọn chỉ lượt vào hoặc chỉ lượt ra về; thẻ thống kê và bảng cùng đổi theo.",
    )
    log_type = LOG_TYPE_OPTIONS[log_type_label]
with filter_col5:
    status_filter = st.multiselect(
        "Trạng thái chuyên cần",
        STATUS_OPTIONS,
        default=STATUS_OPTIONS,
        help="Chỉ lọc các dòng của bảng bên dưới.",
    )

# Một nguồn dữ liệu và một bộ điều kiện lọc (ngày, lớp, học sinh, loại lượt)
# cho cả thẻ thống kê lẫn bảng.
events = filter_attendance_events(
    get_student_attendance_dataframe(selected_date, selected_class_id),
    log_type=log_type,
    student_code=selected_student_code,
)
scope_records = filter_attendance_summary(
    get_student_attendance_summary_dataframe(selected_date, selected_class_id),
    log_type=log_type,
    student_code=selected_student_code,
)
records = filter_attendance_summary(scope_records, statuses=status_filter)

# Sĩ số lấy từ danh sách học sinh đang học, không suy ra từ số dòng của bảng.
roster_codes = active_roster_codes(
    all_students,
    class_id=selected_class_id,
    student_code=selected_student_code,
)
stats = compute_attendance_stats(roster_codes, events, scope_records)

scope_text = describe_scope(
    class_label=(
        f"{class_map[selected_class_id].class_code} · {class_map[selected_class_id].name}"
        if selected_class_id is not None else None
    ),
    attendance_date=selected_date,
    student_label=(
        f"{selected_student_code} · {student_map[selected_student_code].full_name}"
        if selected_student_code is not None else None
    ),
    log_type_label=log_type_label,
)
st.caption(f"Phạm vi thống kê: {scope_text}.")

metric_cols = st.columns(4)
metric_cols[0].metric(
    "Sĩ số",
    stats["roster"],
    help="Số học sinh đang học trong phạm vi lọc (lớp, học sinh).",
)
metric_cols[1].metric(
    "Đã điểm danh",
    stats["checked"],
    help=(
        "Số học sinh duy nhất có ít nhất một lượt ghi nhận trong phạm vi lọc, "
        "kể cả vắng mặt đã được giáo viên xác nhận."
    ),
)
metric_cols[2].metric(
    "Chưa điểm danh",
    stats["unchecked"],
    help="Sĩ số trừ số học sinh đã điểm danh. Chưa điểm danh không đồng nghĩa với vắng mặt.",
)
metric_cols[3].metric(
    "Tổng lượt ghi nhận",
    stats["events"],
    help="Số sự kiện điểm danh (vào, ra về) trong phạm vi lọc; không phải số học sinh.",
)
status_cols = st.columns(3)
status_cols[0].metric("Có mặt", stats["by_status"]["Có mặt"])
status_cols[1].metric("Đi muộn", stats["by_status"]["Đi muộn"])
status_cols[2].metric("Vắng mặt đã xác nhận", stats["by_status"]["Vắng mặt"])
st.caption(
    "Các thẻ đếm học sinh duy nhất; học sinh có nhiều buổi trong phạm vi lọc "
    "có thể được tính ở nhiều trạng thái."
)
if stats["outside_events"]:
    st.warning(
        f"Có {stats['outside_events']} lượt ghi nhận của {stats['outside_students']} hồ sơ "
        "không thuộc danh sách học sinh đang học trong phạm vi lọc (dữ liệu cũ, học sinh "
        "đã nghỉ hoặc đã chuyển lớp). Các lượt này có trong bảng và trong tổng lượt ghi nhận "
        "nhưng không tính vào sĩ số và số đã điểm danh."
    )

table_note = (
    f"Bảng liệt kê theo học sinh – ngày – buổi: {len(records)} dòng của "
    f"{records['student_code'].nunique() if not records.empty else 0} học sinh."
)
if set(status_filter) != set(STATUS_OPTIONS):
    table_note += " Bảng đang lọc theo trạng thái; các thẻ thống kê không đổi theo bộ lọc này."
st.caption(table_note)

display = records[
    [
        "student_code",
        "student_name",
        "class_name",
        "attendance_date",
        "session_name",
        "check_in_time",
        "check_out_time",
        "attendance_status",
        "attendance_state",
    ]
].rename(
    columns={
        "student_code": "Mã học sinh",
        "student_name": "Họ và tên",
        "class_name": "Lớp",
        "attendance_date": "Ngày",
        "session_name": "Buổi học",
        "check_in_time": "Giờ vào",
        "check_out_time": "Giờ ra",
        "attendance_status": "Trạng thái",
        "attendance_state": "Tình trạng lượt",
    }
)
for time_column in ("Giờ vào", "Giờ ra"):
    display[time_column] = display[time_column].fillna("Chưa ghi nhận")
st.dataframe(display, width="stretch", hide_index=True)

if display.empty:
    st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại; chưa thể xuất Excel.")
else:
    export_records = display.rename(
        columns={
            "Mã học sinh": "Mã học sinh",
            "Họ và tên": "Họ và tên",
            "Lớp": "Lớp",
            "Ngày": "Ngày",
            "Giờ vào": "Giờ vào",
            "Giờ ra": "Giờ ra",
            "Trạng thái": "Trạng thái",
        }
    )[
        [
            "Mã học sinh",
            "Họ và tên",
            "Lớp",
            "Ngày",
            "Giờ vào",
            "Giờ ra",
            "Trạng thái",
        ]
    ]
    if selected_date is not None:
        filename_period = selected_date.isoformat()
        title_period = selected_date.strftime("%d/%m/%Y")
    elif records["attendance_date"].notna().any():
        dates = []
        for value in records["attendance_date"].dropna():
            try:
                dates.append(date.fromisoformat(str(value)[:10]))
            except ValueError:
                continue
        filename_period = (
            f"{min(dates):%Y%m%d}-{max(dates):%Y%m%d}"
            if dates else "tat-ca-thoi-gian"
        )
        title_period = (
            f"{min(dates):%d/%m/%Y} – {max(dates):%d/%m/%Y}"
            if dates else "Tất cả thời gian"
        )
    else:
        filename_period = "tat-ca-thoi-gian"
        title_period = "Tất cả thời gian"
    excel_data = build_attendance_excel(
        export_records,
        f"BÁO CÁO LỊCH SỬ ĐIỂM DANH · {title_period}",
    )
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Xuất Excel",
            data=excel_data,
            file_name=f"lich_su_diem_danh_{filename_period}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with export_col2:
        st.download_button(
            "Xuất CSV",
            data=export_records.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"lich_su_diem_danh_{filename_period}.csv",
            mime="text/csv",
        )
