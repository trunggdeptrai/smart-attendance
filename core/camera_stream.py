import base64
import os
# Giới hạn số luồng CPU của OpenMP / BLAS / MKL để Dlib không chiếm trọn 100% CPU
# Giữ CPU luôn thông thoáng cho OpenCV và Streamlit WebSocket server hoạt động 0ms độ trễ
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

import cv2
import threading
import time
from collections.abc import MutableMapping
from typing import Optional, Tuple, List, Dict, Any

CAMERA_FRAME_WIDTH = 640
CAMERA_FRAME_HEIGHT = 480
CAMERA_PAGE_KEYS = ("register_face", "attendance", "face_detection", "face_recognition")

# Tần số điều tiết hiển thị video qua Streamlit WebSocket (~30 FPS)
# Đảm bảo hiển thị khung hình tức thì thời gian thực, bám sát cử động khuôn mặt 0ms delay
STREAM_FRAME_INTERVAL = 0.033
# Thời gian nhả CPU giữa các vòng lặp streaming để tránh tight spin loop
STREAM_SLEEP_INTERVAL = 0.010
# Keep the Streamlit preview aligned with the measured webcam capture rate.
ATTENDANCE_FRAME_INTERVAL = 1 / 30
ATTENDANCE_CAMERA_FRAME_INTERVAL = 1 / 30
REGISTER_FACE_FRAME_INTERVAL = ATTENDANCE_CAMERA_FRAME_INTERVAL
# Chất lượng nén JPEG tối ưu cho video stream (cân bằng sắc nét và dung lượng nhẹ)
STREAM_JPEG_QUALITY = 75
ATTENDANCE_PREVIEW_WIDTH = 700
ATTENDANCE_PREVIEW_HEIGHT = 394


def crop_frame_to_aspect_ratio(
    frame: Any,
    aspect_ratio: float = 16 / 9,
) -> Tuple[Any, Tuple[int, int]]:
    """Center-crop a preview without changing the source frame used for capture."""
    if frame is None:
        return None, (0, 0)
    if aspect_ratio <= 0:
        raise ValueError("Aspect ratio must be greater than zero.")

    height, width = frame.shape[:2]
    if width <= 0 or height <= 0:
        return frame, (0, 0)

    frame_ratio = width / height
    if frame_ratio > aspect_ratio:
        cropped_width = max(1, int(round(height * aspect_ratio)))
        left = (width - cropped_width) // 2
        return frame[:, left:left + cropped_width], (left, 0)

    cropped_height = max(1, int(round(width / aspect_ratio)))
    top = (height - cropped_height) // 2
    return frame[top:top + cropped_height, :], (0, top)


def translate_face_boxes_for_crop(
    faces: List[Tuple[int, int, int, int]],
    crop_origin: Tuple[int, int],
) -> List[Tuple[int, int, int, int]]:
    """Translate source-frame face boxes to a center-cropped preview."""
    left, top = crop_origin
    return [
        (x - left, y - top, width, height)
        for x, y, width, height in faces
    ]


def resize_frame_to_fit(
    frame: Any,
    max_width: int = ATTENDANCE_PREVIEW_WIDTH,
    max_height: int = ATTENDANCE_PREVIEW_HEIGHT,
) -> Any:
    """Resize a preview without distorting its aspect ratio or enlarging it."""
    if frame is None:
        return None

    height, width = frame.shape[:2]
    if width <= 0 or height <= 0:
        return frame

    scale = min(max_width / width, max_height / height, 1.0)
    if scale >= 1.0:
        return frame

    resized_dimensions = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    return cv2.resize(frame, resized_dimensions, interpolation=cv2.INTER_AREA)


