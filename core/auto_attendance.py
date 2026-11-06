"""Điểm danh tự động bằng nhận diện khuôn mặt (chế độ VÀO / RA VỀ).

Luồng xử lý (gọi từ trang Điểm danh cho mỗi kết quả nhận diện MỚI):

    kết quả nhận diện ─▶ ConsensusTracker (cùng một mã qua nhiều lần liên tiếp)
                     ─▶ chống gọi lặp (cooldown theo mã học sinh)
                     ─▶ auto_record(): kiểm tra lịch sử trong buổi ─▶ ghi qua
                        record_student_attendance() (cùng một kho dữ liệu với
                        điểm danh thủ công; chỉ mục duy nhất của SQLite chặn ghi trùng)

Danh tính chỉ lấy từ kết quả nhận diện, không phụ thuộc học sinh/lớp đang chọn
trên giao diện. Module không phụ thuộc Streamlit để kiểm thử được.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select

from core.timeutil import now_vn
from db.attendance_repo import record_student_attendance
from db.models import AttendanceLog, SchoolClass, Student
from db.session import SessionLocal

MODE_IN = "IN"
MODE_OUT = "OUT"
MODE_LABELS = {MODE_IN: "ĐIỂM DANH VÀO", MODE_OUT: "ĐIỂM DANH RA VỀ"}

# Số lần nhận diện liên tiếp cùng một học sinh trước khi ghi (giảm nhận nhầm)
REQUIRED_CONSECUTIVE = 2
# Các lần nhận diện phải nằm trong khoảng thời gian này (giây)
CONSENSUS_WINDOW_SECONDS = 8.0
# Sau khi xử lý một học sinh, bỏ qua mã đó trong khoảng này (giây) để không truy vấn/ghi lặp
STUDENT_COOLDOWN_SECONDS = 10.0

# Kết quả trả về của auto_record
RECORDED = "recorded"
ALREADY = "already"
NO_CHECK_IN = "no_check_in"
ABSENT = "absent"
UNKNOWN_STUDENT = "unknown_student"
ERROR = "error"

TITLES = {
    (RECORDED, MODE_IN): "ĐIỂM DANH VÀO THÀNH CÔNG",
    (RECORDED, MODE_OUT): "ĐIỂM DANH RA VỀ THÀNH CÔNG",
    (ALREADY, MODE_IN): "HỌC SINH ĐÃ ĐIỂM DANH VÀO",
    (ALREADY, MODE_OUT): "HỌC SINH ĐÃ ĐIỂM DANH RA VỀ",
    (NO_CHECK_IN, MODE_OUT): "CHƯA CÓ DỮ LIỆU ĐIỂM DANH VÀO",
    (ABSENT, MODE_OUT): "HỌC SINH ĐÃ ĐƯỢC XÁC NHẬN VẮNG",
}


def default_session_name(moment=None) -> str:
    hour = (moment or now_vn()).hour
    if hour < 12:
        return "Buổi sáng"
    if hour < 18:
        return "Buổi chiều"
    return "Buổi tối"


class ConsensusTracker:
    """Chỉ xác nhận một mã khi nó xuất hiện ở `required` lần nhận diện liên tiếp gần nhau."""

    def __init__(self, required=REQUIRED_CONSECUTIVE, window_seconds=CONSENSUS_WINDOW_SECONDS):
        self.required = max(1, int(required))
        self.window_seconds = window_seconds
        self.reset()

    def reset(self):
        self.code: Optional[str] = None
        self.count = 0
        self.first_seen = 0.0

    def update(self, code: Optional[str], now: float) -> Optional[str]:
        if not code:
            self.reset()
            return None
        if code != self.code or (now - self.first_seen) > self.window_seconds:
            self.code, self.count, self.first_seen = code, 1, now
        else:
            self.count += 1
        if self.count >= self.required:
            confirmed = self.code
            self.reset()
            return confirmed
        return None


def _time_part(log_time: Optional[str]) -> Optional[str]:
    return log_time[11:19] if log_time and len(log_time) >= 19 else None


def _student_events(db, student_code, date_value, session_name):
    rows = db.scalars(
        select(AttendanceLog).where(
            AttendanceLog.student_code == student_code,
            AttendanceLog.attendance_date == date_value,
            AttendanceLog.session_name == session_name,
            AttendanceLog.attendance_method.in_(("face", "manual")),
        )
    ).all()
    return {row.log_type: row for row in rows}


def auto_record(student_code, mode, session_name, distance=None, moment=None) -> dict:
    """Kiểm tra lịch sử trong buổi rồi ghi lượt VÀO/RA cho học sinh đã nhận diện.

    Chỉ trả về RECORDED khi cơ sở dữ liệu đã ghi thành công.
    """
    if mode not in (MODE_IN, MODE_OUT):
        raise ValueError("Chế độ điểm danh không hợp lệ.")
    moment = moment or now_vn()
    date_value = moment.date().isoformat()
    result = {"student_code": student_code, "mode": mode, "session_name": session_name,
              "date": date_value, "time": moment.strftime("%H:%M:%S"), "full_name": "",
              "class_name": "", "check_in": None, "check_out": None}

    with SessionLocal() as db:
        row = db.execute(
            select(Student, SchoolClass.name)
            .join(SchoolClass, SchoolClass.id == Student.class_id)
            .where(Student.student_code == student_code, Student.status == "Đang học")
        ).first()
        if row is None:
            result.update(outcome=UNKNOWN_STUDENT, title="KHÔNG NHẬN DIỆN ĐƯỢC",
                          message=f"Mã {student_code} không thuộc học sinh đang học.")
            return result
        student, class_name = row
        result.update(full_name=student.full_name, class_name=class_name)
        class_id = student.class_id
        events = _student_events(db, student_code, date_value, session_name)

    def finish(outcome, message):
        with SessionLocal() as db:
            events_now = _student_events(db, student_code, date_value, session_name)
        result["check_in"] = _time_part(events_now["IN"].log_time) if "IN" in events_now else None
        result["check_out"] = _time_part(events_now["OUT"].log_time) if "OUT" in events_now else None
        if "IN" in events_now:
            result["status"] = events_now["IN"].attendance_status
        result.update(outcome=outcome, title=TITLES.get((outcome, mode), "THÔNG BÁO"), message=message)
        return result

    if mode == MODE_IN and "IN" in events:
        return finish(ALREADY, "Học sinh đã được điểm danh vào trong buổi này.")
    if mode == MODE_OUT:
        if "IN" not in events:
            return finish(NO_CHECK_IN, "Học sinh chưa điểm danh vào nên chưa ghi nhận ra về.")
        if events["IN"].attendance_status == "Vắng mặt":
            return finish(ABSENT, "Học sinh đã được xác nhận vắng mặt trong buổi này.")
        if "OUT" in events:
            return finish(ALREADY, "Học sinh đã được điểm danh ra về trong buổi này.")

    confidence = None
    if distance is not None and 0 <= float(distance) <= 1:
        confidence = float(distance)
    try:
        record_student_attendance(
            student_code, class_id, date_value, session_name, "Có mặt",
            method="face", confidence=confidence, attendance_type=mode,
        )
    except ValueError as error:
        text = str(error)
        # Hai yêu cầu cùng lúc: yêu cầu sau bị chỉ mục duy nhất/kiểm tra chặn -> coi là đã ghi
        if "đã có lượt" in text or "đã được ghi nhận" in text:
            return finish(ALREADY, "Học sinh đã được ghi nhận trong buổi này.")
        if "chưa có lượt điểm danh vào" in text:
            return finish(NO_CHECK_IN, "Học sinh chưa điểm danh vào nên chưa ghi nhận ra về.")
        if "vắng mặt" in text:
            return finish(ABSENT, text)
        result.update(outcome=ERROR, title="KHÔNG GHI NHẬN ĐƯỢC", message=text)
        return result
    label = "vào" if mode == MODE_IN else "ra về"
    return finish(RECORDED, f"Đã ghi nhận điểm danh {label} lúc {moment:%H:%M:%S}.")


@dataclass
class AutoAttendanceSession:
    """Trạng thái một phiên quét (lưu trong session_state). Đổi chế độ -> tạo phiên mới."""

    mode: str
    session_name: str
    required: int = REQUIRED_CONSECUTIVE
    cooldown_seconds: float = STUDENT_COOLDOWN_SECONDS
    tracker: ConsensusTracker = field(default=None)
    cooldown_until: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    last_result: Optional[dict] = None
    recorded_count: int = 0

    def __post_init__(self):
        if self.tracker is None:
            self.tracker = ConsensusTracker(self.required)

    def handle_prediction(self, prediction: Optional[dict], faces_count: int,
                          now: Optional[float] = None, moment=None) -> Optional[dict]:
        """Xử lý MỘT kết quả nhận diện mới. Trả về kết quả ghi (dict) hoặc None."""
        now = time.time() if now is None else now
        if faces_count != 1 or not prediction:
            self.tracker.reset()
            return None
        code = prediction.get("display_code") if prediction.get("is_match") else None
        if code == "Unknown":
            code = None
        confirmed = self.tracker.update(code, now)
        if not confirmed:
            return None
        if now < self.cooldown_until.get(confirmed, 0):
            return None
        self.cooldown_until[confirmed] = now + self.cooldown_seconds
        result = auto_record(confirmed, self.mode, self.session_name,
                             distance=prediction.get("confidence"), moment=moment)
        self.last_result = result
        if result["outcome"] == RECORDED:
            self.recorded_count += 1
            self.log.insert(0, result)
        return result
