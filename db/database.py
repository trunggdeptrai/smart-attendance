from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import AttendanceLog, Employee, SchoolClass, Student, Teacher
from db.session import SessionLocal, engine, init_db

STUDENT_CODE_PREFIX = "HS"
STUDENT_CODE_WIDTH = 3


def format_student_code(number):
    return f"{STUDENT_CODE_PREFIX}{number:0{STUDENT_CODE_WIDTH}d}"


def _next_student_code(db: Session):
    used = set()
    for code in db.scalars(select(Student.student_code)):
        if code and code.startswith(STUDENT_CODE_PREFIX):
            number = code[len(STUDENT_CODE_PREFIX):]
            if number.isdigit():
                used.add(int(number))
    number = 1
    while number in used:
        number += 1
    return format_student_code(number)


def _next_class_code(db: Session):
    existing = set(db.scalars(select(SchoolClass.class_code)))
    number = 1
    while f"L{number:03d}" in existing:
        number += 1
    return f"L{number:03d}"


def initialize_database():
    init_db()
    with SessionLocal() as db:
        students = db.execute(
            select(Student.id, Student.student_code).order_by(Student.id)
        ).fetchall()
    from core.save_face import sync_employee_face_folders

    sync_employee_face_folders(students)


def create_class(name, class_code=None, homeroom_teacher_id=None):
    initialize_database()
    normalized_name = (name or "").strip()
    if not normalized_name:
        raise ValueError("Vui lòng nhập tên lớp.")
    with SessionLocal() as db:
        if class_code:
            normalized_code = class_code.strip().upper()
        else:
            normalized_code = _next_class_code(db)
        school_class = SchoolClass(
            class_code=normalized_code,
            name=normalized_name,
            homeroom_teacher_id=homeroom_teacher_id,
            active=True,
        )
        db.add(school_class)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("Mã lớp đã tồn tại.") from error
        db.refresh(school_class)
        result = school_class.id
    clear_school_caches()
    return result


def update_class(class_id, name, class_code, homeroom_teacher_id=None, active=True):
    initialize_database()
    if not (name or "").strip() or not (class_code or "").strip():
        raise ValueError("Mã lớp và tên lớp không được để trống.")
    with SessionLocal() as db:
        school_class = db.get(SchoolClass, class_id)
        if school_class is None:
            raise ValueError("Không tìm thấy lớp học.")
        school_class.name = name.strip()
        school_class.class_code = class_code.strip().upper()
        school_class.homeroom_teacher_id = homeroom_teacher_id
        school_class.active = bool(active)
        student_codes = db.scalars(
            select(Student.student_code).where(Student.class_id == class_id)
        ).all()
        if student_codes:
            legacy_students = db.scalars(
                select(Employee).where(Employee.employee_code.in_(student_codes))
            ).all()
            for legacy_student in legacy_students:
                legacy_student.department = school_class.name
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("Mã lớp đã được sử dụng.") from error
    clear_school_caches()


@st.cache_data(show_spinner=False)
def get_classes(active_only=True):
    initialize_database()
    with SessionLocal() as db:
        stmt = select(
            SchoolClass.id,
            SchoolClass.class_code,
            SchoolClass.name,
            SchoolClass.homeroom_teacher_id,
            SchoolClass.active,
        )
        if active_only:
            stmt = stmt.where(SchoolClass.active.is_(True))
        return db.execute(stmt.order_by(SchoolClass.name)).fetchall()


def create_student(name, class_id, date_of_birth=None, student_code=None):
    initialize_database()
    errors = validate_student_fields(name, class_id)
    if errors:
        raise ValueError(" ".join(errors))
    parsed_birth_date = _parse_date(date_of_birth)
    with SessionLocal() as db:
        school_class = db.get(SchoolClass, class_id)
        if school_class is None or not school_class.active:
            raise ValueError("Lớp học không tồn tại hoặc đã ngừng hoạt động.")
        code = (student_code or _next_student_code(db)).strip().upper()
        student = Student(
            student_code=code,
            full_name=name.strip(),
            date_of_birth=parsed_birth_date,
            class_id=class_id,
            status="Đang học",
        )
        db.add(student)
        try:
            db.flush()
            # Keep the original employee row so historical foreign keys and older
            # face-recognition files continue to resolve during the transition.
            legacy = db.scalars(
                select(Employee).where(Employee.employee_code == code)
            ).first()
            if legacy is None:
                db.add(Employee(employee_code=code, name=name.strip(), department=school_class.name))
            else:
                legacy.name = name.strip()
                legacy.department = school_class.name
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError(f"Mã học sinh {code} đã tồn tại.") from error
    from core.save_face import ensure_employee_folder

    ensure_employee_folder(code)
    clear_school_caches()
    return code


