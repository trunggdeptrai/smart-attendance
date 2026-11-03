from datetime import date, datetime
import pandas as pd
import streamlit as st
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from db.session import SessionLocal, engine, init_db
from db.models import AttendanceLog, Employee, SchoolClass, Student

VALID_LOG_TYPES = {"IN", "OUT"}

def initialize_attendance_logs():
    init_db()

def _normalize_log_type(log_type):
    normalized_log_type = str(log_type).upper().strip()
    if normalized_log_type not in VALID_LOG_TYPES:
        raise ValueError("log_type must be 'IN' or 'OUT'.")
    return normalized_log_type

def _normalize_timestamp(reference_time=None):
    timestamp = reference_time or datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def _normalize_date(reference_time=None):
    timestamp = reference_time or datetime.now()
    return timestamp.strftime("%Y-%m-%d")

def _row_to_dict(log_obj):
    if not log_obj:
        return None
    return {
        "id": log_obj.id,
        "employee_code": log_obj.employee_code,
        "log_time": log_obj.log_time,
        "log_type": log_obj.log_type,
        "camera_source": log_obj.camera_source,
        "confidence": log_obj.confidence,
        "student_code": log_obj.student_code,
        "class_id": log_obj.class_id,
        "attendance_date": log_obj.attendance_date,
        "session_name": log_obj.session_name,
        "attendance_status": log_obj.attendance_status,
        "attendance_method": log_obj.attendance_method,
        "confirmed": log_obj.confirmed,
    }

def clear_attendance_cache():
    get_latest_attendance_log.clear()
    get_attendance_count.clear()
    get_today_attendance_dataframe.clear()
    get_attendance_history_dataframe.clear()
    get_student_attendance_dataframe.clear()
    get_student_attendance_summary_dataframe.clear()

