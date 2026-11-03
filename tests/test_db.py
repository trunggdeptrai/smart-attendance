import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import create_employee, get_employee_codes, update_employee, delete_employee, get_all_employees
from db.attendance_repo import register_check_in, register_check_out, get_today_logs

print("Testing database...")
try:
    code = create_employee("Test Name", "IT")
    print(f"Created: {code}")
    employees = get_all_employees()
    last_id = None
    for emp in employees:
        if emp.employee_code == code:
            last_id = emp.id
            break
    
    update_employee(last_id, "Updated Name", "HR")
    print("Updated")
    
    # Đảm bảo dọn dẹp các log cũ nếu có của mã nhân viên test để test chạy độc lập (idempotent)
    from db.session import SessionLocal
    from db.models import AttendanceLog
    with SessionLocal() as db_session:
        db_session.query(AttendanceLog).filter(AttendanceLog.employee_code == code).delete()
        db_session.commit()

    register_check_in(code, "Laptop", 0.95)
    print("Checked in")
    
    logs = get_today_logs(code)
    print(f"Logs: {logs}")
    
    register_check_out(code, "Laptop", 0.98)
    print("Checked out")
    
    delete_employee(last_id)
    print("Deleted")
    print("All tests passed!")
except Exception as e:
    import traceback
    traceback.print_exc()
