from datetime import date

import streamlit as st

from core.attendance_export import build_attendance_excel
from db.attendance_repo import get_student_attendance_summary_dataframe
from db.database import get_classes, get_students

st.title("Lịch sử điểm danh")
st.caption("Tra cứu lượt vào, lượt ra và tình trạng chuyên cần theo bộ lọc.")

classes = get_classes(active_only=False)
class_map = {row.id: row for row in classes}
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    use_date_filter = st.checkbox("Lọc theo ngày", value=True)
    selected_date = (
        st.date_input(
            "Ngày điểm danh",
            value=date.today(),
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
    students = get_students(active_only=False)
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
with filter_col4:
    status_filter = st.multiselect(
        "Trạng thái chuyên cần",
        ["Có mặt", "Đi muộn", "Vắng mặt", "Chưa ghi nhận"],
        default=["Có mặt", "Đi muộn", "Vắng mặt", "Chưa ghi nhận"],
    )

records = get_student_attendance_summary_dataframe(
    selected_date,
    selected_class_id,
)
if selected_student_code is not None:
    records = records[records["student_code"] == selected_student_code]
if status_filter:
    records = records[records["attendance_status"].isin(status_filter)]
else:
    records = records.iloc[0:0]

metric_cols = st.columns(4)
metric_cols[0].metric("Tổng học sinh có lịch sử", len(records))
metric_cols[1].metric(
    "Có mặt",
    int((records["attendance_status"] == "Có mặt").sum()),
)
metric_cols[2].metric(
    "Đi muộn",
    int((records["attendance_status"] == "Đi muộn").sum()),
)
metric_cols[3].metric(
    "Vắng mặt đã xác nhận",
    int((records["attendance_status"] == "Vắng mặt").sum()),
)

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
