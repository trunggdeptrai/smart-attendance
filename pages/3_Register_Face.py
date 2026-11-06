from pathlib import Path

import cv2
import numpy as np
import streamlit as st

from core.camera_stream import (
    release_camera,
    release_inactive_cameras,
    smooth_face_boxes,
)
from core.live_camera import decode_camera_image, live_camera
from core.face_detect import detect_faces
from core.face_recognizer import train_model
from core.save_face import crop_and_resize_face, save_face_image
from streamlit.runtime.media_file_storage import MediaFileStorageError
from core.paths import FACES_DIR
from db.database import get_students

release_inactive_cameras(st.session_state, "register_face")
if st.session_state.get("register_face_camera_error"):
    st.session_state["register_face_stream_active"] = True

st.title("Đăng ký khuôn mặt học sinh")
st.caption(
    "Trang này chụp và lưu ảnh mẫu khuôn mặt. Nhận diện và điểm danh thực hiện ở trang "
    "“Điểm danh nhận diện khuôn mặt”. Ảnh mẫu được lưu cục bộ trong thư mục riêng của dự án."
)

students = get_students()
if not students:
    st.warning("Chưa có học sinh đang học. Hãy thêm học sinh trước.")
    st.stop()

student_map = {row.student_code: row for row in students}
student_code = st.selectbox(
    "Học sinh",
    list(student_map),
    format_func=lambda value: (
        f"{value} · {student_map[value].full_name} ({student_map[value].class_name})"
    ),
)
if student_code is None:
    st.error("Hãy chọn học sinh cần đăng ký khuôn mặt.")
    st.stop()
face_dir = FACES_DIR / student_code


