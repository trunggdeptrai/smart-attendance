from datetime import date
import time

import cv2
import numpy as np
import streamlit as st

from core.dataframes import records_to_dataframe
from core.camera_stream import (
    clear_prediction_cache,
    get_or_update_prediction,
    release_camera,
    release_inactive_cameras,
)
from core.live_camera import decode_camera_image, live_camera
from core.face_detect import detect_faces
from core.face_recognizer import predict_face
from core.save_face import crop_and_resize_face
from streamlit.runtime.media_file_storage import MediaFileStorageError
from db.attendance_repo import (
    get_student_attendance_dataframe,
    record_student_attendance,
    update_student_attendance,
)
from db.database import get_classes, get_students

st.title("Điểm danh bằng nhận diện khuôn mặt")
st.caption("Giáo viên chọn lớp và buổi học, kiểm tra kết quả rồi xác nhận trước khi lưu.")
release_inactive_cameras(st.session_state, "attendance")

classes = get_classes()
if not classes:
    st.session_state["attendance_is_running"] = False
    st.session_state["attendance_stream_active"] = False
    release_camera(st.session_state, "attendance")
    st.warning("Chưa có lớp học đang hoạt động. Hãy tạo lớp trước khi điểm danh.")
    st.stop()

class_map = {row.id: row for row in classes}
selection_col, date_col, session_col = st.columns([1.3, 1, 1])
with selection_col:
    selected_class_id = st.selectbox(
        "Lớp học",
        list(class_map),
        format_func=lambda value: (
            f"{class_map[value].class_code} · {class_map[value].name}"
        ),
    )
with date_col:
    attendance_date = st.date_input(
        "Ngày điểm danh",
        value=date.today(),
        format="DD/MM/YYYY",
    )
with session_col:
    session_name = st.selectbox(
        "Buổi học",
        ["Buổi sáng", "Buổi chiều", "Buổi tối"],
    )
attendance_col, source_col = st.columns([1, 1.8])
with source_col:
    source = st.radio(
        "Nguồn ảnh",
        ["Camera trực tiếp", "Chụp ảnh bằng camera", "Tải ảnh từ thiết bị"],
        horizontal=True,
    )
with attendance_col:
    if source == "Camera trực tiếp":
        st.caption("Chọn lượt điểm danh bằng nút bên dưới camera.")
        attendance_type = "Điểm danh vào"
    else:
        attendance_type = st.radio(
            "Loại lượt điểm danh",
            ["Điểm danh vào", "Điểm danh ra"],
            horizontal=True,
        )
attendance_event = "IN" if attendance_type == "Điểm danh vào" else "OUT"
if source != "Camera trực tiếp" and st.session_state.get(
    "attendance_is_running",
    False,
):
    st.session_state["attendance_is_running"] = False
    st.session_state["attendance_stream_active"] = False
    release_camera(st.session_state, "attendance")
    clear_prediction_cache(st.session_state, "attendance")

students = [
    row for row in get_students()
    if row.class_id == selected_class_id
]
if not students:
    st.session_state["attendance_is_running"] = False
    st.session_state["attendance_stream_active"] = False
    release_camera(st.session_state, "attendance")
    st.info("Lớp này chưa có học sinh đang học.")
    st.stop()

student_by_code = {row.student_code: row for row in students}
student_by_id = {row.id: row for row in students}
context = (selected_class_id, attendance_date.isoformat(), session_name)
stored_context = st.session_state.get("attendance_candidate_context")
if stored_context != context:
    st.session_state.pop("attendance_candidates", None)
    st.session_state.pop("attendance_live_recorded_events", None)
    st.session_state["attendance_candidate_context"] = context


def load_daily_records():
    records = get_student_attendance_dataframe(
        attendance_date,
        selected_class_id,
    )
    if not records.empty:
        records = records[
            (records["session_name"].isna())
            | (records["session_name"] == session_name)
        ]
    return records


daily_records = load_daily_records()
live_recorded_events = st.session_state.setdefault(
    "attendance_live_recorded_events",
    set(),
)

