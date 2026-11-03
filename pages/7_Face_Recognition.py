import time
import cv2
import streamlit as st

from core.camera_stream import (
    STREAM_FRAME_INTERVAL,
    STREAM_SLEEP_INTERVAL,
    clear_prediction_cache,
    get_or_create_camera,
    get_or_update_prediction,
    read_camera_frame,
    release_camera,
    release_inactive_cameras,
    render_stream_frame,
    update_detected_faces,
)
from core.face_detect import detect_faces
from core.face_recognizer import predict_face, train_model
from core.save_face import crop_and_resize_face
from db.database import initialize_database

PAGE_KEY = "face_recognition"
RECOGNITION_PADDING_RATIO = 0.18

initialize_database()

if f"{PAGE_KEY}_is_running" not in st.session_state:
    st.session_state[f"{PAGE_KEY}_is_running"] = False

release_inactive_cameras(st.session_state, PAGE_KEY)

st.title("Kiểm tra mô hình nhận diện khuôn mặt")
st.caption("Huấn luyện mô hình và kiểm tra khả năng nhận diện trực tiếp bằng camera.")

# --- STEP 1: TRAIN MODEL ---
train_col, summary_col = st.columns([1.1, 1], gap="large")

with train_col:
    with st.container(border=True):
        st.subheader("Bước 1: Huấn luyện mô hình")
        st.caption("Huấn luyện lại sau khi thay đổi hồ sơ hoặc ảnh khuôn mặt.")

        if st.button("Huấn luyện mô hình nhận diện", type="primary", width="stretch"):
            try:
                result = train_model()
                st.session_state[f"{PAGE_KEY}_train_result"] = result
                st.session_state[f"{PAGE_KEY}_train_error"] = None
                st.toast("✅ Huấn luyện mô hình nhận diện thành công!")
            except Exception as error:
                st.session_state[f"{PAGE_KEY}_train_result"] = None
                st.session_state[f"{PAGE_KEY}_train_error"] = str(error)
                st.toast(f"⚠️ Huấn luyện thất bại: {error}")

with summary_col:
    with st.container(border=True):
        st.subheader("Kết quả huấn luyện")
        train_error = st.session_state.get(f"{PAGE_KEY}_train_error")
        train_result = st.session_state.get(f"{PAGE_KEY}_train_result")

        if train_error:
            st.error(f"Huấn luyện thất bại: {train_error}")
        elif train_result:
            metric_col_1, metric_col_2 = st.columns(2)
            metric_col_1.metric("Số ảnh", train_result["num_images"])
            metric_col_2.metric("Số học sinh", train_result["num_people"])

            with st.expander("Mã học sinh trong mô hình"):
                st.json(train_result["label_to_code"])

            with st.expander("Ngưỡng từ chối kết quả không khớp"):
                st.json(train_result["code_thresholds"])

            with st.expander("Cấu hình ngưỡng theo camera"):
                st.json(train_result["camera_profiles"])
        else:
            st.info("Huấn luyện mô hình để xem kết quả và ngưỡng hiện tại.")

st.divider()

# --- STEP 2: TEST RECOGNITION (NATIVE LIVE LOOP) ---
st.subheader("Bước 2: Kiểm tra nhận diện")

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
        if st.button("Bắt đầu kiểm tra", type="primary", width="stretch"):
            st.session_state[f"{PAGE_KEY}_is_running"] = True
    with btn_stop_col:
        if st.button("⏹️ Tắt", width="stretch"):
            st.session_state[f"{PAGE_KEY}_is_running"] = False
            release_camera(st.session_state, PAGE_KEY)
            clear_prediction_cache(st.session_state, PAGE_KEY)
            st.rerun()

with control_col_3:
    with st.container(border=True):
        st.caption("Mục tiêu kiểm tra")
        st.write("Xác minh mô hình nhận diện trực tiếp trên luồng Native Camera thời gian thực.")

previous_camera_index = st.session_state.get(f"{PAGE_KEY}_active_camera_index")
if previous_camera_index != selected_camera_index:
    st.session_state[f"{PAGE_KEY}_active_camera_index"] = selected_camera_index
    release_camera(st.session_state, PAGE_KEY)
    clear_prediction_cache(st.session_state, PAGE_KEY)

preview_col, status_col = st.columns([1.5, 1], gap="large")

with preview_col:
    with st.container(border=True):
        st.subheader("Nhận diện trực tiếp")
        video_placeholder = st.empty()

with status_col:
    status_card_placeholder = st.empty()

is_running = st.session_state.get(f"{PAGE_KEY}_is_running", False)

if not is_running:
    video_placeholder.info("Camera đang tắt. Bấm **'▶️ Bật Live Test'** để kiểm tra nhận diện trực tiếp.")
    with status_card_placeholder.container(border=True):
        st.subheader("Trạng thái nhận diện")
        st.write("**Trạng thái:** Đã dừng")
        st.info("Bật camera để xem kết quả nhận diện thời gian thực.")