def _count_saved_faces(directory):
    if not directory.exists():
        return 0
    return sum(
        1
        for path in directory.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

capture_tab, upload_tab = st.tabs(["Chụp bằng camera", "Tải ảnh lên"])
with capture_tab:
    camera_col, start_col, stop_col = st.columns([1.2, 1, 1])
    with camera_col:
        camera_index = st.selectbox(
            "Chọn camera",
            [0, 1],
            format_func=lambda index: f"Camera {index + 1}",
            key="register_face_camera_index",
        )
    with start_col:
        start_camera = st.button(
            "Bật camera trực tiếp",
            type="primary",
            disabled=st.session_state.get("register_face_is_running", False),
        )
    with stop_col:
        stop_camera = st.button(
            "Tắt camera",
            disabled=not st.session_state.get("register_face_is_running", False),
        )

    previous_camera_index = st.session_state.get(
        "register_face_active_camera_index"
    )
    if previous_camera_index != camera_index:
        st.session_state["register_face_active_camera_index"] = camera_index
        release_camera(st.session_state, "register_face")
        st.session_state["register_face_faces"] = []
        st.session_state["register_face_smoothed_faces"] = []
        st.session_state["register_face_read_failures"] = 0
        st.session_state["register_face_last_component_frame_id"] = 0

    if start_camera:
        st.session_state["register_face_is_running"] = True
        st.session_state["register_face_stream_active"] = True
        st.session_state.pop("register_face_camera_error", None)
        st.session_state["register_face_faces"] = []
        st.session_state["register_face_smoothed_faces"] = []
        st.session_state["register_face_read_failures"] = 0
        st.session_state["register_face_last_component_frame_id"] = 0
        st.session_state.pop("register_face_feedback", None)
    if stop_camera:
        st.session_state["register_face_is_running"] = False
        st.session_state["register_face_stream_active"] = False
        st.session_state["register_face_read_failures"] = 0
        st.session_state["register_face_faces"] = []
        st.session_state["register_face_smoothed_faces"] = []
        release_camera(st.session_state, "register_face")

    def _retry_registration_camera():
        st.session_state["register_face_is_running"] = True
        st.session_state["register_face_stream_active"] = True
        st.session_state.pop("register_face_camera_error", None)
        st.session_state["register_face_faces"] = []
        st.session_state["register_face_smoothed_faces"] = []
        st.session_state["register_face_read_failures"] = 0
        st.session_state["register_face_last_component_frame_id"] = 0
        st.session_state["register_face_restart_key"] = (
            st.session_state.get("register_face_restart_key", 0) + 1
        )
        release_camera(st.session_state, "register_face")

    @st.fragment
    def render_registration_camera():
        if not st.session_state.get("register_face_is_running", False):
            live_camera(
                active=False,
                camera_index=camera_index,
                overlays=[],
                restart_key=st.session_state.get(
                    "register_face_restart_key",
                    0,
                ),
                key="register_face_live_camera",
            )
            st.info("Bật camera để xem khung theo dõi khuôn mặt.")
            if st.session_state.get("register_face_camera_error"):
                st.error(st.session_state["register_face_camera_error"])
                st.button(
                    "Thử mở lại camera",
                    key="retry_register_face_camera",
                    type="primary",
                    on_click=_retry_registration_camera,
                )
            st.metric("Ảnh mẫu đã lưu", _count_saved_faces(face_dir))
            return

        faces = st.session_state.get("register_face_faces", [])
        overlays = [
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "color": "#00d084" if len(faces) == 1 else "#ffae42",
            }
            for x, y, width, height in faces
        ]
        result = live_camera(
            active=True,
            camera_index=camera_index,
            overlays=overlays,
            restart_key=st.session_state.get(
                "register_face_restart_key",
                0,
            ),
            capture_request_id=st.session_state.get(
                "register_face_capture_request_id",
                0,
            ),
            capture_ack_id=st.session_state.get(
                "register_face_capture_ack_id",
                0,
            ),
            face_hint="Đã thấy 1 khuôn mặt – bấm “Chụp và đăng ký” bên dưới để lưu ảnh mẫu.",
            key="register_face_live_camera",
        )

        capture_to_save = None
        if result and result.get("kind") == "status":
            status = result.get("status", "")
            if status and not status.startswith("Camera đang hoạt động"):
                st.session_state["register_face_camera_error"] = status
        elif result and result.get("kind") == "capture":
            request_id = int(result.get("capture_request_id", 0))
            if request_id > st.session_state.get(
                "register_face_capture_ack_id",
                0,
            ):
                capture_to_save = (request_id, result.get("image"))
        elif result and result.get("kind") == "frame":
            frame_id = int(result.get("frame_id", 0))
            if frame_id > st.session_state.get(
                "register_face_last_component_frame_id",
                0,
            ):
                st.session_state["register_face_last_component_frame_id"] = (
                    frame_id
                )
                try:
                    frame = decode_camera_image(result.get("image"))
                    detected_faces, _ = detect_faces(
                        frame,
                        processing_width=480,
                        return_gray=False,
                    )
                except (ValueError, cv2.error) as error:
                    st.error(f"Không thể phát hiện khuôn mặt: {error}")
                    detected_faces = []
                faces = smooth_face_boxes(
                    st.session_state.get(
                        "register_face_smoothed_faces",
                        [],
                    ),
                    detected_faces,
                )
                st.session_state["register_face_faces"] = faces
                st.session_state["register_face_smoothed_faces"] = faces
                st.session_state.pop("register_face_camera_error", None)

        if capture_to_save is not None:
            request_id, image_data = capture_to_save
            try:
                photo = decode_camera_image(image_data)
                capture_faces, _ = detect_faces(
                    photo,
                    processing_width=640,
                    return_gray=False,
                )
                if len(capture_faces) != 1:
                    st.session_state["register_face_feedback"] = {
                        "level": "warning",
                        "text": (
                            "Ảnh vừa chụp cần có đúng một khuôn mặt; "
                            f"hiện phát hiện {len(capture_faces)}."
                        ),
                    }
                else:
                    save_face_image(
                        student_code,
                        crop_and_resize_face(photo, capture_faces[0]),
                    )
                    st.session_state["register_face_feedback"] = {
                        "level": "success",
                        "text": (
                            f"Đã lưu ảnh mẫu cho {student_code} · "
                            f"{student_map[student_code].full_name}."
                        ),
                    }
            except (OSError, ValueError, cv2.error) as error:
                st.session_state["register_face_feedback"] = {
                    "level": "error",
                    "text": f"Không thể lưu ảnh mẫu: {error}",
                }
            st.session_state["register_face_capture_ack_id"] = request_id
            st.rerun(scope="fragment")

        feedback = st.session_state.get("register_face_feedback")
        if feedback:
            getattr(st, feedback["level"])(feedback["text"])

        if st.session_state.get("register_face_camera_error"):
            st.error(st.session_state["register_face_camera_error"])
            st.button(
                "Thử mở lại camera",
                key="retry_register_face_camera",
                type="primary",
                on_click=_retry_registration_camera,
            )
        elif not result:
            st.info("Đang chờ camera khởi động...")
        elif result.get("kind") == "frame":
            if not faces:
                st.warning(
                    "Chưa phát hiện khuôn mặt. Hãy đưa một khuôn mặt vào giữa "
                    "khung hình và đảm bảo đủ ánh sáng."
                )
            elif len(faces) > 1:
                st.warning(
                    "Phát hiện nhiều khuôn mặt. Chỉ để một học sinh trước camera; "
                    "chưa thể đăng ký ảnh này."
                )
            else:
                st.success(
                    f"Đã phát hiện một khuôn mặt. Ảnh sẽ được lưu cho "
                    f"{student_code} · {student_map[student_code].full_name}."
                )

        if len(faces) == 1:
            if st.button(
                f"Chụp và đăng ký cho {student_code}",
                type="primary",
                key="capture_register_face",
            ):
                st.session_state["register_face_capture_request_id"] = (
                    st.session_state.get(
                        "register_face_capture_request_id",
                        0,
                    ) + 1
                )
                st.rerun(scope="fragment")

        st.metric("Ảnh mẫu đã lưu", _count_saved_faces(face_dir))

    render_registration_camera()

