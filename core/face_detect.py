import cv2
import os

MAX_PROCESSING_WIDTH = 640
MIN_FACE_SIZE = (60, 60)

# Initialize Haar Cascade classifier
cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)

def detect_faces(
    frame,
    processing_width=MAX_PROCESSING_WIDTH,
    return_gray=True,
):
    """
    Detect faces using OpenCV Haar Cascade.
    Haar Cascade is significantly faster on CPU than dlib HOG, preventing WebRTC frame drops and freezing.
    It is also much more robust to large/close-up faces where HOG often fails.
    Returns face locations in (x, y, w, h) format.
    """
    height, width = frame.shape[:2]
    
    processing_width = max(1, int(processing_width))
    scale = min(1.0, processing_width / width)
    
    if scale != 1.0:
        resized_width = max(1, int(width * scale))
        resized_height = max(1, int(height * scale))
        process_frame = cv2.resize(frame, (resized_width, resized_height))
    else:
        process_frame = frame

    gray = cv2.cvtColor(process_frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(
            max(1, int(round(MIN_FACE_SIZE[0] * scale))),
            max(1, int(round(MIN_FACE_SIZE[1] * scale))),
        ),
    )

    scaled_faces = []
    for (x, y, w, h) in faces:
        if scale != 1.0:
            orig_x = int(x / scale)
            orig_y = int(y / scale)
            orig_w = int(w / scale)
            orig_h = int(h / scale)
        else:
            orig_x, orig_y, orig_w, orig_h = x, y, w, h
            
        scaled_faces.append((orig_x, orig_y, orig_w, orig_h))

    full_gray = None
    if return_gray:
        full_gray = gray if scale == 1.0 else cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )
    return scaled_faces, full_gray