def update_student(student_id, name, class_id, status="Đang học", date_of_birth=None):
    initialize_database()
    errors = validate_student_fields(name, class_id)
    if errors:
        raise ValueError(" ".join(errors))
    if status not in {"Đang học", "Tạm nghỉ", "Đã chuyển trường", "Đã xóa"}:
        raise ValueError("Trạng thái học sinh không hợp lệ.")
    with SessionLocal() as db:
        student = db.get(Student, student_id)
        if student is None:
            raise ValueError("Không tìm thấy học sinh.")
        school_class = db.get(SchoolClass, class_id)
        if school_class is None:
            raise ValueError("Không tìm thấy lớp học.")
        student.full_name = name.strip()
        student.class_id = class_id
        student.status = status
        student.date_of_birth = _parse_date(date_of_birth)
        legacy = db.scalars(
            select(Employee).where(Employee.employee_code == student.student_code)
        ).first()
        if legacy:
            legacy.name = student.full_name
            legacy.department = school_class.name
        db.commit()
    clear_school_caches()


def deactivate_student(student_id):
    initialize_database()
    with SessionLocal() as db:
        student = db.get(Student, student_id)
        if student is None:
            raise ValueError("Không tìm thấy học sinh.")
        student.status = "Đã chuyển trường"
        db.commit()
        code = student.student_code
    clear_school_caches()
    return code


def delete_student_profile(student_id):
    """Soft-delete a student while preserving attendance and face data."""
    initialize_database()
    with SessionLocal() as db:
        student = db.get(Student, student_id)
        if student is None:
            raise ValueError("Không tìm thấy hồ sơ học sinh.")
        if student.status == "Đã xóa":
            raise ValueError("Hồ sơ học sinh đã được xóa trước đó.")

        attendance_count = db.scalar(
            select(func.count(AttendanceLog.id)).where(
                (AttendanceLog.student_code == student.student_code)
                | (AttendanceLog.employee_code == student.student_code)
            )
        ) or 0
        student.status = "Đã xóa"
        db.commit()
        result = {
            "student_code": student.student_code,
            "attendance_count": attendance_count,
        }
    clear_school_caches()
    return result


def validate_student_fields(name, class_id):
    errors = []
    if not name or not name.strip():
        errors.append("Họ và tên học sinh không được để trống.")
    if class_id is None:
        errors.append("Vui lòng chọn lớp học.")
    return errors


def _parse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("Ngày sinh không hợp lệ.") from error


@st.cache_data(show_spinner=False)
def get_students(active_only=True):
    initialize_database()
    with SessionLocal() as db:
        stmt = select(
            Student.id,
            Student.student_code,
            Student.full_name,
            SchoolClass.id.label("class_id"),
            SchoolClass.class_code,
            SchoolClass.name.label("class_name"),
            Student.date_of_birth,
            Student.status,
        ).join(SchoolClass, Student.class_id == SchoolClass.id)
        if active_only:
            stmt = stmt.where(Student.status == "Đang học")
        return db.execute(stmt.order_by(Student.student_code)).fetchall()


@st.cache_data(show_spinner=False)
def get_student_dataframe(active_only=True):
    students = get_students(active_only=active_only)
    return pd.DataFrame(
        [
            {
                "Mã học sinh": row.student_code,
                "Họ và tên": row.full_name,
                "Lớp": row.class_name,
                "Ngày sinh": row.date_of_birth,
                "Trạng thái": row.status,
            }
            for row in students
        ],
        columns=["Mã học sinh", "Họ và tên", "Lớp", "Ngày sinh", "Trạng thái"],
    )


def get_employee_codes():
    initialize_database()
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Student.student_code)
                .where(Student.status == "Đang học")
                .order_by(Student.student_code)
            ).all()
        )


@st.cache_data(show_spinner=False)
def get_all_employees():
    """Compatibility adapter for original pages and recognition utilities."""
    initialize_database()
    with SessionLocal() as db:
        stmt = (
            select(
                Student.id,
                Student.student_code.label("employee_code"),
                Student.full_name.label("name"),
                SchoolClass.name.label("department"),
            )
            .join(SchoolClass, Student.class_id == SchoolClass.id)
            .where(Student.status == "Đang học")
            .order_by(Student.id)
        )
        return db.execute(stmt).fetchall()


