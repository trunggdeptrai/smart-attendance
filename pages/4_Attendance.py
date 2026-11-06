"""Điểm danh tự động: chọn ĐIỂM DANH VÀO hoặc ĐIỂM DANH RA VỀ, camera tự bật,
hệ thống tự nhận diện và tự ghi nhận. Phương án có xác nhận/ảnh/thủ công nằm ở
trang "Điểm danh có xác nhận, bằng ảnh và thủ công".
"""

import cv2
import pandas as pd
import streamlit as st

from core.auto_attendance import (
    ALREADY,
    MODE_IN,
    MODE_LABELS,
    MODE_OUT,
    NO_CHECK_IN,
    RECORDED,
    AutoAttendanceSession,
    default_session_name,
)
from core.camera_stream import clear_prediction_cache, get_or_update_prediction
from core.face_detect import detect_faces
from core.face_recognizer import predict_face
from core.live_camera import decode_camera_image, live_camera
from core.research_log import log_teacher_decision, logged_predictor
from core.save_face import crop_and_resize_face
from core.timeutil import today_vn
from db.attendance_repo import get_student_attendance_dataframe
from db.database import get_classes, get_students

PREFIX = "auto"
SESSIONS = ["Buổi sáng", "Buổi chiều", "Buổi tối"]
ss = st.session_state

st.title("Điểm danh tự động")
st.caption(
    "Chọn chế độ một lần: camera tự bật, hệ thống tự nhận diện học sinh trước camera và tự ghi nhận "
    "vào sổ điểm danh. Học sinh không được nhận diện không bị tính vắng."
)

classes = get_classes()
students = get_students()
if not students:
    st.warning("Chưa có học sinh đang học. Hãy thêm học sinh và đăng ký khuôn mặt trước.")
    st.stop()
student_by_code = {row.student_code: row for row in students}
class_map = {row.id: row for row in classes}
today = today_vn()


def _new_scan_session(mode):
    clear_prediction_cache(ss, PREFIX)
    ss["auto_mode"] = mode
    ss["auto_scan"] = AutoAttendanceSession(mode, ss.get("auto_session", default_session_name()))
    ss["auto_restart_key"] = ss.get("auto_restart_key", 0) + 1
    ss["auto_last_frame_id"] = 0
    ss["auto_faces"] = []
    ss["auto_prediction"] = None
    ss.pop("auto_camera_error", None)


def _select_mode(mode):
    if ss.get("auto_mode") == mode and ss.get("auto_scan") is not None:
        return
    _new_scan_session(mode)  # dừng phiên quét cũ, khởi tạo phiên mới


def _stop():
    clear_prediction_cache(ss, PREFIX)
    ss["auto_mode"] = None
    ss["auto_faces"] = []
    ss["auto_prediction"] = None
    ss.pop("auto_camera_error", None)


def _retry_camera():
    ss.pop("auto_camera_error", None)
    ss["auto_restart_key"] = ss.get("auto_restart_key", 0) + 1
    ss["auto_last_frame_id"] = 0


# ---------------- Tùy chọn ----------------
opt1, opt2, opt3, opt4 = st.columns([1.1, 1, 0.9, 1.3])
with opt1:
    if "auto_session" not in ss:
        ss["auto_session"] = default_session_name()
    session_name = st.selectbox("Buổi học", SESSIONS, key="auto_session")
with opt2:
    camera_index = st.selectbox(
        "Camera", [0, 1], key="auto_camera",
        format_func=lambda i: "Camera 1 (điện thoại: trước)" if i == 0 else "Camera 2 (điện thoại: sau)",
    )
with opt3:
    sound_on = st.toggle("Âm thanh báo", value=True, key="auto_sound")
with opt4:
    class_filter = st.selectbox(
        "Lọc theo lớp (bảng, thống kê)", [None] + list(class_map), key="auto_class_filter",
        format_func=lambda v: "Tất cả lớp" if v is None else f"{class_map[v].class_code} · {class_map[v].name}",
    )

scan = ss.get("auto_scan")
mode = ss.get("auto_mode")
if scan is not None and mode and scan.session_name != session_name:
    _new_scan_session(mode)  # đổi buổi học -> phiên quét mới cho buổi đó
    scan = ss["auto_scan"]

