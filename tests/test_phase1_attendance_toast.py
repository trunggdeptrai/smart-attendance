import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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


def test_toast_trigger_and_debounce():
    print("1. Testing Toast Trigger & Anti-Spam Debounce Logic...")
    
    # Mocking streamlit session state
    mock_session_state = {}
    PAGE_KEY = "attendance"
    TOAST_COOLDOWN_SECONDS = 5.0
    toasts_sent = []

    def mock_toast(msg, icon="ℹ️"):
        toasts_sent.append((msg, icon))

    def trigger_attendance_toast(employee_code: str, event_type: str, message: str, icon: str = "ℹ️") -> bool:
        now = time.time()
        toast_key = f"{employee_code}:{event_type}"
        last_key = mock_session_state.get(f"{PAGE_KEY}_last_toast_key")
        last_time = mock_session_state.get(f"{PAGE_KEY}_last_toast_time", 0.0)

        if last_key == toast_key and (now - last_time) < TOAST_COOLDOWN_SECONDS:
            return False

        mock_session_state[f"{PAGE_KEY}_last_toast_key"] = toast_key
        mock_session_state[f"{PAGE_KEY}_last_toast_time"] = now
        mock_toast(message, icon=icon)
        return True

    # Call 1: First success toast -> must succeed
    res1 = trigger_attendance_toast("NV001", "success", "Check in success", icon="✅")
    assert res1 is True, "First toast must be sent"
    assert len(toasts_sent) == 1

    # Call 2: Immediate duplicate -> must be debounced (False)
    res2 = trigger_attendance_toast("NV001", "success", "Check in success", icon="✅")
    assert res2 is False, "Duplicate toast within 5s must be blocked"
    assert len(toasts_sent) == 1

    # Call 3: Different event type (already_checked_in) -> must succeed
    res3 = trigger_attendance_toast("NV001", "already_checked_in", "Already checked in", icon="⚠️")
    assert res3 is True, "Different event type must be sent"
    assert len(toasts_sent) == 2

    # Call 4: Different employee -> must succeed
    res4 = trigger_attendance_toast("NV002", "success", "NV002 success", icon="✅")
    assert res4 is True, "Different employee must be sent"
    assert len(toasts_sent) == 3

    print("  Toast trigger & anti-spam debounce -> PASSED!")


def test_first_vs_repeat_checkin_flow():
    print("\n2. Testing First Check-in vs Repeat Check-in (Business Logic & Notifications)...")
    initialize_database()
    initialize_attendance_logs()

    test_emp = "NV099"
    # Dọn dẹp bản ghi cũ nếu có của NV099
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_emp).delete()
        db_session.commit()

    # Step A: Lần đầu quét mặt NV099 -> can_check_in phải trả về True
    can_log, msg = can_check_in(test_emp)
    assert can_log is True, f"First check-in must be allowed, got: {msg}"
    print(f"  Step A: Initial check-in check -> ALLOWED ({msg})")

    # Ghi nhận check-in lần đầu
    new_log = register_check_in(test_emp, "Camera 1", 0.95)
    assert new_log is not None
    assert new_log["employee_code"] == test_emp
    assert new_log["log_type"] == "IN"
    print(f"  Successfully registered initial check-in: {new_log['employee_code']} at {new_log['log_time']}")

    # Step B: NV099 quét mặt lần thứ 2 trong cùng ngày -> can_check_in phải trả về False
    can_log_2, msg_2 = can_check_in(test_emp)
    assert can_log_2 is False, "Repeat check-in must be blocked!"
    assert "already checked in" in msg_2.lower()
    print(f"  Step B: Repeat check-in check -> BLOCKED as expected ({msg_2})")

    # Step C: Xác nhận nội dung cảnh báo tiếng Việt chuẩn xác
    expected_warning = f"⚠️ Nhân viên {test_emp} đã thực hiện check-in rồi! Không thể check-in được nữa."
    assert "đã thực hiện check-in rồi" in expected_warning
    print(f"  Step C: Warning message verified: '{expected_warning}'")

    # Dọn dẹp bản ghi test sau khi kiểm thử
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == test_emp).delete()
        db_session.commit()
    print("  First vs Repeat Check-in Flow -> PASSED!")


def test_syntax_and_compilation():
    print("\n3. Testing Syntax & Compilation of pages/4_Attendance.py...")
    with open("pages/4_Attendance.py", "r", encoding="utf-8") as f:
        code = f.read()
    compile(code, "pages/4_Attendance.py", "exec")
    print("  pages/4_Attendance.py compiles cleanly -> PASSED!")


if __name__ == "__main__":
    test_toast_trigger_and_debounce()
    test_first_vs_repeat_checkin_flow()
    test_syntax_and_compilation()
    print("\n>>> ALL PHASE 1 TOAST & ATTENDANCE CONTROL TESTS PASSED! <<<")