st.caption(
    "Học sinh chưa được camera nhận diện không bị tự động đánh dấu vắng. "
    "Chỉ các kết quả được giáo viên xác nhận mới được ghi vào sổ điểm danh."
)

if st.session_state.get("attendance_image_source") != source:
    st.session_state.pop("attendance_image_bytes", None)
    st.session_state.pop("attendance_image_file_key", None)
    st.session_state["attendance_image_source"] = source

if (
    source == "Camera trực tiếp"
    and st.session_state.get("attendance_camera_error")
):
    st.session_state["attendance_stream_active"] = True

camera_running = False
if source == "Camera trực tiếp":
    st.session_state.pop("attendance_candidates", None)
    camera_col, start_col, stop_col = st.columns([1.2, 1, 1])
    with camera_col:
        selected_camera_index = st.selectbox(
            "Chọn camera",
            [0, 1],
            format_func=lambda index: f"Camera {index + 1}",
            key="attendance_camera_index",
        )
    with start_col:
        start_camera = st.button(
            "Bật camera trực tiếp",
            type="primary",
            disabled=st.session_state.get("attendance_is_running", False),
        )
    with stop_col:
        stop_camera = st.button(
            "Tắt camera",
            disabled=not st.session_state.get("attendance_is_running", False),
        )

    previous_camera_index = st.session_state.get(
        "attendance_active_camera_index"
    )
    if previous_camera_index != selected_camera_index:
        st.session_state["attendance_active_camera_index"] = selected_camera_index
        release_camera(st.session_state, "attendance")
        clear_prediction_cache(st.session_state, "attendance")
        st.session_state["attendance_faces"] = []
        st.session_state["attendance_read_failures"] = 0
        st.session_state["attendance_last_component_frame_id"] = 0

    if start_camera:
        st.session_state["attendance_is_running"] = True
        st.session_state["attendance_stream_active"] = True
        st.session_state.pop("attendance_camera_error", None)
        clear_prediction_cache(st.session_state, "attendance")
        st.session_state["attendance_faces"] = []
        st.session_state["attendance_read_failures"] = 0
        st.session_state["attendance_last_component_frame_id"] = 0
    if stop_camera:
        st.session_state["attendance_is_running"] = False
        st.session_state["attendance_stream_active"] = False
        st.session_state["attendance_faces"] = []
        release_camera(st.session_state, "attendance")
        clear_prediction_cache(st.session_state, "attendance")
        st.session_state["attendance_read_failures"] = 0

    camera_running = st.session_state.get("attendance_is_running", False)
    def _retry_attendance_camera():
        st.session_state["attendance_is_running"] = True
        st.session_state["attendance_stream_active"] = True
        st.session_state.pop("attendance_camera_error", None)
        st.session_state["attendance_faces"] = []
        st.session_state["attendance_read_failures"] = 0
        st.session_state["attendance_last_component_frame_id"] = 0
        st.session_state["attendance_restart_key"] = (
            st.session_state.get("attendance_restart_key", 0) + 1
        )
        clear_prediction_cache(st.session_state, "attendance")
        release_camera(st.session_state, "attendance")

    @st.fragment
    def render_attendance_camera():
        faces_list = st.session_state.get("attendance_faces", [])
        current_prediction = st.session_state.get("attendance_prediction")
        overlay = []
        if len(faces_list) == 1:
            face = faces_list[0]
            matched_code = (
                current_prediction.get("display_code")
                if current_prediction and current_prediction.get("is_match")
                else None
            )
            matched_row = student_by_code.get(matched_code)
            label = None
            color = "#f4b400"
            if matched_row is not None:
                label = (
                    f"{matched_row.student_code} · "
                    f"{matched_row.full_name} · {matched_row.class_name}"
                )
                color = "#00d084"
            elif matched_code:
                label = f"{matched_code} · Ngoài lớp đang chọn"
                color = "#ffae42"
            overlay.append({
                "x": face[0],
                "y": face[1],
                "width": face[2],
                "height": face[3],
                "label": label,
                "color": color,
            })
        elif len(faces_list) > 1:
            overlay = [
                {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "label": "Nhiều khuôn mặt",
                    "color": "#ffae42",
                }
                for x, y, width, height in faces_list
            ]

        is_running = st.session_state.get("attendance_is_running", False)
        result = live_camera(
            active=is_running,
            camera_index=selected_camera_index,
            overlays=overlay,
            restart_key=st.session_state.get("attendance_restart_key", 0),
            key="attendance_live_camera",
        )
        if not is_running:
            st.info("Camera đang tắt. Bấm “Bật camera trực tiếp” để bắt đầu.")
            return

        if result and result.get("kind") == "status":
            status = result.get("status", "")
            if status and not status.startswith("Camera đang hoạt động"):
                st.session_state["attendance_camera_error"] = status
        elif result and result.get("kind") == "frame":
            frame_id = int(result.get("frame_id", 0))
            if frame_id > st.session_state.get(
                "attendance_last_component_frame_id",
                0,
            ):
                st.session_state["attendance_last_component_frame_id"] = (
                    frame_id
                )
                try:
                    frame = decode_camera_image(result.get("image"))
                    faces_list, _ = detect_faces(
                        frame,
                        processing_width=480,
                        return_gray=False,
                    )
                    st.session_state["attendance_faces"] = faces_list
                    st.session_state.pop("attendance_camera_error", None)
                    prediction, _ = get_or_update_prediction(
                        st.session_state,
                        "attendance",
                        frame,
                        faces_list,
                        crop_and_resize_face,
                        predict_face,
                        camera_index=selected_camera_index,
                    )
                    st.session_state["attendance_prediction"] = prediction
                    st.session_state.pop("attendance_model_error", None)
                except (FileNotFoundError, ValueError, cv2.error) as error:
                    st.session_state["attendance_model_error"] = str(error)
                    st.session_state["attendance_faces"] = []
                    st.session_state["attendance_prediction"] = None
        elif not result:
            st.info("Đang chờ camera khởi động...")

        if st.session_state.get("attendance_camera_error"):
            st.error(st.session_state["attendance_camera_error"])
            st.button(
                "Thử mở lại camera",
                key="retry_attendance_camera",
                type="primary",
                on_click=_retry_attendance_camera,
            )

        if st.session_state.get("attendance_model_error"):
            st.error(
                "Không thể nhận diện khuôn mặt: "
                + st.session_state["attendance_model_error"]
            )

        faces_list = st.session_state.get("attendance_faces", [])
        prediction = st.session_state.get("attendance_prediction")
        if prediction and prediction.get("error"):
            st.error(
                "Không thể nhận diện khuôn mặt: "
                + str(prediction["error"])
            )
        live_records = daily_records
        matched_student = None
        if prediction and prediction.get("is_match"):
            matched_student = student_by_code.get(prediction.get("display_code"))

        if not faces_list:
            st.caption("Đang tìm khuôn mặt trước camera.")
        elif len(faces_list) > 1:
            st.warning("Vui lòng chỉ để một học sinh trước camera.")
        elif matched_student is not None and prediction is not None:
            st.success(
                f"Nhận diện: **{matched_student.student_code} · "
                f"{matched_student.full_name}** · "
                f"Lớp {matched_student.class_name}"
            )
            st.caption(
                f"Khoảng cách nhận diện: {prediction['confidence']:.3f}"
            )
            student_events = live_records[
                live_records["student_code"] == matched_student.student_code
            ]
            has_check_in = bool(
                (student_events["attendance_type"] == "IN").any()
            ) or (
                matched_student.student_code,
                "IN",
            ) in live_recorded_events
            has_check_out = bool(
                (student_events["attendance_type"] == "OUT").any()
            ) or (
                matched_student.student_code,
                "OUT",
            ) in live_recorded_events
            if has_check_in and has_check_out:
                st.info("Đã điểm danh vào và ra trong buổi học này.")
            elif has_check_in:
                st.caption("Đã điểm danh vào · Còn thiếu lượt ra.")
            elif has_check_out:
                st.caption("Đã điểm danh ra · Còn thiếu lượt vào.")

            if not has_check_in:
                st.warning(
                    "Chưa có lượt vào; nút điểm danh ra đang bị khóa."
                )
            status_col, check_in_col, check_out_col = st.columns([1, 1, 1])
            with status_col:
                live_status = st.selectbox(
                    "Trạng thái chuyên cần",
                    ["Có mặt", "Đi muộn"],
                    key="attendance_live_status",
                )
            with check_in_col:
                confirm_check_in = st.button(
                    "Điểm danh vào",
                    type="primary",
                    key="confirm_live_attendance_IN",
                    disabled=has_check_in,
                )
            with check_out_col:
                confirm_check_out = st.button(
                    "Điểm danh ra",
                    key="confirm_live_attendance_OUT",
                    disabled=not has_check_in or has_check_out,
                )

            if confirm_check_in or confirm_check_out:
                event_to_record = "IN" if confirm_check_in else "OUT"
                event_to_record_label = (
                    "vào" if event_to_record == "IN" else "ra"
                )
                try:
                    record_student_attendance(
                        matched_student.student_code,
                        selected_class_id,
                        attendance_date,
                        session_name,
                        live_status,
                        method="face",
                        confidence=prediction["confidence"],
                        attendance_type=event_to_record,
                    )
                    live_recorded_events.add(
                        (matched_student.student_code, event_to_record)
                    )
                    st.success(
                        f"Đã ghi nhận điểm danh {event_to_record_label} cho "
                        f"{matched_student.student_code} · "
                        f"{matched_student.full_name} lúc "
                        f"{time.strftime('%H:%M:%S')}."
                    )
                except ValueError as error:
                    st.warning(str(error))
        elif prediction is not None and prediction.get("is_match"):
            st.warning(
                "Khuôn mặt khớp hồ sơ nhưng không thuộc lớp đang chọn."
            )
        elif len(faces_list) == 1:
            st.info(
                "Đã phát hiện khuôn mặt nhưng chưa khớp hồ sơ học sinh."
            )

    render_attendance_camera()
    image_file = None
    image_bytes = None
