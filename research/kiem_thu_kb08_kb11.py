"""Kiểm thử kỹ thuật KB07 (phần đa khuôn mặt) và KB08–KB11 trên DỮ LIỆU MINH HỌA.

- Không dùng camera, không dùng ảnh khuôn mặt: kết quả nhận diện được GIẢ LẬP làm đầu vào
  (đúng định dạng mà trang Điểm danh tự động nhận từ bộ nhận diện).
- Mục đích: kiểm chứng logic ghi nhận (vào, ra về, chống trùng, lịch sử, xuất Excel), KHÔNG đo độ chính xác nhận diện.
- Chạy trên thư mục dữ liệu tạm (SMART_ATTENDANCE_DATA_ROOT), không chạm cơ sở dữ liệu thật.

Cách chạy:  python research/kiem_thu_kb08_kb11.py [thư_mục_kết_quả]
"""
import io
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_kb_")
os.environ["SMART_ATTENDANCE_RESEARCH_LOG"] = "0"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402

from core import auto_attendance as aa  # noqa: E402
from core import paths  # noqa: E402
from core.attendance_export import build_attendance_excel  # noqa: E402
from core.timeutil import now_vn, today_vn  # noqa: E402
from db.attendance_repo import get_student_attendance_dataframe  # noqa: E402
from db.database import create_class, create_student  # noqa: E402

assert paths.DATA_ROOT != paths.PROJECT_ROOT
SESSION = "Buổi sáng"
N_STUDENTS = 10


def match(code, distance=0.35):
    return {"is_match": True, "display_code": code, "predicted_code": code, "confidence": distance}


UNKNOWN = {"is_match": False, "display_code": "Unknown", "predicted_code": "HS999", "confidence": 0.55}


def rows(code=None, log_type=None):
    con = sqlite3.connect(paths.DB_PATH)
    try:
        q = "SELECT student_code, log_type FROM attendance_logs WHERE attendance_date=? AND session_name=?"
        args = [today_vn().isoformat(), SESSION]
        if code:
            q += " AND student_code=?"; args.append(code)
        if log_type:
            q += " AND log_type=?"; args.append(log_type)
        return con.execute(q, args).fetchall()
    finally:
        con.close()


def stream(scan, code, start, seconds, step=0.5, faces=1, pred=None):
    """Giả lập luồng kết quả nhận diện: mỗi `step` giây một kết quả, trong `seconds` giây."""
    out, t, calls, times = [], start, 0, []
    while t < start + seconds:
        t0 = time.perf_counter()
        r = scan.handle_prediction(pred if pred is not None else match(code), faces, now=t)
        if r:
            calls += 1
            times.append((time.perf_counter() - t0) * 1000)
            out.append((round(t - start, 2), r["outcome"]))
        t += step
    return out, calls, times


cls = create_class("Lớp DEMO kiểm thử")
cid = cls["id"] if isinstance(cls, dict) else cls
codes = []
for i in range(N_STUDENTS + 5):
    c = create_student(f"Học sinh minh họa {i + 1:02d}", cid, student_code=f"DM{i + 1:03d}")
    codes.append(c["student_code"] if isinstance(c, dict) else c)
main, never_in = codes[:N_STUDENTS], codes[N_STUDENTS:]
R = {"dieu_kien": {
    "thoi_diem": now_vn().strftime("%d/%m/%Y %H:%M"), "may": platform.platform(), "python": platform.python_version(),
    "du_lieu": f"Lớp DEMO, {len(codes)} học sinh minh họa (không có ảnh, không có người thật)",
    "dau_vao": "Kết quả nhận diện giả lập, 2 kết quả/giây (mỗi 0,5 s), khung hình 1 khuôn mặt trừ khi ghi khác",
    "tham_so": f"REQUIRED_CONSECUTIVE={aa.REQUIRED_CONSECUTIVE}, CONSENSUS_WINDOW={aa.CONSENSUS_WINDOW_SECONDS}s, COOLDOWN={aa.STUDENT_COOLDOWN_SECONDS}s"}}

# ---------------- KB07 (phần kỹ thuật): khung hình có 2 hoặc 3 khuôn mặt
scan = aa.AutoAttendanceSession(aa.MODE_IN, SESSION)
ev2, _, _ = stream(scan, main[0], 0, 10, faces=2)
ev3, _, _ = stream(scan, main[0], 20, 10, faces=3)
R["KB07"] = {"luot": 40, "ghi": len(ev2) + len(ev3), "ban_ghi_csdl": len(rows(main[0])),
             "ky_vong": "0 bản ghi khi khung hình có hơn 1 khuôn mặt"}

