import argparse
import importlib
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_IMPORTS = {
    "streamlit": "streamlit",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "pandas": "pandas",
    "sqlalchemy": "SQLAlchemy",
    "plotly": "plotly",
    "face_recognition": "face-recognition and dlib",
    "openpyxl": "openpyxl",
}
REQUIRED_TABLES = {
    "attendance_logs",
    "classes",
    "employees",
    "students",
    "teachers",
    "schema_migrations",
}


def _check_imports() -> list[str]:
    problems = []
    for module_name, package_name in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(module_name)
        except (ImportError, OSError) as error:
            problems.append(
                f"Thiếu hoặc không nạp được {package_name} ({module_name}): {error}. "
                "Hãy kích hoạt .venv, cài requirements.txt và chạy lại kiểm tra."
            )
        else:
            print(f"[OK] Thư viện: {package_name}")
    return problems


def _check_database(database_path: Path) -> list[str]:
    if not database_path.exists():
        print(
            "[INFO] Chưa có attendance.db. Ứng dụng sẽ khởi tạo database lần đầu; "
            "có thể chạy check_environment.py --init-db để khởi tạo trước."
        )
        return []

    try:
        uri = f"file:{database_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            missing_tables = REQUIRED_TABLES - table_names
            if missing_tables:
                print(
                    "[WARN] Database cần khởi tạo/cập nhật schema: "
                    + ", ".join(sorted(missing_tables))
                    + ". Hãy chạy check_environment.py --init-db."
                )
                return []
            versions = {
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                )
            }
            if 3 not in versions:
                print(
                    "[WARN] Database cần áp dụng migration hiện có. "
                    "Hãy sao lưu attendance.db rồi chạy check_environment.py --init-db."
                )
                return []
    except sqlite3.DatabaseError as error:
        return [
            f"Không đọc được {database_path.name}: {error}. "
            "Dừng ứng dụng và kiểm tra/khôi phục một bản sao lưu; "
            "không xóa hoặc tạo đè database hiện tại."
        ]

    print(f"[OK] Database có schema ứng dụng tại {database_path}")
    return []


def _initialize_database() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from sqlalchemy.exc import SQLAlchemyError

    from db.session import init_db

    try:
        init_db()
    except (OSError, SQLAlchemyError) as error:
        raise RuntimeError(
            "Không thể khởi tạo database. Nếu đang dùng database cũ, hãy dừng ứng dụng "
            "và xác minh backup trước khi thử lại."
        ) from error
    print(
        "[OK] Đã chạy init_db() an toàn, có thể chạy lặp lại; "
        "các migration hiện có sẽ giữ dữ liệu và tạo backup khi cần."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kiểm tra môi trường chạy Smart Attendance."
    )
    parser.add_argument(
        "--create-dirs",
        action="store_true",
        help="Tạo data/faces và models bên trong thư mục dự án.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Khởi tạo/cập nhật database bằng migration hiện có.",
    )
    args = parser.parse_args()

    print(f"Smart Attendance: {PROJECT_ROOT}")
    problems = []
    if sys.version_info[:2] != (3, 11):
        problems.append(
            f"Python hiện tại là {sys.version_info.major}.{sys.version_info.minor}; "
            "dự án ghim hỗ trợ Python 3.11.x. Cài Python 3.11 và tạo lại .venv "
            "trong thư mục dự án."
        )
    else:
        print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}")

    for required_file in (
        PROJECT_ROOT / "app.py",
        PROJECT_ROOT / "requirements.txt",
    ):
        if not required_file.is_file():
            problems.append(f"Thiếu tệp dự án bắt buộc: {required_file.name}.")
        else:
            print(f"[OK] Tệp: {required_file.relative_to(PROJECT_ROOT)}")

    if args.create_dirs:
        from core.paths import ensure_runtime_directories

        ensure_runtime_directories()
    for required_directory in (
        PROJECT_ROOT / "data" / "faces",
        PROJECT_ROOT / "models",
    ):
        if required_directory.is_dir():
            print(f"[OK] Thư mục dữ liệu: {required_directory.relative_to(PROJECT_ROOT)}")
        else:
            print(
                f"[WARN] Thiếu thư mục {required_directory.relative_to(PROJECT_ROOT)}; "
                "chạy check_environment.py --create-dirs hoặc khởi động ứng dụng."
            )

    config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
    if config_path.is_file():
        print("[OK] Cấu hình .streamlit/config.toml")
    else:
        print(
            "[WARN] Thiếu .streamlit/config.toml. Streamlit dùng cấu hình mặc định; "
            "khôi phục tệp cấu hình dự án nếu cần giao diện/địa chỉ bind đã thiết lập."
        )

    problems.extend(_check_imports())
    try:
        import cv2

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if cascade_path.is_file():
            print("[OK] OpenCV Haar Cascade")
        else:
            problems.append(
                "Thiếu haarcascade_frontalface_default.xml trong gói OpenCV. "
                "Cài lại opencv-python trong .venv."
            )
    except (ImportError, OSError, AttributeError) as error:
        problems.append(f"Không kiểm tra được OpenCV Haar Cascade: {error}.")

    if args.init_db:
        if problems:
            print("[ERROR] Không khởi tạo database do lỗi môi trường ở trên.")
        else:
            try:
                _initialize_database()
            except RuntimeError as error:
                problems.append(str(error))
    else:
        problems.extend(_check_database(PROJECT_ROOT / "attendance.db"))

    model_files = (
        PROJECT_ROOT / "models" / "face_encodings.pkl",
        PROJECT_ROOT / "models" / "label_map.json",
    )
    if all(path.is_file() for path in model_files):
        print("[OK] Có dữ liệu mô hình nhận diện.")
    else:
        print(
            "[INFO] Chưa có mô hình nhận diện. Đây là trạng thái hợp lệ khi cài mới; "
            "thêm ảnh học sinh rồi huấn luyện tại trang Đăng ký khuôn mặt."
        )

    if problems:
        for problem in problems:
            print(f"[ERROR] {problem}")
        return 1

    print("[OK] Kiểm tra môi trường hoàn tất.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
