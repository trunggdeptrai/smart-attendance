"""Kiểm thử điểm danh tự động (14 tình huống) trên dữ liệu tạm – không chạm DB thật."""

import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

if not os.environ.get("SMART_ATTENDANCE_DATA_ROOT"):
    os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_auto_test_")
os.environ["SMART_ATTENDANCE_RESEARCH_LOG"] = "0"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import auto_attendance as aa  # noqa: E402
from core import paths  # noqa: E402
from core.timeutil import now_vn, today_vn  # noqa: E402
from db.attendance_repo import record_student_attendance  # noqa: E402
from db.database import create_class, create_student  # noqa: E402

SESSION = "Buổi sáng"


def match(code, distance=0.35):
    return {"is_match": True, "display_code": code, "predicted_code": code, "confidence": distance}


UNKNOWN = {"is_match": False, "display_code": "Unknown", "predicted_code": "HS999", "confidence": 0.55}


def db_rows(code):
    connection = sqlite3.connect(paths.DB_PATH)
    try:
        return connection.execute(
            "SELECT log_type, attendance_status, log_time FROM attendance_logs "
            "WHERE student_code=? AND attendance_date=? AND session_name=? ORDER BY log_type",
            (code, today_vn().isoformat(), SESSION),
        ).fetchall()
    finally:
        connection.close()


class AutoAttendanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert paths.DATA_ROOT != paths.PROJECT_ROOT, "phải chạy trên dữ liệu tạm"
        stamp = datetime.now().strftime("%H%M%S%f")
        class_id = create_class(f"Lớp tự động {stamp}")
        cls.a = create_student("Học sinh A", class_id, student_code=f"HSA{stamp}")
        cls.b = create_student("Học sinh B", class_id, student_code=f"HSB{stamp}")
        cls.c = create_student("Học sinh C", class_id, student_code=f"HSC{stamp}")
        cls.d = create_student("Học sinh D", class_id, student_code=f"HSD{stamp}")
        cls.class_id = class_id

    def scan(self, mode, required=2):
        return aa.AutoAttendanceSession(mode, SESSION, required=required, cooldown_seconds=10)

    # 1. Điểm danh vào lần đầu
    def test_01_check_in_first_time(self):
        scan = self.scan(aa.MODE_IN)
        self.assertIsNone(scan.handle_prediction(match(self.a), 1, now=100))  # lần 1: chưa đủ nhất quán
        result = scan.handle_prediction(match(self.a), 1, now=101)
        self.assertEqual(result["outcome"], aa.RECORDED)
        self.assertEqual(result["title"], "ĐIỂM DANH VÀO THÀNH CÔNG")
        self.assertIsNotNone(result["check_in"])
        self.assertEqual([r[0] for r in db_rows(self.a)], ["IN"])

    # 2. Điểm danh vào lần thứ hai (phiên quét mới)
    def test_02_check_in_second_time(self):
        result = aa.auto_record(self.a, aa.MODE_IN, SESSION)
        self.assertEqual(result["outcome"], aa.ALREADY)
        self.assertEqual(result["title"], "HỌC SINH ĐÃ ĐIỂM DANH VÀO")
        self.assertEqual(len(db_rows(self.a)), 1)

    # 3. Một học sinh xuất hiện liên tục trước camera (hàng trăm kết quả)
    def test_03_continuous_presence(self):
        scan = self.scan(aa.MODE_IN)
        outcomes = [scan.handle_prediction(match(self.b), 1, now=200 + i * 0.3) for i in range(300)]
        recorded = [o for o in outcomes if o and o["outcome"] == aa.RECORDED]
        db_calls = [o for o in outcomes if o]
        self.assertEqual(len(recorded), 1)
        self.assertLessEqual(len(db_calls), 10)  # cooldown 10 s trong 90 s -> tối đa ~9 lần truy vấn
        self.assertEqual(len(db_rows(self.b)), 1)

    # 4. Hai học sinh lần lượt xuất hiện
    def test_04_two_students_in_turn(self):
        scan = self.scan(aa.MODE_IN)
        scan.handle_prediction(match(self.c), 1, now=300)
        r1 = scan.handle_prediction(match(self.c), 1, now=301)
        scan.handle_prediction(match(self.d), 1, now=303)
        r2 = scan.handle_prediction(match(self.d), 1, now=304)
        self.assertEqual((r1["outcome"], r2["outcome"]), (aa.RECORDED, aa.RECORDED))
        self.assertEqual([x["student_code"] for x in scan.log], [self.d, self.c])

    # 5. Học sinh chưa đăng ký khuôn mặt -> nhận diện ra Unknown, không ghi
    def test_05_unregistered_face(self):
        scan = self.scan(aa.MODE_IN)
        for i in range(20):
            self.assertIsNone(scan.handle_prediction(UNKNOWN, 1, now=400 + i))
        self.assertIsNone(scan.last_result)
        # mã không thuộc học sinh đang học cũng không được ghi
        self.assertEqual(aa.auto_record("HS_KHONG_TON_TAI", aa.MODE_IN, SESSION)["outcome"], aa.UNKNOWN_STUDENT)

    # 6. Không đủ tin cậy / kết quả dao động giữa hai người -> không ghi
    def test_06_inconsistent_results(self):
        scan = self.scan(aa.MODE_IN)
        sequence = [match(self.a), UNKNOWN, match(self.b), match(self.a), UNKNOWN] * 4
        outcomes = [scan.handle_prediction(p, 1, now=500 + i) for i, p in enumerate(sequence)]
        self.assertTrue(all(o is None for o in outcomes))
        # kết quả cách nhau quá cửa sổ thời gian cũng không cộng dồn
        tracker = aa.ConsensusTracker(required=2, window_seconds=8)
        self.assertIsNone(tracker.update("X", 0))
        self.assertIsNone(tracker.update("X", 30))
        self.assertEqual(tracker.update("X", 31), "X")
        # nhiều khuôn mặt trong khung -> không ghi
        scan2 = self.scan(aa.MODE_IN)
        self.assertIsNone(scan2.handle_prediction(match(self.d), 2, now=600))
        self.assertIsNone(scan2.handle_prediction(match(self.d), 2, now=601))

    # 7. Ra về khi đã có giờ vào
    def test_07_check_out_after_check_in(self):
        scan = self.scan(aa.MODE_OUT)
        scan.handle_prediction(match(self.a), 1, now=700)
        result = scan.handle_prediction(match(self.a), 1, now=701)
        self.assertEqual(result["outcome"], aa.RECORDED)
        self.assertEqual(result["title"], "ĐIỂM DANH RA VỀ THÀNH CÔNG")
        self.assertTrue(result["check_in"] and result["check_out"])
        self.assertEqual([r[0] for r in db_rows(self.a)], ["IN", "OUT"])

    # 8. Ra về khi chưa có giờ vào
    def test_08_check_out_without_check_in(self):
        stamp = datetime.now().strftime("%H%M%S%f")
        code = create_student("Học sinh E", self.class_id, student_code=f"HSE{stamp}")
        result = aa.auto_record(code, aa.MODE_OUT, SESSION)
        self.assertEqual(result["outcome"], aa.NO_CHECK_IN)
        self.assertEqual(result["title"], "CHƯA CÓ DỮ LIỆU ĐIỂM DANH VÀO")
        self.assertEqual(db_rows(code), [])

    # 9. Ra về lần thứ hai
    def test_09_check_out_second_time(self):
        result = aa.auto_record(self.a, aa.MODE_OUT, SESSION)
        self.assertEqual(result["outcome"], aa.ALREADY)
        self.assertEqual(result["title"], "HỌC SINH ĐÃ ĐIỂM DANH RA VỀ")
        self.assertEqual(len(db_rows(self.a)), 2)

    # 10. Tắt camera rồi bật lại (phiên quét mới, cùng chế độ) -> không ghi trùng
    def test_10_restart_camera(self):
        first = self.scan(aa.MODE_IN)
        first.handle_prediction(match(self.b), 1, now=1000)
        first.handle_prediction(match(self.b), 1, now=1001)
        second = self.scan(aa.MODE_IN)  # trang tạo phiên mới khi bật lại
        self.assertEqual(second.log, [])
        second.handle_prediction(match(self.b), 1, now=1002)
        result = second.handle_prediction(match(self.b), 1, now=1003)
        self.assertEqual(result["outcome"], aa.ALREADY)
        self.assertEqual(len(db_rows(self.b)), 1)

    # 11. Chuyển từ VÀO sang RA VỀ: phiên mới, bộ đếm và danh sách riêng
    def test_11_switch_mode(self):
        scan_in = self.scan(aa.MODE_IN)
        scan_in.handle_prediction(match(self.c), 1, now=1100)  # 1 lần, chưa đủ
        scan_out = self.scan(aa.MODE_OUT)
        self.assertIsNone(scan_out.handle_prediction(match(self.c), 1, now=1101))  # không thừa hưởng bộ đếm cũ
        result = scan_out.handle_prediction(match(self.c), 1, now=1102)
        self.assertEqual(result["outcome"], aa.RECORDED)
        self.assertEqual(result["mode"], aa.MODE_OUT)

    # 12. Mất kết nối camera / khung không có mặt -> không ghi, bộ đếm đặt lại
    def test_12_camera_lost(self):
        scan = self.scan(aa.MODE_IN)
        scan.handle_prediction(match(self.d), 1, now=1200)
        self.assertIsNone(scan.handle_prediction(None, 0, now=1201))  # mất khung hình
        self.assertEqual(scan.tracker.count, 0)
        self.assertIsNone(scan.handle_prediction(match(self.d), 1, now=1202))  # phải đếm lại từ đầu

    # 13. Khởi động lại ứng dụng: dữ liệu cũ còn nguyên (đọc bằng kết nối mới)
    def test_13_data_persists(self):
        rows = db_rows(self.a)
        self.assertEqual([r[0] for r in rows], ["IN", "OUT"])
        for _, status, log_time in rows:
            self.assertEqual(status, "Có mặt")
            self.assertEqual(log_time[:10], today_vn().isoformat())

    # 14. Hai yêu cầu ghi cùng lúc -> chỉ một bản ghi
    def test_14_concurrent_requests(self):
        stamp = datetime.now().strftime("%H%M%S%f")
        code = create_student("Học sinh F", self.class_id, student_code=f"HSF{stamp}")
        results, barrier = [], threading.Barrier(4)

        def worker():
            barrier.wait()
            results.append(aa.auto_record(code, aa.MODE_IN, SESSION)["outcome"])

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count(aa.RECORDED), 1, results)
        self.assertEqual(set(results) - {aa.RECORDED}, {aa.ALREADY})
        self.assertEqual(len(db_rows(code)), 1)

    # Bổ sung: giờ Việt Nam và học sinh đã xác nhận vắng
    def test_15_vietnam_time_and_absent(self):
        vn = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)
        self.assertLess(abs((now_vn() - vn).total_seconds()), 5)
        self.assertEqual(aa.default_session_name(datetime(2026, 11, 6, 7, 0)), "Buổi sáng")
        self.assertEqual(aa.default_session_name(datetime(2026, 11, 6, 13, 0)), "Buổi chiều")
        self.assertEqual(aa.default_session_name(datetime(2026, 11, 6, 19, 0)), "Buổi tối")
        stamp = datetime.now().strftime("%H%M%S%f")
        code = create_student("Học sinh G", self.class_id, student_code=f"HSG{stamp}")
        record_student_attendance(code, self.class_id, today_vn(), SESSION, "Vắng mặt", method="manual")
        self.assertEqual(aa.auto_record(code, aa.MODE_IN, SESSION)["outcome"], aa.ALREADY)
        self.assertEqual(aa.auto_record(code, aa.MODE_OUT, SESSION)["outcome"], aa.ABSENT)
        self.assertEqual(len(db_rows(code)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
