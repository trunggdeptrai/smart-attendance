from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db.attendance_repo import get_student_attendance_dataframe
from db.database import get_classes, get_student_dataframe

today = date.today()
students_df = get_student_dataframe()
classes = get_classes()
today_df = get_student_attendance_dataframe(today)
all_logs = get_student_attendance_dataframe()

if not today_df.empty:
    today_df = today_df.drop_duplicates(
        subset=["student_code", "session_name"],
        keep="first",
    )

present_count = (
    today_df.loc[today_df["attendance_status"] == "Có mặt", "student_code"].nunique()
    if not today_df.empty else 0
)
late_count = (
    today_df.loc[today_df["attendance_status"] == "Đi muộn", "student_code"].nunique()
    if not today_df.empty else 0
)
absent_count = (
    today_df.loc[today_df["attendance_status"] == "Vắng mặt", "student_code"].nunique()
    if not today_df.empty else 0
)

st.title("Trang tổng quan")
st.caption(
    f"SMART ATTENDANCE – HỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH · "
    f"{today.strftime('%d/%m/%Y')}"
)

metric_cols = st.columns(5)
metric_cols[0].metric("Tổng số học sinh", len(students_df))
metric_cols[1].metric("Số lớp", len(classes))
metric_cols[2].metric("Có mặt", present_count)
metric_cols[3].metric("Đi muộn", late_count)
metric_cols[4].metric("Vắng mặt đã xác nhận", absent_count)
st.caption("Học sinh chưa được ghi nhận không được tự động tính là vắng mặt.")

left, right = st.columns([1.5, 1], gap="large")
with left:
    st.subheader("Tình hình điểm danh 7 ngày gần nhất")
    days = [
        (today - timedelta(days=offset)).isoformat()
        for offset in range(6, -1, -1)
    ]
    trend_rows = []
    if not all_logs.empty:
        recent_logs = all_logs[
            all_logs["attendance_date"].astype(str).isin(days)
        ].drop_duplicates(subset=["attendance_date", "student_code", "session_name"])
        for day in days:
            day_rows = recent_logs[recent_logs["attendance_date"] == day]
            for status in ("Có mặt", "Đi muộn", "Vắng mặt"):
                trend_rows.append(
                    {
                        "Ngày": day,
                        "Trạng thái": status,
                        "Số học sinh": int(
                            day_rows.loc[
                                day_rows["attendance_status"] == status,
                                "student_code",
                            ].nunique()
                        ),
                    }
                )
    else:
        trend_rows = [
            {"Ngày": day, "Trạng thái": status, "Số học sinh": 0}
            for day in days
            for status in ("Có mặt", "Đi muộn", "Vắng mặt")
        ]
    trend = pd.DataFrame(trend_rows)
    trend["Ngày"] = [
        date.fromisoformat(day).strftime("%d/%m")
        for day in trend["Ngày"]
    ]
    chart = px.bar(
        trend,
        x="Ngày",
        y="Số học sinh",
        color="Trạng thái",
        barmode="group",
        color_discrete_map={
            "Có mặt": "#15803D",
            "Đi muộn": "#D97706",
            "Vắng mặt": "#DC2626",
        },
    )
    chart.update_layout(
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
    if not today_df.empty:
        per_class = (
            today_df.groupby(["class_name", "attendance_status"])["student_code"]
            .nunique()
            .reset_index(name="Số học sinh")
        )
    else:
        per_class = pd.DataFrame(
            columns=["class_name", "attendance_status", "Số học sinh"]
        )
    if per_class.empty:
        st.info("Chưa có lượt điểm danh được xác nhận hôm nay.")
    else:
        class_chart = px.bar(
            per_class,
            x="class_name",
            y="Số học sinh",
            color="attendance_status",
            barmode="stack",
            labels={
                "class_name": "Lớp",
                "attendance_status": "Trạng thái",
            },
            color_discrete_map={
                "Có mặt": "#2563EB",
                "Đi muộn": "#D97706",
                "Vắng mặt": "#DC2626",
            },
        )
        class_chart.update_layout(
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
if today_df.empty:
    st.info("Chưa có dữ liệu. Bắt đầu tại mục Điểm danh để ghi nhận học sinh.")
else:
    latest = today_df.sort_values("log_time", ascending=False).head(10)
    st.dataframe(
        latest[
            [
                "student_code",
                "student_name",
                "class_name",
                "session_name",
                "attendance_status",
                "attendance_method",
                "log_time",
            ]
        ].rename(
            columns={
                "student_code": "Mã học sinh",
                "student_name": "Họ và tên",
                "class_name": "Lớp",
                "session_name": "Buổi học",
                "attendance_status": "Trạng thái",
                "attendance_method": "Phương thức",
                "log_time": "Thời gian",
            }
        ),
        width="stretch",
        hide_index=True,
    )