elif source == "Chụp ảnh bằng camera":
    st.session_state["attendance_is_running"] = False
    st.session_state["attendance_stream_active"] = False
    st.session_state["attendance_read_failures"] = 0
    release_camera(st.session_state, "attendance")
    image_file = st.camera_input(
        "Chụp ảnh học sinh",
        help="Cho phép trình duyệt truy cập camera và chụp ảnh có mặt rõ nét.",
    )
else:
    st.session_state["attendance_is_running"] = False
    st.session_state["attendance_stream_active"] = False
    st.session_state["attendance_read_failures"] = 0
    release_camera(st.session_state, "attendance")
    image_file = st.file_uploader(
        "Chọn ảnh để nhận diện",
        type=["jpg", "jpeg", "png"],
    )

image_bytes = None
if source != "Camera trực tiếp" and image_file is not None:
    file_key = (source, image_file.file_id)
    if st.session_state.get("attendance_image_file_key") == file_key:
        image_bytes = st.session_state.get("attendance_image_bytes")
    else:
        try:
            image_bytes = bytes(image_file.getvalue())
        except MediaFileStorageError:
            st.session_state.pop("attendance_image_bytes", None)
            st.session_state.pop("attendance_image_file_key", None)
            st.warning(
                "Ảnh không còn khả dụng trong phiên. "
                "Vui lòng chụp hoặc tải ảnh lên lại."
            )
        else:
            st.session_state["attendance_image_file_key"] = file_key
            st.session_state["attendance_image_bytes"] = image_bytes

