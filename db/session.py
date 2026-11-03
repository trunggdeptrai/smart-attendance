import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.models import Base

DB_PATH = Path(__file__).resolve().parent.parent / "attendance.db"
# Use sqlite backend
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# create_engine specific to sqlite (check_same_thread=False for Streamlit multithreading)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migration_backup_needed():
    if not DB_PATH.exists():
        return False
    with engine.connect() as connection:
        has_marker = connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).first()
        has_data = connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employees'"
        ).first()
        if not has_data:
            return False
        if not has_marker:
            return True
        has_latest_version = connection.exec_driver_sql(
            "SELECT 1 FROM schema_migrations WHERE version=3"
        ).first()
        return has_latest_version is None


def _apply_school_migration(connection):
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    migrated = connection.exec_driver_sql(
        "SELECT 1 FROM schema_migrations WHERE version=1"
    ).first()
    if migrated:
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_attendance_logs_class_date "
            "ON attendance_logs (class_id, attendance_date)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_attendance_logs_student_date "
            "ON attendance_logs (student_code, attendance_date)"
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) "
                "VALUES (2, :applied_at)"
            ),
            {"applied_at": datetime.now().isoformat(timespec="seconds")},
        )
        return

    columns = {
        row[1] for row in connection.exec_driver_sql("PRAGMA table_info(attendance_logs)")
    }
    new_columns = {
        "student_code": "VARCHAR REFERENCES students(student_code)",
        "class_id": "INTEGER REFERENCES classes(id)",
        "attendance_date": "VARCHAR",
        "session_name": "VARCHAR",
        "attendance_status": "VARCHAR",
        "attendance_method": "VARCHAR NOT NULL DEFAULT 'legacy'",
        "confirmed": "BOOLEAN NOT NULL DEFAULT 1",
    }
    for column, definition in new_columns.items():
        if column not in columns:
            connection.exec_driver_sql(
                f"ALTER TABLE attendance_logs ADD COLUMN {column} {definition}"
            )

    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_attendance_logs_class_date "
        "ON attendance_logs (class_id, attendance_date)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_attendance_logs_student_date "
        "ON attendance_logs (student_code, attendance_date)"
    )

    legacy_classes = connection.exec_driver_sql(
        "SELECT DISTINCT trim(department) FROM employees "
        "WHERE department IS NOT NULL AND trim(department) != '' ORDER BY trim(department)"
    ).fetchall()
    for index, (class_name,) in enumerate(legacy_classes, start=1):
        class_code = f"LEGACY-{index:03d}"
        connection.execute(
            text(
                "INSERT OR IGNORE INTO classes (class_code, name, active) "
                "VALUES (:class_code, :name, 1)"
            ),
            {"class_code": class_code, "name": class_name.strip()},
        )

    has_unassigned = connection.exec_driver_sql(
        "SELECT 1 FROM employees "
        "WHERE department IS NULL OR trim(department) = '' LIMIT 1"
    ).first()
    if has_unassigned:
        connection.execute(
            text(
                "INSERT OR IGNORE INTO classes (class_code, name, active) "
                "VALUES ('LEGACY-UNASSIGNED', 'Chưa phân lớp', 1)"
            )
        )

    connection.exec_driver_sql(
        """
        INSERT OR IGNORE INTO students (student_code, full_name, class_id, status)
        SELECT e.employee_code, e.name, c.id, 'Đang học'
        FROM employees e
        JOIN classes c ON (
            (e.department IS NOT NULL AND trim(e.department) != ''
             AND c.class_code LIKE 'LEGACY-%' AND c.name = trim(e.department))
            OR
            ((e.department IS NULL OR trim(e.department) = '')
             AND c.class_code = 'LEGACY-UNASSIGNED')
        )
        WHERE e.employee_code IS NOT NULL
          AND trim(e.employee_code) != ''
        """
    )
    connection.exec_driver_sql(
        """
        UPDATE attendance_logs
        SET student_code = employee_code,
            attendance_date = substr(log_time, 1, 10),
            attendance_status = CASE
                WHEN log_type = 'IN' THEN 'Có mặt'
                ELSE attendance_status
            END
        WHERE student_code IS NULL
          AND EXISTS (
              SELECT 1 FROM students s
              WHERE s.student_code = attendance_logs.employee_code
          )
        """
    )
    connection.exec_driver_sql(
        """
        UPDATE attendance_logs
        SET class_id = (
            SELECT s.class_id FROM students s
            WHERE s.student_code = attendance_logs.student_code
        )
        WHERE student_code IS NOT NULL AND class_id IS NULL
        """
    )
    connection.exec_driver_sql(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_attendance_session
        ON attendance_logs (student_code, attendance_date, session_name)
        WHERE student_code IS NOT NULL
          AND attendance_method IN ('face', 'manual')
        """
    )
    connection.execute(
        text("INSERT INTO schema_migrations (version, applied_at) VALUES (1, :applied_at)"),
        {"applied_at": datetime.now().isoformat(timespec="seconds")},
    )
    connection.execute(
        text("INSERT INTO schema_migrations (version, applied_at) VALUES (2, :applied_at)"),
        {"applied_at": datetime.now().isoformat(timespec="seconds")},
    )


def _apply_attendance_event_migration(connection):
    migrated = connection.exec_driver_sql(
        "SELECT 1 FROM schema_migrations WHERE version=3"
    ).first()
    if migrated:
        return

    connection.exec_driver_sql(
        """
        UPDATE attendance_logs
        SET log_type = 'IN'
        WHERE log_type = 'ATTENDANCE'
          AND attendance_method IN ('face', 'manual')
        """
    )
    connection.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_student_attendance_session"
    )
    connection.exec_driver_sql(
        """
        CREATE UNIQUE INDEX idx_student_attendance_session
        ON attendance_logs (
            student_code,
            attendance_date,
            session_name,
            log_type
        )
        WHERE student_code IS NOT NULL
          AND attendance_method IN ('face', 'manual')
          AND log_type IN ('IN', 'OUT')
        """
    )
    connection.execute(
        text(
            "INSERT INTO schema_migrations (version, applied_at) "
            "VALUES (3, :applied_at)"
        ),
        {"applied_at": datetime.now().isoformat(timespec="seconds")},
    )


def init_db():
    if _migration_backup_needed():
        backup_dir = DB_PATH.parent / "database_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / (
            f"{DB_PATH.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{DB_PATH.suffix}"
        )
        shutil.copy2(DB_PATH, backup_path)

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        _apply_school_migration(connection)
        _apply_attendance_event_migration(connection)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
