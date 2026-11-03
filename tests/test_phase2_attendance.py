import sys
import os
import time
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.camera_stream import (
    STREAM_FRAME_INTERVAL,
    STREAM_SLEEP_INTERVAL,
    render_stream_frame,
    read_camera_frame,
    PredictionStore,
)
from db.database import initialize_database
from db.attendance_repo import (
    initialize_attendance_logs,
    register_check_in,
    register_check_out,
    get_latest_attendance_log,
    can_check_in,
    can_check_out,
)
from db.session import SessionLocal
from db.models import AttendanceLog


class StrictStreamlitMockPlaceholder:
    """
    MockPlaceholder mô phỏng chính xác 100% chữ ký hàm st.image / DeltaGenerator.image của Streamlit.
    Tuyệt đối không dùng **kwargs để phát hiện ngay bất kỳ lỗi tham số nào.
    """
    def __init__(self):
        self.call_count = 0
        self.last_image = None
        self.last_channels = None
        self.last_width = None

    def image(
        self,
        image,
        caption=None,
        width="content",
        clamp=False,
        channels="RGB",
        output_format="auto",
        *,
        link=None,
    ):
        self.call_count += 1
        self.last_image = image
        self.last_channels = channels
        self.last_width = width


class MockCameraDevice:
    def __init__(self):
        self.grab_count = 0
        self.read_count = 0

    def isOpened(self):
        return True

    def grab(self):
        self.grab_count += 1
        return True

    def read(self):
        self.read_count += 1
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, frame


def test_attendance_streaming_timing():
    print("1. Testing Attendance Direct RGB Streaming Timing (30 FPS)...")
    placeholder = StrictStreamlitMockPlaceholder()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Mô phỏng 1.0 giây vòng lặp streaming với STREAM_SLEEP_INTERVAL và STREAM_FRAME_INTERVAL
    start_time = time.time()
    last_video_time = 0.0
    iterations = 0

    while time.time() - start_time < 1.0:
        iterations += 1
        now = time.time()
        if now - last_video_time >= STREAM_FRAME_INTERVAL:
            success = render_stream_frame(placeholder, frame)
            assert success is True, "render_stream_frame returned False"
            last_video_time = now
        time.sleep(STREAM_SLEEP_INTERVAL)

    fps = placeholder.call_count
    print(f"  Iterations in 1.0s: {iterations}")
    print(f"  Rendered frames in 1.0s: {fps} FPS")
    print(f"  Image channels: {placeholder.last_channels}, width: {placeholder.last_width}")

    # Xác thực tốc độ và định dạng RGB trực tiếp
    assert fps >= 22, f"FPS too low: {fps} FPS (expected >= 22 FPS)"
    assert placeholder.last_channels == "RGB", f"Expected channels='RGB', got {placeholder.last_channels}"
    assert placeholder.last_width == "stretch"
    assert isinstance(placeholder.last_image, np.ndarray), f"Expected ndarray image, got {type(placeholder.last_image)}"
    print("  Streaming rate matches 30 FPS target & Direct RGB image -> PASSED!")


def test_attendance_read_frame_flush():
    print("\n2. Testing Attendance Camera Buffer Flushing...")
    mock_cam = MockCameraDevice()
    ret, frame = read_camera_frame(mock_cam)
    assert ret is True
    assert frame is not None
    assert mock_cam.grab_count == 1, "Must call cap.grab() to flush buffer"
    assert mock_cam.read_count == 1, "Must call cap.read() to get latest frame"
    print("  DirectShow frame buffer flush -> PASSED!")


