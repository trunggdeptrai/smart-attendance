"""Thời gian theo múi giờ Việt Nam (Asia/Ho_Chi_Minh, UTC+7, không đổi giờ mùa hè).

Máy chủ đám mây (Streamlit Cloud) chạy theo UTC: dùng ``datetime.now()`` sẽ ghi
sai ngày điểm danh trước 7 giờ sáng. Mọi thời điểm điểm danh dùng các hàm dưới.
Giá trị lưu trong cơ sở dữ liệu là giờ Việt Nam dạng ``YYYY-MM-DD HH:MM:SS``.
"""

from datetime import date, datetime, timedelta, timezone

try:  # tzdata đi kèm pandas; nếu thiếu vẫn dùng được độ lệch cố định +7
    from zoneinfo import ZoneInfo

    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover
    VN_TZ = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")


def now_vn() -> datetime:
    """Thời điểm hiện tại theo giờ Việt Nam, không kèm tzinfo (để lưu/so sánh nhất quán)."""
    return datetime.now(VN_TZ).replace(tzinfo=None)


def today_vn() -> date:
    return now_vn().date()


def format_vn(value) -> str:
    """Hiển thị DD/MM/YYYY HH:mm từ datetime hoặc chuỗi 'YYYY-MM-DD HH:MM:SS'."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d/%m/%Y %H:%M")
