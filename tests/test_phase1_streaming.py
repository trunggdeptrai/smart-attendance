import base64
import time
import numpy as np
import cv2
from unittest.mock import patch
from core.camera_stream import (
    STREAM_FRAME_INTERVAL,
    STREAM_SLEEP_INTERVAL,
    ATTENDANCE_CAMERA_FRAME_INTERVAL,
    ATTENDANCE_PREVIEW_HEIGHT,
    ATTENDANCE_PREVIEW_WIDTH,
    REGISTER_FACE_FRAME_INTERVAL,
    RECOGNITION_COOLDOWN_SECONDS,
    RECOGNITION_UNKNOWN_RETRY_SECONDS,
    PredictionStore,
    render_stream_frame,
    read_camera_frame,
    ThreadedCameraReader,
    crop_frame_to_aspect_ratio,
    release_inactive_cameras,
    resize_frame_to_fit,
    smooth_face_boxes,
    translate_face_boxes_for_crop,
    update_detected_faces,
)
from core.face_detect import detect_faces
from core.live_camera import decode_camera_image


class StrictStreamlitMockPlaceholder:
    """
    MockPlaceholder mô phỏng chính xác chữ ký hàm st.image / DeltaGenerator.image của Streamlit.
    """
    def __init__(self):
        self.last_image = None
        self.last_channels = None
        self.last_width = None
        self.call_count = 0

    def image(
        self,
        image,
        caption=None,
        width="content",
        clamp=False,
        channels="RGB",
        output_format="auto",
        *,
        link=None,
    ):
        self.last_image = image
        self.last_channels = channels
        self.last_width = width
        self.call_count += 1


class MockCapture:
    def __init__(self, is_opened: bool = True):
        self._opened = is_opened
        self.grab_called = 0
        self.read_called = 0

    def isOpened(self) -> bool:
        return self._opened

    def grab(self) -> bool:
        self.grab_called += 1
        return True

    def read(self):
        self.read_called += 1
        return True, np.zeros((480, 640, 3), dtype=np.uint8)


def test_constants():
    print("1. Testing Stream & Recognition Constants...")
    assert STREAM_FRAME_INTERVAL <= 0.035, f"Interval too slow for 30 FPS: {STREAM_FRAME_INTERVAL}"
    assert STREAM_SLEEP_INTERVAL <= 0.015, f"Sleep too high: {STREAM_SLEEP_INTERVAL}"
    assert RECOGNITION_COOLDOWN_SECONDS >= 2.5, f"Cooldown too short: {RECOGNITION_COOLDOWN_SECONDS}"
    assert RECOGNITION_UNKNOWN_RETRY_SECONDS >= 1.0, f"Retry too short: {RECOGNITION_UNKNOWN_RETRY_SECONDS}"
    
    fps = 1.0 / STREAM_FRAME_INTERVAL
    print(f"  STREAM_FRAME_INTERVAL = {STREAM_FRAME_INTERVAL:.3f}s (~{fps:.1f} FPS) -> OK")
    print(f"  STREAM_SLEEP_INTERVAL = {STREAM_SLEEP_INTERVAL:.3f}s -> OK")
    print(f"  RECOGNITION_COOLDOWN_SECONDS = {RECOGNITION_COOLDOWN_SECONDS:.1f}s -> OK")
    print(f"  RECOGNITION_UNKNOWN_RETRY_SECONDS = {RECOGNITION_UNKNOWN_RETRY_SECONDS:.1f}s -> OK")


def test_render_stream_frame_rgb():
    print("\n2. Testing render_stream_frame Direct RGB Rendering...")
    placeholder = StrictStreamlitMockPlaceholder()

    # Guard checks
    assert render_stream_frame(None, np.zeros((10, 10, 3))) is False
    assert render_stream_frame(placeholder, None) is False
    assert placeholder.call_count == 0
    print("  Null input guards -> OK")

    # Valid BGR image rendering
    bgr_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bgr_frame[:, :, 0] = 255  # Blue channel in BGR
    
    t0 = time.perf_counter()
    success = render_stream_frame(placeholder, bgr_frame)
    render_time_ms = (time.perf_counter() - t0) * 1000

    assert success is True
    assert placeholder.call_count == 1
    assert isinstance(placeholder.last_image, np.ndarray), f"Expected ndarray, got {type(placeholder.last_image)}"
    assert placeholder.last_channels == "RGB"
    assert placeholder.last_width == "stretch"
    # Verify BGR -> RGB conversion happened (Blue channel in BGR becomes Red channel at index 2 in RGB)
    assert placeholder.last_image[0, 0, 2] == 255
    assert placeholder.last_image[0, 0, 0] == 0

    print(f"  Direct RGB render -> OK ({render_time_ms:.2f} ms, channels={placeholder.last_channels}, shape={placeholder.last_image.shape})")