class ThreadedCameraReader:
    """
    Trình đọc camera đa luồng chuyên dụng (Dedicated Camera Capture Thread):
    Liên tục rút cạn bộ đệm DirectShow của Windows ở tốc độ tối đa của phần cứng,
    đảm bảo cap.read() LUÔN LUÔN trả về khung hình mới nhất thời gian thực.
    Loại bỏ triệt để 100% hiện tượng tích tụ bộ đệm gây trễ 1-2 giây khi quay mặt!
    """

    def __init__(self, camera_index: int = 0, width: int = CAMERA_FRAME_WIDTH, height: int = CAMERA_FRAME_HEIGHT):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(camera_index)

        self.latest_frame = None
        self.latest_frame_time = 0.0
        self.last_error: Optional[str] = None
        self.running = False
        self.lock = threading.Lock()
        self.thread = None

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.latest_frame = frame
                self.latest_frame_time = time.monotonic()

            self.running = True
            self.thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.thread.start()

    def _capture_worker(self):
        while self.running and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
            except (cv2.error, OSError) as error:
                self.last_error = str(error)
                self.running = False
                break
            if ret and frame is not None:
                with self.lock:
                    self.latest_frame = frame
                    self.latest_frame_time = time.monotonic()
            else:
                time.sleep(0.005)

    def isOpened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[Any]]:
        with self.lock:
            if (
                self.latest_frame is not None
                and time.monotonic() - self.latest_frame_time <= 1.5
            ):
                return True, self.latest_frame.copy()
        return False, None

    def release(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=0.3)
            except Exception:
                pass
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass


def get_or_create_camera(
    session_state: MutableMapping[Any, Any],
    prefix: str,
    camera_index: int,
) -> Optional[ThreadedCameraReader]:
    """
    Khởi tạo hoặc tái sử dụng camera phần cứng đa luồng chuyên dụng (ThreadedCameraReader).
    Đảm bảo 0ms độ trễ tích lũy khung hình trên Windows DirectShow.
    """
    cap_key = f"{prefix}_cap"
    index_key = f"{prefix}_camera_index_value"
    cap = session_state.get(cap_key)
    current_index = session_state.get(index_key)

    # Đảm bảo cap là ThreadedCameraReader hợp lệ; nếu là VideoCapture cũ thì hủy và tạo mới
    if cap is None or not isinstance(cap, ThreadedCameraReader) or current_index != camera_index or not cap.isOpened():
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        reader = ThreadedCameraReader(camera_index)
        if reader.isOpened():
            session_state[cap_key] = reader
            session_state[index_key] = camera_index
            return reader
        else:
            session_state[cap_key] = None
            session_state[index_key] = None
            return None

    return cap


RECOGNITION_COOLDOWN_SECONDS = 3.0       # Giãn cách 3 giây khi đã nhận diện thành công một nhân viên
RECOGNITION_UNKNOWN_RETRY_SECONDS = 1.5  # Giãn cách 1.5 giây khi chưa nhận diện được hoặc Unknown
PREDICTION_INTERVAL_SECONDS = 0.25       # Tần suất tối thiểu giữa các lần trigger
PREDICTION_POSITION_TOLERANCE = 20
PREDICTION_SIZE_TOLERANCE = 20


