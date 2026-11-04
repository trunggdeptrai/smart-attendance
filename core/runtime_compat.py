from collections.abc import Callable


def runtime_compatibility_error(
    python_version: tuple[int, ...],
    numpy_arange: Callable[..., object],
) -> str | None:
    if python_version[:2] != (3, 11):
        return (
            f"Ứng dụng yêu cầu Python 3.11.x, nhưng hiện đang chạy "
            f"Python {python_version[0]}.{python_version[1]}. "
            "Hãy chạy setup_windows.bat, sau đó khởi động bằng run.bat."
        )

    try:
        numpy_arange(0)
    except ValueError as error:
        return (
            f"NumPy trong môi trường hiện tại không tương thích "
            f"({error}). Hãy chạy setup_windows.bat để cài đúng dependencies "
            "và dùng run.bat để khởi động."
        )

    return None
