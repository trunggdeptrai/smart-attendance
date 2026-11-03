from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Employee(Base):
    """Compatibility table retained for existing attendance records and face IDs."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_code = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)


class SchoolClass(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    homeroom_teacher_id = Column(Integer, ForeignKey("teachers.id"))
    active = Column(Boolean, nullable=False, default=True)


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_code = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True)
    active = Column(Boolean, nullable=False, default=True)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_code = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String, nullable=False)
    date_of_birth = Column(Date)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    status = Column(String, nullable=False, default="Đang học")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # employee_code is retained for compatibility with the original database.
    employee_code = Column(String, ForeignKey("employees.employee_code"), nullable=False)
    log_time = Column(String, nullable=False)
    log_type = Column(String, nullable=False)
    camera_source = Column(String)
    confidence = Column(Float)
    student_code = Column(String, ForeignKey("students.student_code"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    attendance_date = Column(String)
    session_name = Column(String)
    attendance_status = Column(String)
    attendance_method = Column(String, nullable=False, default="legacy")
    confirmed = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_attendance_logs_employee_time", "employee_code", "log_time"),
        Index("idx_attendance_logs_time", "log_time"),
        Index("idx_attendance_logs_class_date", "class_id", "attendance_date"),
        Index("idx_attendance_logs_student_date", "student_code", "attendance_date"),
        Index(
            "idx_student_attendance_session",
            "student_code",
            "attendance_date",
            "session_name",
            "log_type",
            unique=True,
            sqlite_where=(
                (student_code.is_not(None))
                & attendance_method.in_(("face", "manual"))
                & log_type.in_(("IN", "OUT"))
            ),
        ),
    )