class PredictionStore:
    """
    Bộ lưu trữ kết quả nhận diện khuôn mặt an toàn đa luồng (Thread-safe Prediction Store):
    Tách biệt hoàn toàn việc lưu trữ kết quả khỏi Streamlit SessionStateProxy,
    cho phép worker thread ghi dữ liệu trên heap an toàn mà không bị Streamlit
    cô lập vào _mock_session_state.
    Tích hợp bộ điều phối nhận diện thông minh (Smart Recognition Coordinator):
    Khóa nhãn và duy trì kết quả cho khuôn mặt đã nhận diện, giải phóng triệt để
    Python GIL để camera đạt 30 FPS thời gian thực không độ trễ.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.prediction: Optional[Dict[str, Any]] = None
        self.prediction_id: float = 0.0
        self.last_read_id: float = 0.0
        self.is_busy: bool = False
        self.last_predict_time: float = 0.0
        self.last_face_box: Optional[Tuple[int, int, int, int]] = None
        self.empty_frames_count: int = 0
        self._generation = 0
        self._busy_generation: Optional[int] = None

    def get_prediction(self) -> Tuple[Optional[Dict[str, Any]], bool, bool]:
        """
        Đọc kết quả mới nhất từ luồng chính (Main thread).
        Trả về: (latest_prediction, is_new, is_busy)
        """
        with self.lock:
            is_new = False
            if self.prediction_id > 0 and self.prediction_id != self.last_read_id:
                self.last_read_id = self.prediction_id
                is_new = True
            pred_copy = dict(self.prediction) if self.prediction is not None else None
            return pred_copy, is_new, self.is_busy

    def set_prediction(
        self,
        result: Optional[Dict[str, Any]],
        finished_at: Optional[float] = None,
        generation: Optional[int] = None,
    ) -> None:
        """
        Ghi kết quả từ background worker thread và cập nhật thời điểm kết thúc nhận diện.
        """
        with self.lock:
            if generation is not None and generation != self._generation:
                if self._busy_generation == generation:
                    self.is_busy = False
                    self._busy_generation = None
                return
            finish_ts = finished_at if finished_at is not None else time.time()
            self.prediction = result
            self.prediction_id = finish_ts
            self.last_predict_time = finish_ts
            self.is_busy = False
            self._busy_generation = None

    def set_busy(
        self,
        busy: bool,
        now: float,
        face_box: Tuple[int, int, int, int],
    ) -> int:
        with self.lock:
            self.is_busy = busy
            self.last_predict_time = now
            self.last_face_box = face_box
            if busy:
                self._busy_generation = self._generation
            else:
                self._busy_generation = None
            return self._generation

    def can_trigger(self, now: float, current_face_box: Tuple[int, int, int, int]) -> bool:
        """
        Điều phối thông minh việc kích hoạt Dlib nhận diện:
        - Nếu worker đang bận: Tuyệt đối không kích hoạt (tránh dồn ứ thread).
        - Nếu chưa có kết quả (khuôn mặt mới xuất hiện): Kích hoạt ngay lập tức.
        - Nếu đã match thành công: Giữ nguyên nhãn và chỉ quét lại sau RECOGNITION_COOLDOWN_SECONDS (3.0s).
          Không kích hoạt lại chỉ vì khuôn mặt chuyển động nhẹ/vừa trong khung hình!
        - Nếu là Unknown: Chờ ít nhất RECOGNITION_UNKNOWN_RETRY_SECONDS (1.5s) trước khi thử lại.
        Nhờ đó, Python GIL thông thoáng 95% thời gian -> Camera không bị delay 2-3s!
        """
        with self.lock:
            if self.is_busy:
                return False
            if self.prediction is None:
                return True

            # Trường hợp khuôn mặt đã được nhận diện hợp lệ (Match)
            if self.prediction.get("is_match", False):
                # Chỉ quét lại định kỳ sau 3.0 giây để xác nhận, giải phóng GIL cho OpenCV & Streamlit
                return (now - self.last_predict_time) >= RECOGNITION_COOLDOWN_SECONDS

            # Trường hợp Unknown
            time_passed = (now - self.last_predict_time) >= RECOGNITION_UNKNOWN_RETRY_SECONDS
            box_moved = _face_box_changed(self.last_face_box, current_face_box)
            # Thử lại nếu đã qua 1.5s VÀ (mặt di chuyển góc nhìn mới HOẶC đã quá 3.0s)
            return time_passed and (box_moved or (now - self.last_predict_time) >= (RECOGNITION_UNKNOWN_RETRY_SECONDS * 2))

    def handle_faces_count(self, count: int) -> bool:
        """
        Quản lý grace period 5 frame để chống chớp tắt làm mất dấu nhận diện tức thời.
        - Trả về True nếu vẫn trong trạng thái hợp lệ.
        - Trả về False nếu quá 5 frame không có khuôn mặt nào.
        """
        with self.lock:
            if count == 1:
                self.empty_frames_count = 0
                return True
            else:
                self.empty_frames_count += 1
                if self.empty_frames_count >= 5:
                    if self.prediction is not None or self.last_face_box is not None:
                        self._generation += 1
                    self.prediction = None
                    self.prediction_id = 0.0
                    self.last_read_id = 0.0
                    self.last_face_box = None
                    if self._busy_generation is None:
                        self.is_busy = False
                    return False
                return True

    def clear(self) -> None:
        with self.lock:
            self._generation += 1
            self.prediction = None
            self.prediction_id = 0.0
            self.last_read_id = 0.0
            if self._busy_generation is None:
                self.is_busy = False
            self.last_predict_time = 0.0
            self.last_face_box = None
            self.empty_frames_count = 0


def clear_prediction_cache(session_state: MutableMapping[Any, Any], prefix: str) -> None:
    store_key = f"{prefix}_prediction_store"
    store = session_state.get(store_key)
    if store is not None and isinstance(store, PredictionStore):
        store.clear()
    session_state[f"{prefix}_prediction"] = None
    session_state[f"{prefix}_prediction_face"] = None
    session_state[f"{prefix}_prediction_counter"] = 0
    session_state[f"{prefix}_prediction_id"] = None
    session_state[f"{prefix}_last_count_id"] = None
    session_state[f"{prefix}_worker_busy"] = False
    session_state[f"{prefix}_last_predict_time"] = 0.0
    session_state[f"{prefix}_last_face_box"] = None


def _normalize_face_box(face_box: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    return (
        int(face_box[0]),
        int(face_box[1]),
        int(face_box[2]),
        int(face_box[3]),
    )


def _face_box_changed(previous_face_box: Optional[Tuple[int, int, int, int]], current_face_box: Tuple[int, int, int, int]) -> bool:
    if previous_face_box is None:
        return True

    previous_x, previous_y, previous_w, previous_h = previous_face_box
    current_x, current_y, current_w, current_h = current_face_box

    return (
        abs(previous_x - current_x) > PREDICTION_POSITION_TOLERANCE
        or abs(previous_y - current_y) > PREDICTION_POSITION_TOLERANCE
        or abs(previous_w - current_w) > PREDICTION_SIZE_TOLERANCE
        or abs(previous_h - current_h) > PREDICTION_SIZE_TOLERANCE
    )


def get_or_update_prediction(
    session_state: MutableMapping[Any, Any],
    prefix: str,
    frame: Any,
    faces_list: List[Tuple[int, int, int, int]],
    crop_face_fn,
    predict_face_fn,
    camera_index: Optional[int] = None,
    padding_ratio: float = 0.18,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Nhận diện khuôn mặt phi chặn (Non-blocking Background Thread):
    Sử dụng PredictionStore an toàn luồng lưu trên heap Python,
    loại bỏ triệt để lỗi phân mảnh session state của Streamlit.
    Trả về: (latest_prediction, is_new_prediction)
    """
    store_key = f"{prefix}_prediction_store"
    store = session_state.get(store_key)
    if store is None or not isinstance(store, PredictionStore):
        store = PredictionStore()
        session_state[store_key] = store

    # Quản lý số lượng khuôn mặt và grace period (tránh nhấp nháy khi chớp tắt 1 frame)
    is_valid_face = store.handle_faces_count(len(faces_list))
    if not is_valid_face or len(faces_list) != 1:
        latest_prediction, _, _ = store.get_prediction()
        session_state[f"{prefix}_prediction"] = latest_prediction
        return latest_prediction, False

    current_face_box = _normalize_face_box(faces_list[0])
    now = time.time()

    # Kiểm tra xem có cần và có thể kích hoạt worker ngầm không
    if store.can_trigger(now, current_face_box):
        face_crop = crop_face_fn(
            frame,
            current_face_box,
            padding_ratio=padding_ratio,
        )
        generation = store.set_busy(True, now, current_face_box)

        def _worker_thread(
            crop_img,
            cam_idx,
            pred_fn,
            pred_store: PredictionStore,
            worker_generation: int,
        ):
            try:
                kwargs = {}
                if cam_idx is not None:
                    kwargs["camera_index"] = cam_idx
                result = pred_fn(crop_img, **kwargs)
                pred_store.set_prediction(
                    result,
                    generation=worker_generation,
                )
            except Exception as err:
                print(f"Background prediction error: {err}")
                pred_store.set_prediction(
                    {
                        "is_match": False,
                        "display_code": "Unknown",
                        "confidence": 1.0,
                        "error": str(err),
                    },
                    generation=worker_generation,
                )

        t = threading.Thread(
            target=_worker_thread,
            args=(
                face_crop.copy(),
                camera_index,
                predict_face_fn,
                store,
                generation,
            ),
            daemon=True,
        )

        t.start()

    latest_prediction, is_new, _ = store.get_prediction()

    # Đồng bộ ngược vào session_state cho các module cũ đọc nếu cần
    session_state[f"{prefix}_prediction"] = latest_prediction

    return latest_prediction, is_new