with upload_tab:
    photos = st.file_uploader(
        "Chọn một hoặc nhiều ảnh JPG/PNG",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )
    if st.button("Kiểm tra và lưu ảnh đã chọn", disabled=not photos):
        saved = 0
        skipped = []
        for photo in photos:
            try:
                photo_bytes = photo.getvalue()
            except MediaFileStorageError:
                skipped.append(
                    f"{photo.name}: ảnh không còn khả dụng trong phiên; "
                    "hãy tải ảnh lên lại"
                )
                continue
            image = cv2.imdecode(np.frombuffer(photo_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                skipped.append(f"{photo.name}: không đọc được ảnh")
                continue
            faces, _ = detect_faces(image)
            if len(faces) != 1:
                skipped.append(
                    f"{photo.name}: phát hiện {len(faces)} khuôn mặt, cần đúng một"
                )
                continue
            try:
                save_face_image(
                    student_code,
                    crop_and_resize_face(image, faces[0]),
                )
                saved += 1
            except (OSError, ValueError, cv2.error) as error:
                skipped.append(f"{photo.name}: không thể lưu ảnh ({error})")
        if saved:
            st.success(f"Đã lưu {saved} ảnh mẫu cho {student_code}.")
            saved_count_placeholder.metric(
                "Ảnh mẫu đã lưu",
                _count_saved_faces(face_dir),
            )
        if skipped:
            st.warning("Một số ảnh chưa được lưu:\n\n" + "\n".join(skipped))

st.divider()
st.subheader("Cập nhật mô hình nhận diện")
st.caption("Huấn luyện lại sau khi bổ sung ảnh khuôn mặt để dùng dữ liệu mới.")
if st.button("Huấn luyện mô hình", type="primary"):
    try:
        result = train_model()
        st.success(
            f"Mô hình đã cập nhật: {result['num_images']} ảnh, "
            f"{result['num_people']} học sinh."
        )
    except (FileNotFoundError, ValueError, OSError) as error:
        st.error(f"Không thể huấn luyện mô hình: {error}")

st.divider()
st.subheader("Xóa dữ liệu khuôn mặt của học sinh")
st.caption(
    "Dùng khi học sinh/phụ huynh rút lại sự đồng ý hoặc dữ liệu không còn cần thiết. "
    "Thao tác xóa vĩnh viễn ảnh mẫu của học sinh đang chọn; hồ sơ và lịch sử điểm danh được giữ nguyên. "
    "Sau khi xóa cần huấn luyện lại mô hình để loại bỏ vector đặc trưng khỏi mô hình."
)
confirm_delete = st.checkbox(
    f"Tôi xác nhận xóa toàn bộ ảnh mẫu của {student_code}",
    key=f"confirm_delete_faces_{student_code}",
)
if st.button("Xóa ảnh mẫu và huấn luyện lại", disabled=not confirm_delete):
    from core.save_face import delete_employee_folder

    try:
        removed = _count_saved_faces(face_dir)
        delete_employee_folder(student_code)
        st.success(f"Đã xóa {removed} ảnh mẫu của {student_code}.")
        try:
            result = train_model()
            st.info(
                f"Đã huấn luyện lại: {result['num_images']} ảnh, {result['num_people']} học sinh."
            )
        except ValueError:
            from core.face_recognizer import remove_model_files

            remove_model_files()
            st.info("Không còn ảnh mẫu hợp lệ; đã xóa tệp mô hình cũ.")
        except (FileNotFoundError, OSError) as error:
            st.warning(f"Đã xóa ảnh nhưng chưa huấn luyện lại được ({error}).")
    except OSError as error:
        st.error(f"Không thể xóa ảnh mẫu: {error}")