# ---------------- Chọn chế độ ----------------
st.markdown(
    """
    <style>
    div[data-testid="stButton"] button[kind] p { font-size: 1.15rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)
mode_in_col, mode_out_col = st.columns(2)
with mode_in_col:
    st.button(
        "▶ ĐIỂM DANH VÀO", key="auto_btn_in", width="stretch",
        type="primary" if mode == MODE_IN else "secondary",
        on_click=_select_mode, args=(MODE_IN,),
    )
    st.caption("Hệ thống tự động nhận diện học sinh và ghi nhận thời gian đến trường.")
with mode_out_col:
    st.button(
        "◀ ĐIỂM DANH RA VỀ", key="auto_btn_out", width="stretch",
        type="primary" if mode == MODE_OUT else "secondary",
        on_click=_select_mode, args=(MODE_OUT,),
    )
    st.caption("Hệ thống tự động nhận diện học sinh và ghi nhận thời gian ra về.")

if mode:
    info_col, stop_col = st.columns([3, 1])
    info_col.markdown(
        f"**Đang hoạt động: {MODE_LABELS[mode]}** · {session_name} · {today:%d/%m/%Y}"
    )
    stop_col.button("■ Dừng camera", key="auto_btn_stop", width="stretch", on_click=_stop)


def _result_card(result):
    title = result.get("title", "")
    who = f"{result['student_code']} · {result.get('full_name', '')} · Lớp {result.get('class_name', '')}"
    times = []
    if result.get("check_in"):
        times.append(f"Giờ vào: {result['check_in']}")
    if result.get("check_out"):
        times.append(f"Giờ ra: {result['check_out']}")
    detail = f"{who}  \n{' · '.join(times) if times else result.get('message', '')}"
    if result.get("check_in") and result.get("check_out"):
        detail += "  \nTrạng thái: ĐÃ HOÀN THÀNH"
    text = f"**{title}**  \n{detail}"
    outcome = result.get("outcome")
    if outcome == RECORDED:
        st.success(text, icon=":material/check_circle:")
    elif outcome == ALREADY:
        st.info(text, icon=":material/info:")
    elif outcome == NO_CHECK_IN:
        st.warning(text, icon=":material/warning:")
    else:
        st.error(text, icon=":material/error:")


# ---------------- Camera + xử lý tự động ----------------
@st.fragment
def render_camera():
    mode = ss.get("auto_mode")
    scan = ss.get("auto_scan")
    faces = ss.get("auto_faces", [])
    prediction = ss.get("auto_prediction")
    overlays = []
    if len(faces) == 1:
        label, color = None, "#f4b400"
        if prediction and prediction.get("is_match"):
            row = student_by_code.get(prediction.get("display_code"))
            if row is not None:
                label, color = f"{row.student_code} · {row.full_name} · {row.class_name}", "#00d084"
        elif prediction is not None:
            label, color = "Không xác định được danh tính", "#ffae42"
        x, y, w, h = faces[0]
        overlays.append({"x": x, "y": y, "width": w, "height": h, "label": label, "color": color})
    elif len(faces) > 1:
        overlays = [{"x": x, "y": y, "width": w, "height": h, "label": "Nhiều khuôn mặt", "color": "#ffae42"}
                    for x, y, w, h in faces]

    result = live_camera(
        active=bool(mode),
        camera_index=camera_index,
        overlays=overlays,
        restart_key=ss.get("auto_restart_key", 0),
        face_hint="Đã thấy 1 khuôn mặt – đang nhận diện…",
        beep_id=ss.get("auto_beep_id", 0),
        sound=sound_on,
        key="auto_live_camera",
    )
    if not mode:
        st.info("Chọn **ĐIỂM DANH VÀO** hoặc **ĐIỂM DANH RA VỀ** để camera tự bật và bắt đầu quét.")
        return

    if result and result.get("kind") == "status":
        status = result.get("status", "")
        if status and not status.startswith("Camera đang hoạt động") and not status.startswith("Camera đã sẵn sàng"):
            ss["auto_camera_error"] = status
    elif result and result.get("kind") == "frame":
        frame_id = int(result.get("frame_id", 0))
        if frame_id > ss.get("auto_last_frame_id", 0):
            ss["auto_last_frame_id"] = frame_id
            try:
                frame = decode_camera_image(result.get("image"))
                faces, _ = detect_faces(frame, processing_width=480, return_gray=False)
                ss["auto_faces"] = faces
                ss.pop("auto_camera_error", None)
                prediction, is_new = get_or_update_prediction(
                    ss, PREFIX, frame, faces, crop_and_resize_face,
                    logged_predictor(predict_face, "attendance_auto"), camera_index=camera_index,
                )
                ss["auto_prediction"] = prediction
                ss.pop("auto_model_error", None)
                if is_new and scan is not None:
                    outcome = scan.handle_prediction(prediction, len(faces))
                    if outcome is not None:
                        if outcome["outcome"] == RECORDED:
                            ss["auto_beep_id"] = ss.get("auto_beep_id", 0) + 1
                            log_teacher_decision(
                                "attendance_auto", "auto", attendance_type=mode, method="face",
                                predicted_code=outcome["student_code"], final_code=outcome["student_code"],
                                distance=(prediction or {}).get("confidence"),
                            )
                            st.toast(f"{outcome['title']}: {outcome['student_code']} · {outcome['full_name']}",
                                     icon="✅")
            except FileNotFoundError:
                ss["auto_model_error"] = "Chưa có mô hình nhận diện. Hãy đăng ký khuôn mặt và huấn luyện mô hình."
            except (ValueError, cv2.error) as error:
                ss["auto_model_error"] = str(error)
    elif not result:
        st.caption("Đang khởi tạo camera… Nếu trình duyệt hỏi quyền camera, hãy chọn Cho phép.")

    if ss.get("auto_camera_error"):
        st.error(f"Camera bị gián đoạn: {ss['auto_camera_error']}")
        st.button("Thử mở lại camera", key="auto_retry", type="primary", on_click=_retry_camera)
    if ss.get("auto_model_error"):
        st.error(ss["auto_model_error"])

    faces = ss.get("auto_faces", [])
    prediction = ss.get("auto_prediction")
    if not faces:
        st.caption("Đang quét khuôn mặt…")
    elif len(faces) > 1:
        st.warning("Phát hiện nhiều khuôn mặt – chỉ để một học sinh trước camera.")
    elif prediction is not None and not prediction.get("is_match"):
        st.warning("**KHÔNG NHẬN DIỆN ĐƯỢC** – khuôn mặt chưa khớp hồ sơ học sinh; hệ thống tiếp tục quét.")
    elif prediction is None:
        st.caption("Đang nhận diện…")

    if scan is not None and scan.last_result:
        st.markdown("##### Kết quả gần nhất")
        _result_card(scan.last_result)


render_camera()


# ---------------- Thống kê + danh sách trong phiên ----------------
@st.fragment(run_every=2.0 if mode else None)
def render_stats():
    mode = ss.get("auto_mode")
    scan = ss.get("auto_scan")
    records = get_student_attendance_dataframe(attendance_date=today.isoformat(), class_id=class_filter)
    records = records[records["session_name"] == session_name] if not records.empty else records
    active = [row for row in students if class_filter is None or row.class_id == class_filter]
    ins = records[records["attendance_type"] == "IN"] if not records.empty else records
    outs = records[records["attendance_type"] == "OUT"] if not records.empty else records
    checked_in = set(ins["student_code"]) if not ins.empty else set()
    st.markdown(f"##### Thống kê {session_name.lower()} {today:%d/%m/%Y}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lượt điểm danh vào", len(ins))
    m2.metric("Học sinh đã điểm danh", len(checked_in))
    m3.metric("Lượt điểm danh ra về", len(outs))
    m4.metric("Chưa được ghi nhận", max(0, len({r.student_code for r in active} - checked_in)))

    st.markdown("##### Học sinh vừa được ghi nhận trong phiên")
    log = scan.log if (scan is not None and mode) else []
    if class_filter is not None:
        class_name = class_map[class_filter].name
        log = [item for item in log if item.get("class_name") == class_name]
    if not log:
        st.caption("Chưa có lượt ghi nhận nào trong phiên quét này.")
        return
    rows = []
    for index, item in enumerate(log, start=1):
        moment = f"{pd.to_datetime(item['date']):%d/%m/%Y} {item['time'][:5]}"
        state = "ĐÃ ĐIỂM DANH VÀO" if item["mode"] == MODE_IN else "ĐÃ ĐIỂM DANH RA VỀ"
        if item.get("check_in") and item.get("check_out"):
            state = f"ĐÃ HOÀN THÀNH (vào {item['check_in'][:5]}, ra {item['check_out'][:5]})"
        rows.append({"STT": index, "Mã HS": item["student_code"], "Họ tên": item.get("full_name", ""),
                     "Lớp": item.get("class_name", ""), "Thời gian": moment, "Trạng thái": state})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


render_stats()
st.caption(
    "Cần ghi vắng, điều chỉnh kết quả hoặc điểm danh bằng ảnh: dùng trang "
    "“Điểm danh có xác nhận, bằng ảnh và thủ công”."
)
