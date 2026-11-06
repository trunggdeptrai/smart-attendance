from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from core.dashboard_data import (
    attendance_for_date,
    attendance_trend_counts,
    class_attendance_counts,
    latest_attendance_table,
    normalize_attendance_records,
)
from db.attendance_repo import get_student_attendance_dataframe
from db.database import get_classes, get_student_dataframe
from core.timeutil import today_vn

today = today_vn()
students_df = get_student_dataframe()
classes = get_classes()
today_records, today_malformed_count, today_invalid_date_count = (
    normalize_attendance_records(get_student_attendance_dataframe(today))
)
all_records, all_malformed_count, all_invalid_date_count = (
    normalize_attendance_records(get_student_attendance_dataframe())
)
today_records = attendance_for_date(today_records, today)


def count_students(status: str) -> int:
    return len(
        {
            row["student_code"]
            for row in today_records
            if row["attendance_status"] == status
            and row["student_code"] is not None
        }
    )

st.title("Trang tổng quan")
st.caption(
    f"SMART ATTENDANCE – HỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH · "
    f"{today.strftime('%d/%m/%Y')}"
)
if today_malformed_count or all_malformed_count:
    st.warning(
        "Đã bỏ qua "
        f"{max(today_malformed_count, all_malformed_count)} "
        "bản ghi điểm danh sai cấu trúc."
    )
if today_invalid_date_count or all_invalid_date_count:
    st.warning(
        "Đã bỏ qua "
        f"{max(today_invalid_date_count, all_invalid_date_count)} "
        "bản ghi có ngày điểm danh không hợp lệ."
    )

metric_cols = st.columns(5)
metric_cols[0].metric("Tổng số học sinh", len(students_df))
metric_cols[1].metric("Số lớp", len(classes))
metric_cols[2].metric("Có mặt", count_students("Có mặt"))
metric_cols[3].metric("Đi muộn", count_students("Đi muộn"))
metric_cols[4].metric("Vắng mặt đã xác nhận", count_students("Vắng mặt"))
st.caption("Học sinh chưa được ghi nhận không được tự động tính là vắng mặt.")

left, right = st.columns([1.5, 1], gap="large")
with left:
    st.subheader("Tình hình điểm danh 7 ngày gần nhất")
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    trend_counts = attendance_trend_counts(all_records, days)
    if not any(
        count
        for counts_by_status in trend_counts.values()
        for count in counts_by_status.values()
    ):
        st.info("Chưa có dữ liệu chấm công trong 7 ngày gần nhất.")
    else:
        date_labels = [day.strftime("%d/%m") for day in days]
        chart = go.Figure(
            data=[
                go.Bar(
                    x=date_labels,
                    y=[trend_counts[day][status] for day in days],
                    name=status,
                    marker_color=color,
                )
                for status, color in (
                    ("Có mặt", "#15803D"),
                    ("Đi muộn", "#D97706"),
                    ("Vắng mặt", "#DC2626"),
                )
            ]
        )
        chart.update_layout(
            barmode="group",
            height=330,
            margin=dict(l=12, r=12, t=15, b=12),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )
        st.plotly_chart(
            chart,
            width="stretch",
            config={"displayModeBar": False},
        )

with right:
    st.subheader("Tình hình theo lớp hôm nay")
    per_class = class_attendance_counts(today_records)
    if not per_class:
        st.info("Chưa có lượt điểm danh được xác nhận hôm nay.")
    else:
        class_names = sorted({class_name for class_name, _ in per_class})
        class_chart = go.Figure(
            data=[
                go.Bar(
                    x=class_names,
                    y=[
                        per_class.get((class_name, status), 0)
                        for class_name in class_names
                    ],
                    name=status,
                    marker_color=color,
                )
                for status, color in (
                    ("Có mặt", "#2563EB"),
                    ("Đi muộn", "#D97706"),
                    ("Vắng mặt", "#DC2626"),
                )
            ]
        )
        class_chart.update_layout(
            barmode="stack",
            height=330,
            margin=dict(l=12, r=12, t=15, b=12),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )
        st.plotly_chart(
            class_chart,
            width="stretch",
            config={"displayModeBar": False},
        )

st.subheader("Lượt điểm danh mới nhất hôm nay")
if not today_records:
    st.info(
        "Chưa có dữ liệu chấm công hôm nay. "
        "Bắt đầu tại mục Điểm danh để ghi nhận học sinh."
    )
else:
    latest = latest_attendance_table(today_records)
    st.dataframe(
        latest,
        width="stretch",
        hide_index=True,
    )
