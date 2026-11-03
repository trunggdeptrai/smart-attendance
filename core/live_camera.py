from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "smart_attendance_live_camera",
    path=str(Path(__file__).resolve().parent.parent / "ui" / "live_camera"),
)


def live_camera(
    *,
    active: bool,
    camera_index: int,
    overlays: list[dict[str, Any]],
    restart_key: int,
    key: str,
    capture_request_id: int = 0,
    capture_ack_id: int = 0,
    default: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    return _COMPONENT(
        active=active,
        camera_index=camera_index,
        overlays=overlays,
        restart_key=restart_key,
        capture_request_id=capture_request_id,
        capture_ack_id=capture_ack_id,
        key=key,
        default=default,
    )


def decode_camera_image(image_data: str):
    import base64
    import binascii

    import cv2
    import numpy as np

    if not isinstance(image_data, str):
        raise ValueError("Dữ liệu ảnh camera không hợp lệ.")
    if image_data.startswith("data:"):
        _, separator, image_data = image_data.partition(",")
        if not separator:
            raise ValueError("Không đọc được ảnh camera.")
    try:
        image_bytes = base64.b64decode(image_data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Dữ liệu ảnh camera bị lỗi. Vui lòng thử lại.") from error

    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if image is None:
        raise ValueError("Không thể giải mã ảnh camera. Vui lòng thử lại.")
    return image