analyze_submitted = st.button(
    "Phân tích ảnh",
    type="primary",
    disabled=image_bytes is None,
)
if analyze_submitted and image_bytes is not None:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        if image_bytes is not None:
            st.error("Không thể đọc ảnh. Hãy chọn tệp JPG hoặc PNG hợp lệ.")
    else:
        faces, _ = detect_faces(image)
        if not faces:
            st.session_state["attendance_candidates"] = []
            st.warning("Chưa phát hiện khuôn mặt trong ảnh. Chưa ghi nhận điểm danh.")
        else:
            candidates = []
            for face_box in faces:
                try:
                    face_image = crop_and_resize_face(image, face_box)
                    prediction = predict_face(face_image)
                except FileNotFoundError as error:
                    st.error(f"Chưa có mô hình nhận diện. {error}")
                    candidates = []
                    break
                except (ValueError, cv2.error) as error:
                    st.error(f"Không thể phân tích khuôn mặt: {error}")
                    candidates = []
                    break

                code = prediction.get("display_code")
                student = student_by_code.get(code)
                candidates.append(
                    {
                        "student_code": code if prediction.get("is_match") else None,
                        "name": student.full_name if student else (
                            "Học sinh thuộc lớp khác" if prediction.get("is_match")
                            else "Chưa nhận diện"
                        ),
                        "class_name": student.class_name if student else "—",
                        "distance": float(prediction.get("confidence", 1.0)),
                        "match": bool(prediction.get("is_match")),
                    }
                )
            st.session_state["attendance_candidates"] = candidates