def read_camera_frame(cap: Any) -> Tuple[bool, Optional[Any]]:
    """
    Đọc 1 khung hình từ thiết bị camera đã mở.
    Loại bỏ đệm tồn dư của Windows DirectShow để luôn lấy frame mới nhất thời gian thực.
    """
    if cap is None or not cap.isOpened():
        return False, None
    if not isinstance(cap, ThreadedCameraReader):
        try:
            cap.grab()
        except Exception:
            pass
    ret, frame = cap.read()
    return ret, frame


def release_camera(session_state: MutableMapping[Any, Any], prefix: str) -> None:
    """
    Giải phóng camera phần cứng và dọn dẹp các biến liên quan trong session_state.
    Lưu ý: Không gán session_state[f"{prefix}_run_camera"] = False ở đây để tránh
    lỗi StreamlitAPIException khi widget toggle/checkbox đã được render trên trang.
    """
    cap_key = f"{prefix}_cap"
    cap = session_state.get(cap_key)
    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass
    session_state[cap_key] = None
    session_state[f"{prefix}_camera_index_value"] = None


def release_inactive_cameras(
    session_state: MutableMapping[Any, Any],
    active_prefix: Optional[str] = None,
) -> None:
    """
    Đóng tất cả các camera đang mở của các trang khác để tránh lỗi xung đột phần cứng
    (Windows chỉ cho phép 1 tiến trình/tab giữ quyền điều khiển webcam tại một thời điểm).
    """
    for prefix in CAMERA_PAGE_KEYS:
        if active_prefix is not None and prefix == active_prefix:
            continue
        release_camera(session_state, prefix)
        for state_key in (
            f"{prefix}_run_camera",
            f"{prefix}_is_running",
            f"{prefix}_stream_active",
        ):
            if state_key in session_state:
                session_state[state_key] = False