# ---------------- KB08: điểm danh vào
scan = aa.AutoAttendanceSession(aa.MODE_IN, SESSION)
first_record_at, latency = [], []
for k, c in enumerate(main):
    ev, calls, tms = stream(scan, c, 1000 + k * 30, 3)
    rec = [t for t, o in ev if o == aa.RECORDED]
    first_record_at.append(rec[0] if rec else None)
    latency += tms
in_rows = rows(log_type="IN")
R["KB08"] = {"so_hoc_sinh": N_STUDENTS, "ghi_thanh_cong": sum(1 for x in first_record_at if x is not None),
             "ban_ghi_IN": len(in_rows), "ghi_sau_giay": sorted(set(first_record_at)),
             "thoi_gian_xu_ly_ghi_ms_tb": round(sum(latency) / len(latency), 1), "thoi_gian_xu_ly_ghi_ms_max": round(max(latency), 1)}

# ---------------- KB09: ra về (có lượt vào / chưa có lượt vào)
scan = aa.AutoAttendanceSession(aa.MODE_OUT, SESSION)
out_ok = out_reject = 0
for k, c in enumerate(main):
    ev, _, _ = stream(scan, c, 5000 + k * 30, 3)
    out_ok += any(o == aa.RECORDED for _, o in ev)
for k, c in enumerate(never_in):
    ev, _, _ = stream(scan, c, 8000 + k * 30, 3)
    out_reject += any(o == aa.NO_CHECK_IN for _, o in ev)
R["KB09"] = {"co_luot_vao": N_STUDENTS, "ghi_ra_ve": out_ok, "ban_ghi_OUT": len(rows(log_type="OUT")),
             "chua_vao": len(never_in), "tu_choi_dung": out_reject,
             "ban_ghi_cua_HS_chua_vao": sum(len(rows(c)) for c in never_in)}

# ---------------- KB10: điểm danh trùng
scan = aa.AutoAttendanceSession(aa.MODE_IN, SESSION)
dup_calls, dup_records = 0, 0
for k, c in enumerate(main):
    ev, calls, _ = stream(scan, c, 20000 + k * 100, 20)           # đứng 20 giây
    ev2, calls2, _ = stream(scan, c, 20000 + k * 100 + 60, 5)     # rời đi, quay lại sau 60 giây
    dup_calls += calls + calls2
    dup_records += sum(1 for _, o in ev + ev2 if o == aa.RECORDED)
scan_u = aa.AutoAttendanceSession(aa.MODE_IN, SESSION)
evu, _, _ = stream(scan_u, None, 30000, 10, pred=UNKNOWN)
R["KB10"] = {"so_hoc_sinh": N_STUDENTS, "luot_nhan_dien_gia_lap": N_STUDENTS * 50, "lan_truy_van_ghi": dup_calls,
             "ban_ghi_moi": dup_records, "ban_ghi_IN_sau_cung": len(rows(log_type="IN")),
             "nguoi_chua_dang_ky_20_luot_ghi": len(evu)}

# ---------------- KB11: lịch sử + xuất Excel
df = get_student_attendance_dataframe(today_vn().isoformat(), cid)
n_in = int((df["attendance_type"] == "IN").sum()) if "attendance_type" in df else None
n_out = int((df["attendance_type"] == "OUT").sum()) if "attendance_type" in df else None
import pandas as pd  # noqa: E402
from db.attendance_repo import get_student_attendance_summary_dataframe  # noqa: E402

summ = get_student_attendance_summary_dataframe(today_vn().isoformat(), cid)
summ = summ[summ["session_name"] == SESSION]
report = pd.DataFrame([{
    "Mã học sinh": r.student_code, "Họ và tên": r.student_name, "Lớp": r.class_name, "Ngày": today_vn(),
    "Giờ vào": r.check_in_time or "Chưa ghi nhận", "Giờ ra": r.check_out_time or "Chưa ghi nhận",
    "Trạng thái": r.attendance_status} for r in summ.itertuples()])
R["KB11_bao_cao"] = {"dong_bao_cao": len(report), "co_gio_vao": int((report["Giờ vào"] != "Chưa ghi nhận").sum()),
                     "co_gio_ra": int((report["Giờ ra"] != "Chưa ghi nhận").sum())}
xls = build_attendance_excel(report, "Kiểm thử KB11")
wb = load_workbook(io.BytesIO(xls if isinstance(xls, (bytes, bytearray)) else xls.getvalue()))
ws = wb.active
data_rows = sum(1 for r in ws.iter_rows(min_row=1, values_only=True) if any(str(v).startswith("DM0") for v in r if v))
R["KB11"] = {"ban_ghi_lich_su": len(df), "IN": n_in, "OUT": n_out, "ky_vong": f"{N_STUDENTS} IN + {N_STUDENTS} OUT",
             "excel_mo_duoc": True, "dong_du_lieu_excel": data_rows}

out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "research_results"
out.mkdir(parents=True, exist_ok=True)
(out / "kb08_kb11_ket_qua.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=2))