candidates = st.session_state.get("attendance_candidates")
if candidates is not None:
    st.subheader("Kết quả phân tích")
    st.dataframe(
        records_to_dataframe(
            [
                {
                    "Mã học sinh": item["student_code"] or "—",
                    "Họ và tên": item["name"],
                    "Lớp": item["class_name"],
                    "Khoảng cách nhận diện": round(item["distance"], 3),
                    "Kết quả": "Khớp trong lớp" if (
                        item["student_code"] in student_by_code
                    ) else (
                        "Khớp học sinh lớp khác" if item["match"] else "Chưa nhận diện"
                    ),
                }
                for item in candidates
            ],
            [
                "Mã học sinh",
                "Họ và tên",
                "Lớp",
                "Khoảng cách nhận diện",
                "Kết quả",
            ],
        ),
        width="stretch",
        hide_index=True,
    )

    editable_records = daily_records[
        daily_records["attendance_method"] != "Dữ liệu chuyển đổi"
    ]
    if not editable_records.empty:
        with st.expander("Điều chỉnh kết quả đã xác nhận"):
            record_by_id = {
                row.id: row for row in editable_records.itertuples(index=False)
            }
            selected_log_id = st.selectbox(
                "Lượt điểm danh",
                list(record_by_id),
                format_func=lambda value: (
                    f"{record_by_id[value].student_code} · "
                    f"{record_by_id[value].student_name} · "
                    f"{record_by_id[value].session_name or 'Dữ liệu cũ'}"
                ),
            )
            existing_record = record_by_id[selected_log_id]
            with st.form("correct_attendance_form"):
                corrected_code = st.selectbox(
                    "Học sinh đúng",
                    list(student_by_code),
                    index=(
                        list(student_by_code).index(existing_record.student_code)
                        if existing_record.student_code in student_by_code else 0
                    ),
                )
                status_options = ["Có mặt", "Đi muộn", "Vắng mặt"]
                existing_status = str(existing_record.attendance_status)
                corrected_status = st.selectbox(
                    "Trạng thái đúng",
                    status_options,
                    index=(
                        status_options.index(existing_status)
                        if existing_status in status_options else 0
                    ),
                )
                correction_submitted = st.form_submit_button(
                    "Lưu điều chỉnh thủ công",
                    type="primary",
                )
            if correction_submitted:
                try:
                    update_student_attendance(
                        selected_log_id,
                        corrected_code,
                        selected_class_id,
                        corrected_status,
                    )
                    daily_records = load_daily_records()
                    st.success("Đã cập nhật kết quả điểm danh.")
                except ValueError as error:
                    st.warning(str(error))

    recognized = [
        item for item in candidates
        if item["student_code"] in student_by_code
    ]
    if recognized:
        st.markdown("#### Giáo viên xác nhận học sinh đã nhận diện")
        for candidate_index, item in enumerate(recognized):
            row = student_by_code[item["student_code"]]
            col_name, col_status, col_action = st.columns([2, 1.2, 1])
            col_name.write(f"**{row.student_code} · {row.full_name}**")
            status = col_status.selectbox(
                "Trạng thái",
                ["Có mặt", "Đi muộn"] if attendance_event == "IN"
                else ["Có mặt", "Đi muộn"],
                key=(
                    f"face_status_{attendance_event}_"
                    f"{row.student_code}_{candidate_index}"
                ),
            )
            student_events = daily_records[
                daily_records["student_code"] == row.student_code
            ]
            has_check_in = bool(
                (student_events["attendance_type"] == "IN").any()
            )
            has_check_out = bool(
                (student_events["attendance_type"] == "OUT").any()
            )
            event_exists = (
                has_check_in if attendance_event == "IN" else has_check_out
            )
            if attendance_event == "OUT" and not has_check_in:
                col_action.warning("Chưa có lượt vào.")
                continue
            if event_exists:
                event_label = "vào" if attendance_event == "IN" else "ra"
                col_action.caption(f"Đã điểm danh {event_label}.")
                continue
            if col_action.button(
                f"Xác nhận {attendance_type.removeprefix('Điểm danh ').lower()}",
                key=f"confirm_face_{attendance_event}_{row.student_code}_{candidate_index}",
                type="primary",
            ):
                try:
                    record_student_attendance(
                        row.student_code,
                        selected_class_id,
                        attendance_date,
                        session_name,
                        status,
                        method="face",
                        confidence=item["distance"],
                        attendance_type=attendance_event,
                    )
                    daily_records = load_daily_records()
                    st.success(f"Đã xác nhận điểm danh {row.full_name}.")
                except ValueError as error:
                    st.warning(str(error))
    else:
        st.info("Chưa có học sinh nào được nhận diện trong lớp đã chọn.")

