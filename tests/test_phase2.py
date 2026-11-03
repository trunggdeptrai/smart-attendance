import sys
import os
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.face_detect import detect_faces
from core.face_recognizer import train_model, predict_face

def test_phase2():
    print("Testing train_model...")
    try:
        res = train_model()
        print(f"Train result: {res}")
    except Exception as e:
        print(f"Error in train_model: {e}")
        import traceback
        traceback.print_exc()
        return

    print("Testing detect_faces and predict_face with dummy image...")
    # Create a dummy image
    # Note: face_recognition will not find a face in random noise, so we'll just test if it doesn't crash
    dummy_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    try:
        faces, gray = detect_faces(dummy_img)
        print(f"Detected {len(faces)} faces in dummy image.")
    except Exception as e:
        print(f"Error in detect_faces: {e}")
        import traceback
        traceback.print_exc()

    try:
        # Create a dummy face crop
        dummy_face = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        pred = predict_face(dummy_face)
        print(f"Predict result: {pred}")
    except Exception as e:
        print(f"Error in predict_face: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_phase2()