@st.cache_data(show_spinner=False)
def get_employee_dataframe():
    with engine.connect() as connection:
        return pd.read_sql(
            """
            SELECT s.student_code AS code, s.full_name AS name,
                   c.name AS department, s.id
            FROM students s JOIN classes c ON c.id = s.class_id
            WHERE s.status = 'Đang học'
            ORDER BY s.student_code
            """,
            connection,
        )


def clear_school_caches():
    get_classes.clear()
    get_students.clear()
    get_student_dataframe.clear()
    get_all_employees.clear()
    get_employee_dataframe.clear()


def clear_employee_cache():
    clear_school_caches()


@st.cache_data(show_spinner=False)
def get_teachers(active_only=True):
    initialize_database()
    with SessionLocal() as db:
        stmt = select(
            Teacher.id,
            Teacher.teacher_code,
            Teacher.full_name,
            Teacher.username,
            Teacher.active,
        )
        if active_only:
            stmt = stmt.where(Teacher.active.is_(True))
        return db.execute(stmt.order_by(Teacher.full_name)).fetchall()


def create_teacher(teacher_code, full_name, username=None):
    initialize_database()
    code = (teacher_code or "").strip().upper()
    name = (full_name or "").strip()
    login = (username or "").strip() or None
    if not code or not name:
        raise ValueError("Mã giáo viên và họ tên không được để trống.")
    with SessionLocal() as db:
        db.add(Teacher(teacher_code=code, full_name=name, username=login, active=True))
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("Mã giáo viên hoặc tài khoản đã tồn tại.") from error
    get_teachers.clear()
    get_classes.clear()


def update_teacher(teacher_id, teacher_code, full_name, username=None, active=True):
    initialize_database()
    code = (teacher_code or "").strip().upper()
    name = (full_name or "").strip()
    if not code or not name:
        raise ValueError("Mã giáo viên và họ tên không được để trống.")
    with SessionLocal() as db:
        teacher = db.get(Teacher, teacher_id)
        if teacher is None:
            raise ValueError("Không tìm thấy giáo viên.")
        teacher.teacher_code = code
        teacher.full_name = name
        teacher.username = (username or "").strip() or None
        teacher.active = bool(active)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("Mã giáo viên hoặc tài khoản đã được sử dụng.") from error
    get_teachers.clear()
    get_classes.clear()


def delete_teacher_profile(teacher_id):
    """Deactivate a teacher without breaking class assignment references."""
    initialize_database()
    with SessionLocal() as db:
        teacher = db.get(Teacher, teacher_id)
        if teacher is None:
            raise ValueError("Không tìm thấy hồ sơ giáo viên.")
        if not teacher.active:
            raise ValueError("Hồ sơ giáo viên đã ngừng hoạt động.")
        assigned_class_count = db.scalar(
            select(func.count(SchoolClass.id)).where(
                SchoolClass.homeroom_teacher_id == teacher_id
            )
        ) or 0
        teacher.active = False
        db.commit()
        result = {
            "teacher_code": teacher.teacher_code,
            "assigned_class_count": assigned_class_count,
        }
    get_teachers.clear()
    get_classes.clear()
    return result


# Backwards-compatible function names used by existing tests and integrations.
def create_employee(name, department):
    initialize_database()
    with SessionLocal() as db:
        school_class = db.scalars(
            select(SchoolClass).where(SchoolClass.name == department.strip())
        ).first()
        class_id = school_class.id if school_class else None
    if class_id is None:
        class_id = create_class(department)
    return create_student(name, class_id)


def validate_employee_fields(name, department):
    errors = []
    if not name or not name.strip():
        errors.append("Họ và tên học sinh không được để trống.")
    if not department or not department.strip():
        errors.append("Lớp học không được để trống.")
    return errors


def update_employee(employee_id, name, department):
    initialize_database()
    with SessionLocal() as db:
        school_class = db.scalars(
            select(SchoolClass).where(SchoolClass.name == department.strip())
        ).first()
        class_id = school_class.id if school_class else None
    if class_id is None:
        class_id = create_class(department)
    update_student(employee_id, name, class_id)


def delete_employee(employee_id):
    return deactivate_student(employee_id)
