"""Ngày sinh học sinh: ghép, kiểm tra hợp lệ và bộ chọn 3 ô (ngày / tháng / năm).

Thay cho st.date_input: lịch bật lên của Streamlit giới hạn ±10 năm quanh hôm nay
khi không đặt min_value và khó chọn năm trên iPhone.
"""
from __future__ import annotations

import calendar
from datetime import date

from core.timeutil import today_vn

MIN_BIRTH_DATE = date(1990, 1, 1)
DEFAULT_BIRTH_DATE = date(2010, 1, 1)
EMPTY = "—"


def validate_birth_date(value: date | None, today: date | None = None) -> date | None:
    """Trả lại ngày nếu hợp lệ; None nghĩa là không nhập. Sai thì ValueError."""
    if value is None:
        return None
    today = today or today_vn()
    if value > today:
        raise ValueError("Ngày sinh không được ở tương lai.")
    if value < MIN_BIRTH_DATE:
        raise ValueError(f"Ngày sinh phải từ {MIN_BIRTH_DATE:%d/%m/%Y} trở về sau.")
    return value


def compose_birth_date(day, month, year, today: date | None = None) -> date | None:
    """Ghép 3 giá trị đã chọn thành datetime.date (không dùng giờ, không lệch múi giờ)."""
    parts = [day, month, year]
    if all(p in (None, "", EMPTY) for p in parts):
        return None
    if any(p in (None, "", EMPTY) for p in parts):
        raise ValueError("Hãy chọn đủ ngày, tháng và năm sinh (hoặc để trống cả ba).")
    day, month, year = int(day), int(month), int(year)
    if not 1 <= month <= 12:
        raise ValueError("Tháng sinh không hợp lệ.")
    last_day = calendar.monthrange(year, month)[1]
    if not 1 <= day <= last_day:
        raise ValueError(
            f"Ngày {day:02d}/{month:02d}/{year} không tồn tại "
            f"(tháng {month}/{year} chỉ có {last_day} ngày)."
        )
    return validate_birth_date(date(year, month, day), today)


def year_options(today: date | None = None) -> list[int]:
    """Năm hiện tại → 1990 (giảm dần)."""
    today = today or today_vn()
    return list(range(today.year, MIN_BIRTH_DATE.year - 1, -1))


def birth_date_input(label: str, value: date | None, key: str):
    """Ba ô chọn Ngày / Tháng / Năm. Trả về (ngày, tháng, năm) thô để ghép khi bấm lưu.

    Dùng trong st.form: kiểm tra hợp lệ bằng compose_birth_date khi người dùng gửi form.
    """
    import streamlit as st

    years = year_options()
    days = [EMPTY] + list(range(1, 32))
    months = [EMPTY] + list(range(1, 13))
    year_list = [EMPTY] + years
    if value is not None and value.year not in years:
        year_list.append(value.year)  # giữ hiển thị đúng dữ liệu cũ ngoài khoảng

    wrap = f"{key}_wrap"
    # Giữ 3 ô trên cùng một hàng cả trên điện thoại (Streamlit mặc định xếp dọc khi màn hẹp).
    st.html(
        f"<style>.st-key-{wrap} [data-testid='stHorizontalBlock']{{flex-wrap:nowrap;gap:0.5rem}}"
        f".st-key-{wrap} [data-testid='stColumn']{{min-width:0 !important;flex:1 1 0 !important;width:auto !important}}</style>"
    )
    container = st.container(key=wrap)
    container.markdown(f"**{label}**")
    col_d, col_m, col_y = container.columns([1, 1, 1.3])
    day = col_d.selectbox(
        "Ngày",
        days,
        index=days.index(value.day) if value else 0,
        key=f"{key}_day",
    )
    month = col_m.selectbox(
        "Tháng",
        months,
        index=months.index(value.month) if value else 0,
        key=f"{key}_month",
    )
    year = col_y.selectbox(
        "Năm",
        year_list,
        index=year_list.index(value.year) if value else 0,
        key=f"{key}_year",
    )
    return day, month, year
