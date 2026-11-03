import sys
import os
import time
import json
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cv2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.camera_stream import (
    STREAM_FRAME_INTERVAL,
    STREAM_SLEEP_INTERVAL,
    render_stream_frame,
    read_camera_frame,
    PredictionStore,
)
from db.database import initialize_database
from core import face_recognizer


def test_cached_encoding_matrix():
    print("0. Testing Cached Face Encoding Matrix...")
    with tempfile.TemporaryDirectory() as temp_dir:
        model_dir = Path(temp_dir)
        encodings_path = model_dir / "face_encodings.pkl"
        label_map_path = model_dir / "label_map.json"
        metadata_path = model_dir / "model_metadata.json"
        with encodings_path.open("wb") as file:
            pickle.dump(
                {"encodings": [[0.1] * 128], "labels": [0]},
                file,
            )
        with label_map_path.open("w", encoding="utf-8") as file:
            json.dump({"0": "HS001"}, file)

        with patch.object(face_recognizer, "ENCODINGS_PATH", encodings_path):
            with patch.object(face_recognizer, "LABEL_MAP_PATH", label_map_path):
                with patch.object(
                    face_recognizer,
                    "MODEL_METADATA_PATH",
                    metadata_path,
                ):
                    face_recognizer.clear_model_cache()
                    first_model = face_recognizer.load_model()
                    second_model = face_recognizer.load_model()
                    assert isinstance(first_model[0], np.ndarray)
                    assert first_model[0].shape == (1, 128)
                    assert first_model[0] is second_model[0]
                    face_recognizer.clear_model_cache()

    print("  Encodings loaded as a cached NumPy matrix -> PASSED!")


class StrictStreamlitMockPlaceholder:
    """
    MockPlaceholder mô phỏng chính xác 100% chữ ký hàm st.image / DeltaGenerator.image của Streamlit.
    Tuyệt đối không dùng **kwargs để phát hiện ngay bất kỳ lỗi tham số nào.
    """
    def __init__(self):
        self.call_count = 0
        self.last_image = None
        self.last_channels = None
        self.last_width = None

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
        self.call_count += 1
        self.last_image = image
        self.last_channels = channels
        self.last_width = width


class MockCameraDevice:
    def __init__(self):
        self.grab_count = 0
        self.read_count = 0

    def isOpened(self):
        return True

    def grab(self):
        self.grab_count += 1
        return True

    def read(self):
        self.read_count += 1
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, frame


def test_face_recognition_streaming_timing():
    print("1. Testing Face Recognition Direct RGB Streaming Timing (30 FPS)...")
    placeholder = StrictStreamlitMockPlaceholder()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Mô phỏng 1.0 giây streaming loop với STREAM_SLEEP_INTERVAL và STREAM_FRAME_INTERVAL
    start_time = time.time()
    last_video_time = 0.0
    iterations = 0

    while time.time() - start_time < 1.0:
        iterations += 1
        now = time.time()
        if now - last_video_time >= STREAM_FRAME_INTERVAL:
            success = render_stream_frame(placeholder, frame)
            assert success is True, "render_stream_frame failed"
            last_video_time = now
        time.sleep(STREAM_SLEEP_INTERVAL)

    fps = placeholder.call_count
    print(f"  Iterations in 1.0s: {iterations}")
    print(f"  Rendered frames in 1.0s: {fps} FPS")
    print(f"  Image channels: {placeholder.last_channels}, width: {placeholder.last_width}")

    # Xác thực tốc độ và định dạng RGB trực tiếp
    assert fps >= 22, f"FPS too low: {fps} FPS (expected >= 22 FPS)"
    assert placeholder.last_channels == "RGB", f"Expected channels='RGB', got {placeholder.last_channels}"
    assert placeholder.last_width == "stretch"
    assert isinstance(placeholder.last_image, np.ndarray), f"Expected ndarray image, got {type(placeholder.last_image)}"
    print("  Streaming rate matches 30 FPS target & Direct RGB image -> PASSED!")


def test_face_recognition_annotation_and_render():
    print("\n2. Testing Face Recognition Bounding Box Annotation and Direct RGB Rendering...")
    placeholder = StrictStreamlitMockPlaceholder()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Test Match Annotation (Xanh lá)
    faces_list = [(100, 100, 200, 200)]
    pred_match = {
        "display_code": "NV001",
        "predicted_code": "NV001",
        "confidence": 0.45,
        "match_threshold": 0.60,
        "is_match": True,
    }

    annotated = frame.copy()
    for (x, y, w, h) in faces_list:
        label = f"{pred_match['display_code']} ({pred_match['confidence']:.2f})"
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(annotated, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    t0 = time.perf_counter()
    success = render_stream_frame(placeholder, annotated)
    render_ms = (time.perf_counter() - t0) * 1000

    assert success is True
    assert placeholder.last_channels == "RGB"
    assert placeholder.last_width == "stretch"
    assert isinstance(placeholder.last_image, np.ndarray)
    print(f"  Rendered Match Frame: {render_ms:.2f}ms (Direct RGB) -> PASSED!")

    # 2. Test Unknown Annotation (Đỏ)
    pred_unknown = {
        "display_code": "Unknown",
        "predicted_code": "Unknown",
        "confidence": 0.75,
        "match_threshold": 0.60,
        "is_match": False,
    }
    annotated_unk = frame.copy()
    for (x, y, w, h) in faces_list:
        label = f"Unknown ({pred_unknown['confidence']:.2f})"
        cv2.rectangle(annotated_unk, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(annotated_unk, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    success_unk = render_stream_frame(placeholder, annotated_unk)
    assert success_unk is True
    assert placeholder.last_channels == "RGB"
    print("  Rendered Unknown Frame -> PASSED!")

    # 3. Test Multiple Faces Annotation (Cam)
    faces_multi = [(100, 100, 150, 150), (300, 100, 150, 150)]
    annotated_multi = frame.copy()
    for (x, y, w, h) in faces_multi:
        label = f"Multiple faces ({len(faces_multi)})"
        cv2.rectangle(annotated_multi, (x, y), (x + w, y + h), (0, 165, 255), 2)
        cv2.putText(annotated_multi, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    success_multi = render_stream_frame(placeholder, annotated_multi)
    assert success_multi is True
    print("  Rendered Multiple Faces Frame -> PASSED!")


def test_face_recognition_directshow_flush():
    print("\n3. Testing Face Recognition Camera Buffer Flushing...")
    mock_cam = MockCameraDevice()
    ret, frame = read_camera_frame(mock_cam)
    assert ret is True
    assert frame is not None
    assert mock_cam.grab_count == 1, "Must call cap.grab() to flush buffer"
    assert mock_cam.read_count == 1, "Must call cap.read() to get latest frame"
    print("  DirectShow frame buffer flush -> PASSED!")


def test_both_pages_syntax_and_import():
    print("\n4. Testing Syntax and Compilation Integrity of Both Target Pages...")
    for page_path in ["pages/4_Attendance.py", "pages/7_Face_Recognition.py"]:
        with open(page_path, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, page_path, "exec")
        print(f"  Compiled successfully: {page_path} -> OK")


if __name__ == "__main__":
    test_cached_encoding_matrix()
    test_face_recognition_streaming_timing()
    test_face_recognition_annotation_and_render()
    test_face_recognition_directshow_flush()
    test_both_pages_syntax_and_import()
    print("\n>>> ALL PHASE 3 FACE RECOGNITION INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
