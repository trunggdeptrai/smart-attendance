"""Chạy toàn bộ kiểm thử trong môi trường dữ liệu CÔ LẬP.

Lý do: các tệp test_*.py cũ ghi trực tiếp vào attendance.db (tạo hồ sơ, lượt
điểm danh thử). Trình chạy này sao chép dữ liệu sang thư mục tạm và đặt biến
môi trường SMART_ATTENDANCE_DATA_ROOT để mọi thao tác ghi chỉ diễn ra trên bản sao.

Cách dùng (từ thư mục dự án):
    python tests/run_all.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def prepare_sandbox(sandbox):
    for name in ("attendance.db",):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, sandbox / name)
    for folder in ("models", "data/faces"):
        if (ROOT / folder).exists():
            shutil.copytree(ROOT / folder, sandbox / folder)
    (sandbox / "data" / "faces").mkdir(parents=True, exist_ok=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = sorted((ROOT / "tests").glob("test_*.py"))
    results = []
    with tempfile.TemporaryDirectory(prefix="smart_attendance_test_") as tmp:
        sandbox = Path(tmp)
        prepare_sandbox(sandbox)
        env = dict(os.environ)
        env["SMART_ATTENDANCE_DATA_ROOT"] = str(sandbox)
        env.pop("SMART_ATTENDANCE_DB", None)
        env["SMART_ATTENDANCE_RESEARCH_LOG"] = "0"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(ROOT)
        db_before = (ROOT / "attendance.db").stat().st_mtime_ns if (ROOT / "attendance.db").exists() else None

        for test in tests:
            started = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, str(test)],
                cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            output = proc.stdout + proc.stderr
            ok = proc.returncode == 0 and "Traceback (most recent call last)" not in output
            results.append((test.name, ok, time.perf_counter() - started, output))

        db_after = (ROOT / "attendance.db").stat().st_mtime_ns if (ROOT / "attendance.db").exists() else None

    for name, ok, seconds, output in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} ({seconds:.1f}s)")
        if not ok:
            print("    " + "\n    ".join(output.strip().splitlines()[-15:]))
    untouched = db_before == db_after
    print(f"\nCơ sở dữ liệu thật không bị thay đổi: {'ĐÚNG' if untouched else 'SAI - KIỂM TRA LẠI'}")
    failed = [name for name, ok, *_ in results if not ok]
    print(f"Tổng: {len(results)} tệp, đạt {len(results) - len(failed)}, lỗi {len(failed)}")
    sys.exit(1 if failed or not untouched else 0)


if __name__ == "__main__":
    main()
