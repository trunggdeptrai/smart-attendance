import time
import cv2
import streamlit as st

from core.camera_stream import (
    get_or_create_camera,
    release_camera,
    release_inactive_cameras,
    update_detected_faces,
    annotate_faces,
)
from core.face_detect import detect_faces

PAGE_KEY = "face_detection"

if f"{PAGE_KEY}_is_running" not in st.session_state:
    st.session_state[f"{PAGE_KEY}_is_running"] = False

release_inactive_cameras(st.session_state, PAGE_KEY)

st.title("Kiểm tra phát hiện khuôn mặt")
st.caption("Trang kiểm tra kỹ thuật camera và khả năng phát hiện khuôn mặt bằng OpenCV.")

control_col_1, control_col_2, control_col_3 = st.columns([1, 1.2, 1.2], gap="large")
with control_col_1:
    selected_camera_index = st.selectbox(
        "Chọn camera",
        [0, 1],
        format_func=lambda idx: f"Camera {idx + 1}",
        key=f"{PAGE_KEY}_camera_index",
    )
with control_col_2:
    st.caption("Điều khiển camera")
    btn_start_col, btn_stop_col = st.columns(2)
    with btn_start_col:
        if st.button("▶️ Bật Live Preview", type="primary", width="stretch"):
            st.session_state[f"{PAGE_KEY}_is_running"] = True
    with btn_stop_col:
        if st.button("⏹️ Tắt", width="stretch"):
            st.session_state[f"{PAGE_KEY}_is_running"] = False
            release_camera(st.session_state, PAGE_KEY)
            st.rerun()

with control_col_3:
    with st.container(border=True):
        st.caption("Mục tiêu kiểm tra")
        st.write("Xác minh camera có thể phát hiện một hoặc nhiều khuôn mặt trực tiếp.")

previous_camera_index = st.session_state.get(f"{PAGE_KEY}_active_camera_index")
if previous_camera_index != selected_camera_index:
    st.session_state[f"{PAGE_KEY}_active_camera_index"] = selected_camera_index
    release_camera(st.session_state, PAGE_KEY)

preview_col, info_col = st.columns([1.5, 1], gap="large")

with preview_col:
    with st.container(border=True):
        st.subheader("Hình ảnh camera trực tiếp")
        st.caption("Khung màu xanh đánh dấu khuôn mặt được phát hiện.")
        video_placeholder = st.empty()

with info_col:
    info_card_placeholder = st.empty()

is_running = st.session_state.get(f"{PAGE_KEY}_is_running", False)

if not is_running:
    video_placeholder.info("Camera đang tắt. Bấm **'▶️ Bật Live Preview'** để xem video trực tiếp.")
    with info_card_placeholder.container(border=True):
        st.subheader("Trạng thái phát hiện")
        st.write("**Trạng thái:** Đã dừng")
        st.caption("Bấm 'Bật Live Preview' để bắt đầu phát video.")
else:
    cap = get_or_create_camera(st.session_state, PAGE_KEY, selected_camera_index)
    if cap is None or not cap.isOpened():
        st.session_state[f"{PAGE_KEY}_is_running"] = False
        release_camera(st.session_state, PAGE_KEY)
        video_placeholder.error("Không thể mở thiết bị Camera.")
    else:
        frame_counter = 0
        fps_start = time.time()

        while st.session_state.get(f"{PAGE_KEY}_is_running", False):
            ret, frame = cap.read()
            if not ret or frame is None:
                video_placeholder.warning("Đang chờ khung hình...")
                time.sleep(0.05)
                continue

            frame_counter += 1
            faces_list = update_detected_faces(st.session_state, PAGE_KEY, frame, detect_faces)
            annotated = annotate_faces(frame, faces_list)

            elapsed = time.time() - fps_start
            fps = frame_counter / elapsed if elapsed > 0 else 0
            cv2.putText(
                annotated,
                f"TRỰC TIẾP: {fps:.1f} FPS",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )

            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", width="stretch")

            with info_card_placeholder.container(border=True):
                st.subheader("Trạng thái phát hiện")
                metric_col_1, metric_col_2 = st.columns(2)
                metric_col_1.metric("Camera", selected_camera_index + 1)
                metric_col_2.metric("Số khuôn mặt", len(faces_list))
                st.write("**Trạng thái:** Đang hoạt động")
                st.caption(f"Đang phát mượt mà: {fps:.1f} FPS.")

            time.sleep(0.01)