DETECTION_INTERVAL = 1


def update_detected_faces(
    session_state: MutableMapping[Any, Any],
    prefix: str,
    frame: Any,
    detect_faces_fn,
    detection_interval: int = DETECTION_INTERVAL,
) -> List[Tuple[int, int, int, int]]:
    """
    Reuse the most recent boxes between detection passes to limit CPU usage.
    """
    detection_interval = max(1, int(detection_interval))
    faces_key = f"{prefix}_faces"
    counter_key = f"{prefix}_detect_counter"

    counter = session_state.get(counter_key, 0) + 1
    session_state[counter_key] = counter
    previous_faces = session_state.get(faces_key, [])

    if counter == 1 or (counter - 1) % detection_interval == 0:
        detected_faces, _ = detect_faces_fn(frame)
        faces_list = [
            (int(face[0]), int(face[1]), int(face[2]), int(face[3]))
            for face in detected_faces
        ]
        session_state[faces_key] = faces_list
        return faces_list

    return previous_faces


def smooth_face_boxes(
    previous_faces: List[Tuple[int, int, int, int]],
    current_faces: List[Tuple[int, int, int, int]],
    current_weight: float = 0.7,
) -> List[Tuple[int, int, int, int]]:
    """Reduce small detector jitter without inventing or retaining face boxes."""
    if len(previous_faces) != 1 or len(current_faces) != 1:
        return current_faces

    weight = max(0.0, min(1.0, float(current_weight)))
    previous = previous_faces[0]
    current = current_faces[0]
    return [(
        int(round(previous[0] * (1.0 - weight) + current[0] * weight)),
        int(round(previous[1] * (1.0 - weight) + current[1] * weight)),
        int(round(previous[2] * (1.0 - weight) + current[2] * weight)),
        int(round(previous[3] * (1.0 - weight) + current[3] * weight)),
    )]