def create_attendance_log(
    employee_code, log_type, camera_source, confidence, reference_time=None
):
    initialize_attendance_logs()
    normalized_log_type = _normalize_log_type(log_type)
    log_time = _normalize_timestamp(reference_time)
    normalized_confidence = None if confidence is None else round(float(confidence), 2)

    with SessionLocal() as db:
        new_log = AttendanceLog(
            employee_code=employee_code,
            log_time=log_time,
            log_type=normalized_log_type,
            camera_source=camera_source,
            confidence=normalized_confidence,
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        result = _row_to_dict(new_log)

    clear_attendance_cache()
    return result

@st.cache_data(show_spinner=False)
def get_latest_attendance_log(employee_code=None, log_type=None):
    initialize_attendance_logs()
    with SessionLocal() as db:
        stmt = select(AttendanceLog)
        if employee_code:
            stmt = stmt.where(AttendanceLog.employee_code == employee_code)
        if log_type:
            stmt = stmt.where(AttendanceLog.log_type == _normalize_log_type(log_type))
        
        stmt = stmt.order_by(desc(AttendanceLog.log_time), desc(AttendanceLog.id)).limit(1)
        log_obj = db.scalars(stmt).first()
        return _row_to_dict(log_obj)

def get_today_logs(employee_code, reference_time=None):
    initialize_attendance_logs()
    current_date = _normalize_date(reference_time)

    with SessionLocal() as db:
        stmt = select(AttendanceLog).where(
            and_(
                AttendanceLog.employee_code == employee_code,
                func.substr(AttendanceLog.log_time, 1, 10) == current_date
            )
        ).order_by(AttendanceLog.log_time, AttendanceLog.id)
        
        logs = db.scalars(stmt).all()
        return [_row_to_dict(log) for log in logs]

@st.cache_data(show_spinner=False)
def get_attendance_count(log_type=None, reference_time=None):
    initialize_attendance_logs()
    current_date = _normalize_date(reference_time)

    with SessionLocal() as db:
        stmt = select(func.count(AttendanceLog.id)).where(
            func.substr(AttendanceLog.log_time, 1, 10) == current_date
        )
        if log_type:
            stmt = stmt.where(AttendanceLog.log_type == _normalize_log_type(log_type))
        return db.scalar(stmt) or 0

@st.cache_data(show_spinner=False)
def get_today_attendance_dataframe(reference_time=None):
    initialize_attendance_logs()
    current_date = _normalize_date(reference_time)
    
    query = (
        "SELECT id, employee_code, log_time, log_type, camera_source, confidence "
        f"FROM attendance_logs WHERE substr(log_time, 1, 10) = '{current_date}' "
        "ORDER BY log_time DESC, id DESC"
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def can_check_in(employee_code, reference_time=None):
    today_logs = get_today_logs(employee_code, reference_time)
    has_check_in_today = any(log["log_type"] == "IN" for log in today_logs)

    if not has_check_in_today:
        return True, "The employee can check in today."
    return False, "The employee has already checked in today."

def can_check_out(employee_code, reference_time=None):
    today_logs = get_today_logs(employee_code, reference_time)

    if not today_logs:
        return False, "The employee has not checked in today, so check-out is not allowed."

    latest_log = today_logs[-1]
    has_check_in_today = any(log["log_type"] == "IN" for log in today_logs)

    if not has_check_in_today:
        return False, "The employee has not checked in today, so check-out is not allowed."

    if latest_log["log_type"] == "OUT":
        return False, "The employee has already checked out today."

    return True, "The employee can check out today."

def register_check_in(employee_code, camera_source, confidence, reference_time=None):
    can_log, message = can_check_in(employee_code, reference_time)
    if not can_log:
        raise ValueError(message)
    return create_attendance_log(employee_code, "IN", camera_source, confidence, reference_time)

def register_check_out(employee_code, camera_source, confidence, reference_time=None):
    can_log, message = can_check_out(employee_code, reference_time)
    if not can_log:
        raise ValueError(message)
    return create_attendance_log(employee_code, "OUT", camera_source, confidence, reference_time)

@st.cache_data(show_spinner=False)
def get_attendance_history_dataframe(employee_code=None, log_type=None):
    initialize_attendance_logs()
    
    query = (
        "SELECT al.id, al.employee_code, e.name, al.log_time, al.log_type, "
        "al.camera_source, al.confidence "
        "FROM attendance_logs al "
        "LEFT JOIN employees e ON e.employee_code = al.employee_code "
        "WHERE 1 = 1"
    )
    params = []
    
    if employee_code:
        query += " AND al.employee_code = ?"
        params.append(employee_code)
    if log_type:
        query += " AND al.log_type = ?"
        params.append(_normalize_log_type(log_type))
        
    query += " ORDER BY al.log_time DESC, al.id DESC"
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


VALID_ATTENDANCE_STATUSES = {"Có mặt", "Đi muộn", "Vắng mặt"}
VALID_ATTENDANCE_METHODS = {"face", "manual"}
VALID_ATTENDANCE_TYPES = {"IN", "OUT"}


def record_student_attendance(
        student_code,
        class_id,
        attendance_date,
        session_name,
        status,
        method="manual",
        confidence=None,
        attendance_type="IN",
):
        initialize_attendance_logs()
        student_code = (student_code or "").strip().upper()
        session_name = (session_name or "").strip()
        attendance_type = str(attendance_type).strip().upper()
        if not student_code or not session_name:
            raise ValueError("Mã học sinh và buổi học không được để trống.")
        if attendance_type not in VALID_ATTENDANCE_TYPES:
            raise ValueError("Loại lượt điểm danh không hợp lệ.")
        if status not in VALID_ATTENDANCE_STATUSES:
            raise ValueError("Trạng thái điểm danh không hợp lệ.")
        if attendance_type == "OUT" and status == "Vắng mặt":
            raise ValueError("Không thể ghi nhận lượt ra với trạng thái vắng mặt.")
        if method not in VALID_ATTENDANCE_METHODS:
            raise ValueError("Phương thức điểm danh không hợp lệ.")
        if not attendance_date:
            raise ValueError("Vui lòng chọn ngày điểm danh.")
        date_value = attendance_date.isoformat() if hasattr(attendance_date, "isoformat") else str(attendance_date)
        try:
            date_value = date.fromisoformat(date_value).isoformat()
        except ValueError as error:
            raise ValueError("Ngày điểm danh không hợp lệ.") from error
        normalized_confidence = None if confidence is None else float(confidence)
        if normalized_confidence is not None and not 0 <= normalized_confidence <= 1:
            raise ValueError("Giá trị nhận diện không hợp lệ.")

        with SessionLocal() as db:
            student = db.scalars(
                select(Student).where(
                    Student.student_code == student_code,
                    Student.status == "Đang học",
                )
            ).first()
            if student is None:
                raise ValueError("Không tìm thấy học sinh đang học với mã đã chọn.")
            if student.class_id != class_id:
                raise ValueError("Học sinh không thuộc lớp đã chọn.")
            legacy_employee = db.scalars(
                select(Employee).where(Employee.employee_code == student_code)
            ).first()
            if legacy_employee is None:
                raise ValueError("Không tìm thấy hồ sơ tương thích của học sinh.")

            existing_check_in = db.scalars(
                select(AttendanceLog).where(
                    AttendanceLog.student_code == student_code,
                    AttendanceLog.attendance_date == date_value,
                    AttendanceLog.session_name == session_name,
                    AttendanceLog.log_type == "IN",
                )
            ).first()
            existing_same_type = db.scalars(
                select(AttendanceLog.id).where(
                    AttendanceLog.student_code == student_code,
                    AttendanceLog.attendance_date == date_value,
                    AttendanceLog.session_name == session_name,
                    AttendanceLog.log_type == attendance_type,
                    AttendanceLog.attendance_method.in_(("face", "manual")),
                )
            ).first()
            if attendance_type == "OUT" and existing_check_in is None:
                raise ValueError(
                    "Học sinh chưa có lượt điểm danh vào trong buổi học này."
                )
            if attendance_type == "OUT" and existing_check_in is not None:
                previous_status = existing_check_in.attendance_status
                if previous_status in VALID_ATTENDANCE_STATUSES:
                    status = previous_status
                if status == "Vắng mặt":
                    raise ValueError(
                        "Học sinh đã được xác nhận vắng mặt, không thể ghi nhận lượt ra."
                    )
            if existing_same_type is not None:
                label = "vào" if attendance_type == "IN" else "ra"
                raise ValueError(
                    f"Học sinh này đã có lượt điểm danh {label} trong buổi học."
                )

            log = AttendanceLog(
                employee_code=student_code,
                student_code=student_code,
                class_id=class_id,
                attendance_date=date_value,
                session_name=session_name,
                attendance_status=status,
                attendance_method=method,
                confirmed=True,
                log_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                log_type=attendance_type,
                camera_source="Nhận diện khuôn mặt" if method == "face" else "Giáo viên xác nhận",
                confidence=normalized_confidence,
            )
            db.add(log)
            try:
                db.commit()
                db.refresh(log)
            except IntegrityError as error:
                db.rollback()
                raise ValueError(
                    "Lượt điểm danh này đã được ghi nhận trong buổi học đã chọn."
                ) from error
            result = _row_to_dict(log)
        clear_attendance_cache()
        return result


def update_student_attendance(log_id, student_code, class_id, status):
        initialize_attendance_logs()
        student_code = (student_code or "").strip().upper()
        if status not in VALID_ATTENDANCE_STATUSES:
            raise ValueError("Trạng thái điểm danh không hợp lệ.")
        with SessionLocal() as db:
            log = db.get(AttendanceLog, log_id)
            if log is None or log.log_type not in {"IN", "ATTENDANCE"}:
                raise ValueError("Không tìm thấy lượt điểm danh có thể điều chỉnh.")
            student = db.scalars(
                select(Student).where(
                    Student.student_code == student_code,
                    Student.status == "Đang học",
                )
            ).first()
            if student is None or student.class_id != class_id:
                raise ValueError("Học sinh phải đang học trong lớp đã chọn.")
            legacy_employee = db.scalars(
                select(Employee).where(Employee.employee_code == student_code)
            ).first()
            if legacy_employee is None:
                raise ValueError("Không tìm thấy hồ sơ tương thích của học sinh.")
            log.employee_code = student_code
            log.student_code = student_code
            log.class_id = class_id
            log.attendance_status = status
            log.attendance_method = "manual"
            log.camera_source = "Giáo viên điều chỉnh"
            log.confidence = None
            try:
                db.commit()
            except IntegrityError as error:
                db.rollback()
                raise ValueError(
                    "Học sinh này đã có lượt điểm danh vào trong cùng buổi học."
                ) from error
            result = _row_to_dict(log)
        clear_attendance_cache()
        return result


@st.cache_data(show_spinner=False)
def get_student_attendance_dataframe(attendance_date=None, class_id=None):
        initialize_attendance_logs()
        query = """
            SELECT al.id,
                   COALESCE(s.student_code, al.employee_code) AS student_code,
                   COALESCE(s.full_name, e.name, 'Hồ sơ cũ') AS student_name,
                   c.name AS class_name,
                   al.attendance_date,
                   al.session_name,
                   COALESCE(al.attendance_status, 'Có mặt') AS attendance_status,
                   al.log_type AS attendance_type,
                   CASE al.attendance_method
                       WHEN 'face' THEN 'Nhận diện khuôn mặt'
                       WHEN 'manual' THEN 'Giáo viên xác nhận'
                       ELSE 'Dữ liệu chuyển đổi'
                   END AS attendance_method,
                   al.log_time,
                   al.confidence
            FROM attendance_logs al
            LEFT JOIN students s ON s.student_code = al.student_code
            LEFT JOIN employees e ON e.employee_code = al.employee_code
            LEFT JOIN classes c ON c.id = COALESCE(al.class_id, s.class_id)
            WHERE 1 = 1
        """
        params = []
        if attendance_date:
            query += (
                " AND (al.attendance_date = ? OR "
                "(al.attendance_date IS NULL AND substr(al.log_time, 1, 10) = ?))"
            )
            params.extend([str(attendance_date), str(attendance_date)])
        query += (
            " AND (al.attendance_method IN ('face', 'manual') "
            "OR al.log_type IN ('IN', 'OUT'))"
        )
        if class_id is not None:
            query += " AND COALESCE(al.class_id, s.class_id) = ?"
            params.append(class_id)
        query += " ORDER BY al.log_time DESC, al.id DESC"
        with engine.connect() as connection:
            return pd.read_sql(query, connection, params=tuple(params))


ATTENDANCE_SUMMARY_COLUMNS = [
    "student_code",
    "student_name",
    "class_name",
    "attendance_date",
    "session_name",
    "check_in_time",
    "check_out_time",
    "attendance_status",
    "attendance_state",
]


@st.cache_data(show_spinner=False)
def get_student_attendance_summary_dataframe(attendance_date=None, class_id=None):
    records = get_student_attendance_dataframe(attendance_date, class_id)
    if records.empty:
        return pd.DataFrame(columns=ATTENDANCE_SUMMARY_COLUMNS)

    records = records.copy()
    records["attendance_date"] = records["attendance_date"].where(
        records["attendance_date"].notna(),
        records["log_time"].astype(str).str[:10],
    )
    records["session_name"] = records["session_name"].fillna("Dữ liệu cũ")

    summaries = []
    group_columns = [
        "student_code",
        "student_name",
        "class_name",
        "attendance_date",
        "session_name",
    ]
    for group_values, group in records.groupby(
        group_columns,
        dropna=False,
        sort=False,
    ):
        check_ins = group[group["attendance_type"] == "IN"].sort_values(
            ["log_time", "id"]
        )
        check_outs = group[group["attendance_type"] == "OUT"].sort_values(
            ["log_time", "id"]
        )
        status_values = set(check_ins["attendance_status"].dropna())
        if "Vắng mặt" in status_values:
            status = "Vắng mặt"
        elif "Đi muộn" in status_values:
            status = "Đi muộn"
        elif check_ins.empty:
            status = "Chưa ghi nhận"
        else:
            status = "Có mặt"

        if status == "Vắng mặt":
            check_in_time = None
        else:
            check_in_time = (
                str(check_ins.iloc[0]["log_time"])[11:19]
                if not check_ins.empty else None
            )
        check_out_time = (
            str(check_outs.iloc[-1]["log_time"])[11:19]
            if not check_outs.empty else None
        )
        if status == "Vắng mặt":
            attendance_state = "Đã xác nhận vắng"
        elif check_in_time and check_out_time:
            attendance_state = "Đã điểm danh vào và ra"
        elif check_in_time:
            attendance_state = "Còn thiếu lượt ra"
        elif check_out_time:
            attendance_state = "Còn thiếu lượt vào"
        else:
            attendance_state = "Chưa ghi nhận"

        summaries.append(
            {
                **dict(zip(group_columns, group_values)),
                "check_in_time": check_in_time,
                "check_out_time": check_out_time,
                "attendance_status": status,
                "attendance_state": attendance_state,
            }
        )
    return pd.DataFrame(summaries, columns=ATTENDANCE_SUMMARY_COLUMNS)


def get_class_attendance_summary(attendance_date, class_id=None):
        dataframe = get_student_attendance_summary_dataframe(
            attendance_date,
            class_id,
        )
        if dataframe.empty:
            return {"Có mặt": 0, "Đi muộn": 0, "Vắng mặt": 0}
        counts = dataframe["attendance_status"].value_counts()
        return {status: int(counts.get(status, 0)) for status in VALID_ATTENDANCE_STATUSES}
