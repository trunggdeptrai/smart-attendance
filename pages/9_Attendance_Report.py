from datetime import date

import pandas as pd
import streamlit as st

from core.attendance_export import build_attendance_excel
from db.attendance_repo import get_student_attendance_summary_dataframe
from db.database import get_classes, get_students

st.title("Báo cáo chuyên cần")
st.caption("Theo dõi giờ vào, giờ ra và trạng thái chuyên cần theo lớp.")

classes = get_classes(active_only=False)
class_map = {row.id: row for row in classes}
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    class_options = [None] + [row.id for row in classes]
    selected_class_id = st.selectbox(
        "Lớp học",
        class_options,
        format_func=lambda value: (
            "Tất cả lớp" if value is None
            else f"{class_map[value].class_code} · {class_map[value].name}"
        ),
    )
with filter_col2:
    selected_date = st.date_input(
        "Ngày báo cáo",
        value=date.today(),
        format="DD/MM/YYYY",
    )
with filter_col3:
    selected_session = st.selectbox(
        "Buổi học",
        ["Tất cả buổi", "Buổi sáng", "Buổi chiều", "Buổi tối", "Dữ liệu cũ"],
    )
with filter_col4:
    roster = get_students(active_only=False)
    if selected_class_id is not None:
        roster = [row for row in roster if row.class_id == selected_class_id]
    roster_map = {row.student_code: row for row in roster}
    student_options = [None] + list(roster_map)
    selected_student_code = st.selectbox(
        "Học sinh",
        student_options,
        format_func=lambda value: (
            "Tất cả học sinh" if value is None
            else f"{value} · {roster_map[value].full_name}"
        ),
    )

if selected_student_code is not None:
    roster = [
        row for row in roster
        if row.student_code == selected_student_code
    ]

records = get_student_attendance_summary_dataframe(selected_date, selected_class_id)
if selected_session != "Tất cả buổi":
    records = records[records["session_name"] == selected_session]
if selected_student_code is not None:
    records = records[records["student_code"] == selected_student_code]
record_by_key = {
    (row.student_code, row.session_name): row
    for row in records.itertuples(index=False)
}

report_rows = []
sessions = (
    ["Buổi sáng", "Buổi chiều", "Buổi tối"]
    if selected_session == "Tất cả buổi"
    else [selected_session]
)
if (
    selected_session == "Tất cả buổi"
    and records["session_name"].eq("Dữ liệu cũ").any()
):
    sessions.append("Dữ liệu cũ")
for student in roster:
    for session in sessions:
        record = record_by_key.get((student.student_code, session))
        report_rows.append(
            {
                "Mã học sinh": student.student_code,
                "Họ và tên": student.full_name,
                "Lớp": student.class_name,
                "Ngày": selected_date,
                "Buổi học": session,
                "Giờ vào": (
                    record.check_in_time if record and record.check_in_time
                    else "Chưa ghi nhận"
                ),
                "Giờ ra": (
                    record.check_out_time if record and record.check_out_time
                    else "Chưa ghi nhận"
                ),
                "Trạng thái": (
                    record.attendance_status if record
                    else "Chưa ghi nhận"
                ),
                "Tình trạng lượt": (
                    record.attendance_state if record
                    else "Chưa ghi nhận"
                ),
            }
        )
report = pd.DataFrame(
    report_rows,
    columns=[
        "Mã học sinh",
        "Họ và tên",
        "Lớp",
        "Ngày",
        "Buổi học",
        "Giờ vào",
        "Giờ ra",
        "Trạng thái",
        "Tình trạng lượt",
    ],
)

explicit_absent = int((report["Trạng thái"] == "Vắng mặt").sum())
not_recorded = int((report["Trạng thái"] == "Chưa ghi nhận").sum())
present = int((report["Trạng thái"] == "Có mặt").sum())
late = int((report["Trạng thái"] == "Đi muộn").sum())

metrics = st.columns(5)
metrics[0].metric("Sĩ số", len(report))
metrics[1].metric("Có mặt", present)
metrics[2].metric("Đi muộn", late)
metrics[3].metric("Vắng mặt đã xác nhận", explicit_absent)
metrics[4].metric("Chưa ghi nhận", not_recorded)
st.caption(
    "Học sinh thiếu lượt vào hoặc ra được hiển thị riêng; "
    "chưa ghi nhận không đồng nghĩa với vắng."
)
st.dataframe(report, width="stretch", hide_index=True)

if report.empty:
    st.info("Không có dữ liệu học sinh phù hợp để xuất Excel.")
else:
    class_label = (
        class_map[selected_class_id].class_code
        if selected_class_id is not None else "tat-ca-lop"
    )
    excel_data = build_attendance_excel(
        report[
            [
                "Mã học sinh",
                "Họ và tên",
                "Lớp",
                "Ngày",
                "Giờ vào",
                "Giờ ra",
                "Trạng thái",
            ]
        ],
        (
            f"BÁO CÁO CHUYÊN CẦN · {class_label} · "
            f"{selected_date:%d/%m/%Y}"
        ),
    )
    export_records = report[
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
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Xuất Excel",
            data=excel_data,
            file_name=(
                f"chuyen_can_{class_label}_{selected_date:%Y%m%d}.xlsx"
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with export_col2:
        st.download_button(
            "Xuất CSV",
            data=export_records.to_csv(index=False).encode("utf-8-sig"),
            file_name=(
                f"chuyen_can_{class_label}_{selected_date:%Y%m%d}.csv"
            ),
            mime="text/csv",
        )