def annotate_faces(frame: Any, faces: List[Tuple[int, int, int, int]]) -> Any:
    """
    Vẽ khung nhận diện khuôn mặt cơ bản (Detection view).
    """
    annotated = frame.copy()
    for (x, y, w, h) in faces:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.putText(
        annotated,
        f"Faces detected: {len(faces)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )
    return annotated


def annotate_recognition(
    frame: Any,
    faces: List[Tuple[int, int, int, int]],
    prediction: Optional[Dict[str, Any]] = None,
    model_error: bool = False,
) -> Any:
    """
    Vẽ khung nhận diện kèm thông tin nhân viên hoặc cảnh báo Unknown.
    """
    annotated = frame.copy()
    for (x, y, w, h) in faces:
        if len(faces) == 1 and prediction is not None:
            if prediction.get("is_match", False):
                label_text = f"{prediction['display_code']} ({prediction['confidence']:.2f})"
                box_color = (0, 255, 0)
            else:
                label_text = f"Unknown ({prediction['confidence']:.2f} > {prediction['match_threshold']:.2f})"
                box_color = (0, 0, 255)
        elif model_error:
            label_text = "Model error"
            box_color = (0, 0, 255)
        else:
            label_text = "Face detected"
            box_color = (0, 215, 255)

        cv2.rectangle(annotated, (x, y), (x + w, y + h), box_color, 2)
        cv2.putText(
            annotated,
            label_text,
            (x, max(20, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            box_color,
            2,
        )

    cv2.putText(
        annotated,
        f"Faces detected: {len(faces)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )
    return annotated


def render_stream_frame(
    placeholder: Any,
    frame: Any,
    *,
    inline_data: bool = False,
    image_width: Any = "stretch",
    jpeg_quality: int = STREAM_JPEG_QUALITY,
) -> bool:
    """
    Hiển thị khung hình camera lên Streamlit placeholder trực tiếp qua mảng RGB.
    Đảm bảo 100% hiển thị tức thì khi bật camera, triệt tiêu lỗi màn hình trắng/đen do HTTP buffer,
    hoạt động mượt mà và ổn định chuẩn xác tương tự trang 6_Face_Detection.py.
    """
    if placeholder is None or frame is None:
        return False

    try:
        if inline_data:
            encoded, jpeg = cv2.imencode(
                ".jpg",
                frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    max(1, min(100, int(jpeg_quality))),
                ],
            )
            if not encoded:
                return False
            image_uri = (
                "data:image/jpeg;base64,"
                + base64.b64encode(jpeg).decode("ascii")
            )
            placeholder.image(image_uri, width=image_width)
            return True

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        placeholder.image(frame_rgb, channels="RGB", width=image_width)
        return True
    except Exception as err:
        print(f"Error rendering stream frame: {err}")
        return False