st.divider()
with st.expander("Điểm danh thủ công hoặc ghi nhận vắng mặt"):
    st.caption("Chỉ giáo viên lựa chọn và xác nhận mới tạo trạng thái; không suy ra vắng mặt từ kết quả camera.")
    with st.form("manual_attendance_form"):
        manual_event_label = st.selectbox(
            "Loại lượt điểm danh",
            ["Điểm danh vào", "Điểm danh ra"],
            index=0 if attendance_event == "IN" else 1,
        )
        manual_event = (
            "IN" if manual_event_label == "Điểm danh vào" else "OUT"
        )
        manual_student_id = st.selectbox(
            "Học sinh",
            list(student_by_id),
            format_func=lambda value: (
                f"{student_by_id[value].student_code} · {student_by_id[value].full_name}"
            ),
        )
        manual_status = st.selectbox(
            "Trạng thái điểm danh",
            ["Có mặt", "Đi muộn", "Vắng mặt"]
            if manual_event == "IN" else ["Có mặt", "Đi muộn"],
        )
        manual_submitted = st.form_submit_button("Lưu điểm danh thủ công")
    if manual_submitted:
        student = student_by_id[manual_student_id]
        try:
            record_student_attendance(
                student.student_code,
                selected_class_id,
                attendance_date,
                session_name,
                manual_status,
                method="manual",
                attendance_type=manual_event,
            )
            daily_records = load_daily_records()
            st.success(f"Đã lưu trạng thái cho {student.full_name}.")
        except ValueError as error:
            st.warning(str(error))

st.subheader("Danh sách điểm danh trong ngày")

@st.fragment(run_every=1.5 if camera_running else None)
def render_daily_attendance_records():
    current_records = load_daily_records()
    if current_records.empty:
        st.info("Chưa có lượt điểm danh được xác nhận trong buổi học này.")
        return

    display_records = current_records.rename(
        columns={
            "student_code": "Mã học sinh",
            "student_name": "Họ và tên",
            "class_name": "Lớp",
            "session_name": "Buổi học",
            "attendance_status": "Trạng thái",
            "attendance_type": "Loại lượt",
            "attendance_method": "Phương thức",
            "log_time": "Thời gian ghi nhận",
        }
    )
    st.dataframe(
        display_records[
            [
                "Mã học sinh",
                "Họ và tên",
                "Lớp",
                "Buổi học",
                "Loại lượt",
                "Trạng thái",
                "Phương thức",
                "Thời gian ghi nhận",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


render_daily_attendance_records()