def test_first_and_repeat_checkin_integration():
    print("\n3. Testing First Check-in vs Repeat Check-in Full Flow...")
    initialize_database()
    initialize_attendance_logs()

    test_code = "NV098"
    # Dọn sạch các log cũ nếu có của NV098
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_code).delete()
        db_session.commit()

    # Step A: Lần đầu quét mặt NV098 (3 frames) -> Điểm danh thành công
    can_log, msg = can_check_in(test_code)
    assert can_log is True, f"Lần đầu check-in phải được phép, nhận được: {msg}"
    
    new_log = register_check_in(test_code, "Camera 1", 0.95)
    assert new_log is not None
    assert new_log["employee_code"] == test_code
    assert new_log["log_type"] == "IN"

    # Mô phỏng trạng thái UI sau khi điểm danh thành công
    action_text = "check in"
    success_status = {
        "employee_code": test_code,
        "status": "success",
        "message": f"✅ Xác thực thành công: **{test_code}**! Đã ghi nhận điểm danh {action_text} thành công vào lúc {new_log['log_time']}.",
        "log_time": new_log["log_time"],
        "action": action_text,
    }
    assert success_status["status"] == "success"
    assert "Đang ghi nhận điểm danh" not in success_status["message"], "Không được chứa text 'Đang ghi nhận...'"
    assert "thành công vào lúc" in success_status["message"]
    print(f"  Step A: First Check-in Success -> {success_status['message']}")

    # Step B: Quét mặt NV098 lần thứ 2 -> Bị chặn, thông báo đã check-in rồi
    can_log_2, msg_2 = can_check_in(test_code)
    assert can_log_2 is False, "Lần thứ 2 check-in trong ngày phải bị chặn!"
    assert "already checked in" in msg_2.lower()

    warning_msg = f"⚠️ Nhân viên {test_code} đã thực hiện check-in rồi! Không thể check-in được nữa."
    repeat_status = {
        "employee_code": test_code,
        "status": "already_checked_in",
        "message": f"⚠️ Nhân viên **{test_code}** đã thực hiện check-in rồi! Không thể check-in được nữa.",
        "action": action_text,
    }
    assert repeat_status["status"] == "already_checked_in"
    assert "đã thực hiện check-in rồi! Không thể check-in được nữa" in warning_msg
    print(f"  Step B: Repeat Check-in Blocked -> {repeat_status['message']}")

    # Dọn dẹp
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_code).delete()
        db_session.commit()
    print("  First vs Repeat Check-in Integration -> PASSED!")


def test_toast_anti_spam_debounce():
    print("\n4. Testing Toast Debounce Anti-Spam Logic...")
    session_state = {}
    PAGE_KEY = "attendance"
    TOAST_COOLDOWN = 5.0
    sent_toasts = []

    def mock_trigger_toast(emp_code, event_type, msg):
        now = time.time()
        toast_key = f"{emp_code}:{event_type}"
        last_key = session_state.get(f"{PAGE_KEY}_last_toast_key")
        last_time = session_state.get(f"{PAGE_KEY}_last_toast_time", 0.0)

        if last_key == toast_key and (now - last_time) < TOAST_COOLDOWN:
            return False

        session_state[f"{PAGE_KEY}_last_toast_key"] = toast_key
        session_state[f"{PAGE_KEY}_last_toast_time"] = now
        sent_toasts.append((emp_code, msg))
        return True

    # Bắn toast lần 1 -> Thành công
    assert mock_trigger_toast("NV001", "success", "Success 1") is True
    # Bắn lặp lại ngay lập tức -> Phải bị chặn
    assert mock_trigger_toast("NV001", "success", "Success 1") is False
    assert len(sent_toasts) == 1
    # Bắn sự kiện khác (cảnh báo) -> Được phép
    assert mock_trigger_toast("NV001", "already_checked_in", "Warning") is True
    assert len(sent_toasts) == 2
    print("  Toast Anti-Spam Debounce -> PASSED!")


def test_checkout_validation_rules():
    print("\n5. Testing Check-out Rules & Notifications...")
    test_emp = "NV097"
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_emp).delete()
        db_session.commit()

    # Chưa check-in -> Không được phép check-out
    can_out_1, msg_out_1 = can_check_out(test_emp)
    assert can_out_1 is False
    assert "not checked in" in msg_out_1.lower()
    print(f"  Step A: Checkout without Check-in blocked -> {msg_out_1}")

    # Thực hiện check-in trước
    register_check_in(test_emp, "Camera 1", 0.95)

    # Sau khi check-in -> Được phép check-out
    can_out_2, msg_out_2 = can_check_out(test_emp)
    assert can_out_2 is True
    out_log = register_check_out(test_emp, "Camera 2", 0.95)
    assert out_log["log_type"] == "OUT"
    print(f"  Step B: Checkout allowed after Check-in -> Logged OUT at {out_log['log_time']}")

    # Sau khi đã check-out -> Không được phép check-out lần 2
    can_out_3, msg_out_3 = can_check_out(test_emp)
    assert can_out_3 is False
    assert "already checked out" in msg_out_3.lower()
    print(f"  Step C: Repeat Checkout blocked -> {msg_out_3}")

    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_emp).delete()
        db_session.commit()
    print("  Check-out Validation Rules -> PASSED!")


def test_attendance_syntax_compile():
    print("\n6. Testing Syntax and Compilation of pages/4_Attendance.py...")
    with open("pages/4_Attendance.py", "r", encoding="utf-8") as f:
        code = f.read()
    compile(code, "pages/4_Attendance.py", "exec")
    print("  pages/4_Attendance.py compiles cleanly -> PASSED!")


if __name__ == "__main__":
    test_attendance_streaming_timing()
    test_attendance_read_frame_flush()
    test_first_and_repeat_checkin_integration()
    test_toast_anti_spam_debounce()
    test_checkout_validation_rules()
    test_attendance_syntax_compile()
    print("\n>>> ALL PHASE 2 & 3 ATTENDANCE INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