else:
    cap = get_or_create_camera(st.session_state, PAGE_KEY, selected_camera_index)
    if cap is None or not cap.isOpened():
        st.session_state[f"{PAGE_KEY}_is_running"] = False
        release_camera(st.session_state, PAGE_KEY)
        video_placeholder.error("Không thể mở thiết bị Camera.")
    else:
        frame_counter = 0
        fps_start = time.time()
        last_video_time = 0.0
        last_ui_time = 0.0
        last_rendered_faces = -1
        last_rendered_pred_id = None

        while st.session_state.get(f"{PAGE_KEY}_is_running", False):
            ret, frame = read_camera_frame(cap)
            if not ret or frame is None:
                video_placeholder.warning("Đang chờ khung hình...")
                time.sleep(0.03)
                continue

            frame_counter += 1
            faces_list = update_detected_faces(st.session_state, PAGE_KEY, frame, detect_faces)
            annotated_frame = frame.copy()

            prediction = None
            is_new_prediction = False
            model_error = False

            try:
                prediction, is_new_prediction = get_or_update_prediction(
                    st.session_state,
                    PAGE_KEY,
                    frame,
                    faces_list,
                    crop_and_resize_face,
                    predict_face,
                    camera_index=selected_camera_index,
                    padding_ratio=RECOGNITION_PADDING_RATIO,
                )
            except Exception:
                prediction = None
                is_new_prediction = False
                model_error = True

            # Vẽ Bounding Box trực quan theo trạng thái nhận diện thực tế
            for (x, y, w, h) in faces_list:
                if len(faces_list) > 1:
                    label_text = f"Nhiều khuôn mặt ({len(faces_list)})"
                    box_color = (0, 165, 255)  # Màu cam cảnh báo
                elif model_error:
                    label_text = "Lỗi mô hình"
                    box_color = (0, 0, 255)    # Màu đỏ lỗi
                elif prediction is not None:
                    if prediction.get("is_match", False):
                        label_text = f"{prediction['display_code']} ({prediction['confidence']:.2f})"
                        box_color = (0, 255, 0)  # Màu xanh lá nhận diện chuẩn xác
                    else:
                        label_text = f"Chưa nhận diện ({prediction['confidence']:.2f})"
                        box_color = (0, 0, 255)  # Màu đỏ chưa đăng ký
                else:
                    # Đang quét / phân tích khuôn mặt lần đầu (chưa có kết quả)
                    label_text = "Đang quét..."
                    box_color = (0, 215, 255)  # Màu vàng cam đang quét

                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), box_color, 2)
                cv2.putText(
                    annotated_frame,
                    label_text,
                    (x, max(20, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    box_color,
                    2,
                )

            elapsed = time.time() - fps_start
            fps = frame_counter / elapsed if elapsed > 0 else 0
            cv2.putText(
                annotated_frame,
                f"LIVE: {fps:.1f} FPS | Faces: {len(faces_list)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )

            # Điều tiết hiển thị video Zero-Delay (Golden FPS ~14.7 FPS, Turbo-JPEG nhẹ ~20KB)
            now = time.time()
            if now - last_video_time >= STREAM_FRAME_INTERVAL:
                render_stream_frame(video_placeholder, annotated_frame)
                last_video_time = now

            # Điều tiết cập nhật widget trạng thái: chỉ vẽ lại khi có kết quả mới, đổi số mặt, hoặc định kỳ 0.25s
            pred_id = (prediction.get("display_code"), prediction.get("is_match")) if prediction else None
            ui_needed = (
                is_new_prediction
                or len(faces_list) != last_rendered_faces
                or pred_id != last_rendered_pred_id
                or (now - last_ui_time >= 0.25)
            )

            if ui_needed:
                last_ui_time = now
                last_rendered_faces = len(faces_list)
                last_rendered_pred_id = pred_id

                with status_card_placeholder.container(border=True):
                    st.subheader("Trạng thái nhận diện")
                    metric_col_1, metric_col_2 = st.columns(2)
                    metric_col_1.metric("Camera", selected_camera_index + 1)
                    metric_col_2.metric("Số khuôn mặt", len(faces_list))

                    if len(faces_list) == 0:
                        st.write("**Trạng thái:** Đang tìm khuôn mặt...")
                        st.caption("Hãy đứng thẳng trước camera.")
                    elif len(faces_list) > 1:
                        st.write("**Trạng thái:** Phát hiện nhiều khuôn mặt")
                        st.warning(f"Phát hiện {len(faces_list)} khuôn mặt. Vui lòng chỉ để 1 người trong khung hình.")
                    elif model_error:
                        st.error("Lỗi khi chạy mô hình nhận diện.")
                    elif prediction is None:
                        st.write("**Trạng thái:** Đang phân tích...")
                        st.info("🔍 Đang nhận diện khuôn mặt, vui lòng giữ yên...")
                    else:
                        if prediction.get("is_match", False):
                            st.success(f"Khớp học sinh: **{prediction['display_code']}**")
                            st.write(f"**Khoảng cách:** {prediction['confidence']:.2f}")
                            st.write(f"**Ngưỡng:** {prediction['match_threshold']:.2f}")
                        else:
                            st.warning("Kết quả: **Chưa nhận diện**")
                            st.write(f"**Khoảng cách:** {prediction['confidence']:.2f}")
                            st.write(f"**Ngưỡng:** {prediction['match_threshold']:.2f}")

            time.sleep(STREAM_SLEEP_INTERVAL)