def test_read_camera_frame_flushing():
    print("\n3. Testing read_camera_frame Windows DirectShow Buffer Flushing...")
    mock_cap = MockCapture(is_opened=True)
    
    ret, frame = read_camera_frame(mock_cap)
    assert ret is True
    assert frame is not None
    assert mock_cap.grab_called == 1, "Expected cap.grab() to be called to flush DirectShow stale frame"
    assert mock_cap.read_called == 1
    print("  DirectShow buffer flush (cap.grab) -> OK")


def test_render_stream_frame_inline_data_uri():
    print("\n4. Testing Inline JPEG Camera Frames...")
    placeholder = StrictStreamlitMockPlaceholder()
    bgr_frame = np.zeros((120, 160, 3), dtype=np.uint8)
    bgr_frame[:, :] = (10, 80, 220)

    assert render_stream_frame(placeholder, bgr_frame, inline_data=True) is True
    assert isinstance(placeholder.last_image, str)
    assert placeholder.last_image.startswith("data:image/jpeg;base64,")

    encoded = placeholder.last_image.partition(",")[2]
    decoded = cv2.imdecode(
        np.frombuffer(base64.b64decode(encoded), dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert decoded is not None
    assert decoded.shape == bgr_frame.shape
    assert np.allclose(decoded[60, 80], bgr_frame[60, 80], atol=8)
    print("  Inline frame renders without a Streamlit media-file URL -> OK")


def test_registration_stream_quality_and_cadence():
    print("\n4. Testing Camera Preview JPEG and Cadence...")
    placeholder = StrictStreamlitMockPlaceholder()
    frame = np.full((480, 640, 3), (35, 115, 205), dtype=np.uint8)
    with patch("core.camera_stream.cv2.imencode", wraps=cv2.imencode) as encode:
        assert render_stream_frame(
            placeholder,
            frame,
            inline_data=True,
            image_width="stretch",
        )
    assert encode.call_args.args[2] == [
        cv2.IMWRITE_JPEG_QUALITY,
        75,
    ]
    assert isinstance(placeholder.last_image, str)
    assert placeholder.last_width == "stretch"
    decoded = cv2.imdecode(
        np.frombuffer(
            base64.b64decode(placeholder.last_image.partition(",")[2]),
            dtype=np.uint8,
        ),
        cv2.IMREAD_COLOR,
    )
    assert decoded is not None
    assert np.allclose(decoded[240, 320], frame[240, 320], atol=8)
    assert REGISTER_FACE_FRAME_INTERVAL == ATTENDANCE_CAMERA_FRAME_INTERVAL
    print("  Camera preview uses the shared JPEG and update settings -> OK")


def test_attendance_preview_size_and_render_width():
    print("\n4. Testing Attendance Preview Size and Aspect Ratio...")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cropped, origin = crop_frame_to_aspect_ratio(frame)
    assert cropped.shape == (360, 640, 3)
    assert origin == (0, 60)
    preview = resize_frame_to_fit(
        cropped,
        max_width=ATTENDANCE_PREVIEW_WIDTH,
        max_height=ATTENDANCE_PREVIEW_HEIGHT,
    )
    assert preview.shape == (360, 640, 3)
    assert translate_face_boxes_for_crop([(100, 80, 120, 120)], origin) == [
        (100, 20, 120, 120)
    ]

    wide_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    wide_preview = resize_frame_to_fit(
        wide_frame,
        max_width=ATTENDANCE_PREVIEW_WIDTH,
        max_height=ATTENDANCE_PREVIEW_HEIGHT,
    )
    assert wide_preview.shape == (394, 700, 3)
    assert abs(wide_preview.shape[1] / wide_preview.shape[0] - 16 / 9) < 0.01

    placeholder = StrictStreamlitMockPlaceholder()
    assert render_stream_frame(
        placeholder,
        preview,
        inline_data=True,
        image_width=ATTENDANCE_PREVIEW_WIDTH,
    )
    assert placeholder.last_width == ATTENDANCE_PREVIEW_WIDTH
    assert ATTENDANCE_CAMERA_FRAME_INTERVAL == 1 / 30
    print("  Preview stays within 700x394 without stretching -> OK")


def test_face_detection_scaled_coordinates():
    print("\n5. Testing Face Detection Coordinate Scaling...")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    class MockCascade:
        def detectMultiScale(self, _gray, **kwargs):
            self.kwargs = kwargs
            return np.array([[75, 45, 90, 90]])

    cascade = MockCascade()
    with patch("core.face_detect.face_cascade", cascade):
        faces, gray = detect_faces(
            frame,
            processing_width=480,
            return_gray=False,
        )

    assert faces == [(100, 60, 120, 120)]
    assert gray is None
    assert cascade.kwargs["minSize"] == (45, 45)
    print("  Resized detector coordinates map back to source frame -> OK")


def test_smooth_face_boxes():
    print("\n6. Testing Detection Box Stabilization...")
    previous = [(100, 80, 120, 120)]
    current = [(110, 90, 130, 130)]
    assert smooth_face_boxes(previous, current) == [(107, 87, 127, 127)]
    assert smooth_face_boxes(previous, []) == []
    assert smooth_face_boxes([], current) == current
    print("  Small position jitter is smoothed; absent faces are not fabricated -> OK")


def test_registration_detection_cadence():
    print("\n7. Testing Registration Detection Cadence...")
    session_state = {}
    detection_calls = []

    def detect_faces_stub(_frame):
        detection_calls.append(1)
        return [(100, 80, 120, 120)], None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for _ in range(30):
        update_detected_faces(
            session_state,
            "registration_cadence_test",
            frame,
            detect_faces_stub,
            detection_interval=3,
        )

    assert len(detection_calls) == 10
    print("  Detection interval reuses boxes between scans -> OK")


def test_browser_camera_frame_decode():
    print("\n7. Testing Sampled Browser Camera Frame Decode...")
    frame = np.full((270, 480, 3), (30, 120, 210), dtype=np.uint8)
    encoded, jpeg = cv2.imencode(".jpg", frame)
    assert encoded
    image_data = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(
        "ascii"
    )
    decoded = decode_camera_image(image_data)
    assert decoded.shape == frame.shape
    assert np.allclose(decoded[135, 240], frame[135, 240], atol=8)

    try:
        decode_camera_image("invalid")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid sampled frame should raise ValueError")
    print("  Sampled JPEG frame decodes and malformed payload is rejected -> OK")


def test_release_inactive_camera_state():
    print("\n5. Testing Single Active Camera Page...")

    class MockCamera:
        def __init__(self):
            self.released = False

        def release(self):
            self.released = True

    active_camera = MockCamera()
    inactive_camera = MockCamera()
    session_state = {
        "attendance_cap": active_camera,
        "attendance_is_running": True,
        "attendance_stream_active": True,
        "register_face_cap": inactive_camera,
        "register_face_is_running": True,
        "register_face_stream_active": True,
    }

    release_inactive_cameras(session_state, "attendance")
    assert not active_camera.released
    assert inactive_camera.released
    assert session_state["attendance_is_running"] is True
    assert session_state["attendance_stream_active"] is True
    assert session_state["register_face_is_running"] is False
    assert session_state["register_face_stream_active"] is False
    print("  Inactive page camera is released and its state cleared -> OK")


def test_face_detection_interval():
    print("\n6. Testing Face Detection Interval...")
    session_state = {}
    detection_calls = []
    expected_faces = [(100, 80, 90, 90)]

    def detect_faces_stub(_frame):
        detection_calls.append(1)
        return expected_faces, None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = [
        update_detected_faces(
            session_state,
            "attendance_test",
            frame,
            detect_faces_stub,
            detection_interval=2,
        )
        for _ in range(6)
    ]

    assert len(detection_calls) == 3
    assert all(faces == expected_faces for faces in results)
    print("  Face boxes reused between detection passes -> OK")


def test_smart_recognition_coordinator():
    print("\n7. Testing Smart Recognition Coordinator (PredictionStore & Cooldown)...")
    store = PredictionStore()
    now = time.time()
    box1 = (100, 100, 80, 80)
    box2 = (110, 105, 80, 80)  # Minor head movement
    box3 = (300, 200, 90, 90)  # Major position jump

    # Step A: New face enters frame -> must trigger immediately
    assert store.can_trigger(now, box1) is True, "New face must trigger immediately"
    store.set_busy(True, now, box1)
    print("  Step A: Initial face appearance triggers recognition -> OK")

    # Step B: Worker is busy running Dlib -> can_trigger must return False
    assert store.can_trigger(now + 0.1, box1) is False, "Must not trigger while worker is busy"
    print("  Step B: Worker busy lock prevents redundant threads -> OK")

    # Step C: Worker finishes and matches NV001
    matched_pred = {
        "is_match": True,
        "employee_code": "NV001",
        "display_code": "NV001",
        "confidence": 0.42,
        "match_threshold": 0.50,
    }
    finish_time = now + 1.65
    store.set_prediction(matched_pred, finished_at=finish_time)
    
    pred, is_new, is_busy = store.get_prediction()
    assert pred is not None
    assert pred["employee_code"] == "NV001"
    assert is_new is True
    assert is_busy is False
    print("  Step C: Match result stored and retrieved -> OK")

    # Step D: During 3.0s cooldown, user moves face left/right
    # can_trigger MUST return False to keep Python GIL 100% free!
    assert store.can_trigger(finish_time + 0.5, box2) is False, "Must keep lock during head movement"
    assert store.can_trigger(finish_time + 1.5, box2) is False, "Must keep lock at t=1.5s"
    assert store.can_trigger(finish_time + 2.8, box2) is False, "Must keep lock at t=2.8s"
    
    # Verify cached prediction is STILL available for drawing green box at 30 FPS
    cached_pred, is_new2, _ = store.get_prediction()
    assert cached_pred is not None
    assert cached_pred["employee_code"] == "NV001"
    assert is_new2 is False, "Result already read, should not be marked new"
    print(f"  Step D: Cooldown {RECOGNITION_COOLDOWN_SECONDS}s holds lock & frees GIL during movement -> OK")

    # Step E: After 3.0s cooldown expires, periodic re-validation is allowed
    assert store.can_trigger(finish_time + 3.1, box2) is True, "Must allow re-check after 3.0s"
    print("  Step E: Cooldown expiration allows periodic re-check -> OK")

    # Step F: Stranger / Unknown Face handling
    unknown_pred = {
        "is_match": False,
        "employee_code": None,
        "display_code": "Unknown",
        "confidence": 0.68,
        "match_threshold": 0.50,
    }
    unk_time = finish_time + 3.5
    unk_finish = unk_time + 1.65
    store.set_busy(True, unk_time, box1)
    store.set_prediction(unknown_pred, finished_at=unk_finish)

    # Unknown face must NOT hammer GIL continuously: must wait at least 1.5s
    assert store.can_trigger(unk_finish + 0.5, box1) is False, "Unknown must wait retry interval"
    assert store.can_trigger(unk_finish + 1.6, box3) is True, "Unknown re-checks after 1.5s when moved"
    print("  Step F: Unknown retry throttling prevents continuous GIL choking -> OK")

    # Step G: Face leaves frame (empty count for 5 frames)
    for _ in range(4):
        still_valid = store.handle_faces_count(0)
        assert still_valid is True, "Grace period 1-4 frames must preserve state"
    
    # 5th frame without face -> clears prediction
    still_valid = store.handle_faces_count(0)
    assert still_valid is False, "5th empty frame must clear prediction"
    
    cleared_pred, _, _ = store.get_prediction()
    assert cleared_pred is None, "Prediction should be cleared after face leaves"
    
    # When next person appears, triggers immediately
    assert store.can_trigger(time.time(), box1) is True, "Next person triggers immediately"
    print("  Step G: Grace period and state clearing on face exit -> OK")


def test_prediction_store_rejects_stale_worker_results():
    print("\n7. Testing Stale Recognition Worker Cancellation...")
    store = PredictionStore()
    face_box = (80, 60, 120, 120)
    worker_generation = store.set_busy(True, time.time(), face_box)

    store.clear()
    assert store.get_prediction()[2] is True
    store.set_prediction(
        {"is_match": True, "display_code": "OLD"},
        generation=worker_generation,
    )
    prediction, _, is_busy = store.get_prediction()

    assert prediction is None
    assert not is_busy
    assert store.can_trigger(time.time(), face_box)
    print("  Cleared session ignores old result and releases worker lock -> OK")


def test_fps_simulation():
    print("\n8. Testing 30 FPS Local Render-Loop Simulation...")
    placeholder = StrictStreamlitMockPlaceholder()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    total_frames = 60
    start_time = time.perf_counter()
    next_frame_at = start_time
    for _ in range(total_frames):
        render_stream_frame(placeholder, frame)
        next_frame_at += STREAM_FRAME_INTERVAL
        delay = next_frame_at - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
    elapsed = time.perf_counter() - start_time
    
    sim_fps = total_frames / elapsed
    print(
        f"  Local renderer scheduled {total_frames} frames in {elapsed:.2f}s "
        f"-> {sim_fps:.1f} FPS; excludes network/browser -> OK"
    )
    assert sim_fps >= 25.0, f"Streaming simulation too slow: {sim_fps:.1f} FPS"


if __name__ == "__main__":
    test_constants()
    test_render_stream_frame_rgb()
    test_render_stream_frame_inline_data_uri()
    test_registration_stream_quality_and_cadence()
    test_attendance_preview_size_and_render_width()
    test_face_detection_scaled_coordinates()
    test_smooth_face_boxes()
    test_registration_detection_cadence()
    test_browser_camera_frame_decode()
    test_release_inactive_camera_state()
    test_read_camera_frame_flushing()
    test_face_detection_interval()
    test_smart_recognition_coordinator()
    test_prediction_store_rejects_stale_worker_results()
    test_fps_simulation()
    print("\n>>> ALL PHASE 1 ZERO-DELAY TESTS PASSED WITH 100% SUCCESS! <<<")
