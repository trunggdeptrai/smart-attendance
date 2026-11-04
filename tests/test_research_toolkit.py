"""Kiểm thử các thành phần bổ sung: phân loại, nhật ký nghiên cứu, sao lưu/khôi phục.

Dùng vector ngẫu nhiên tổng hợp (không phải dữ liệu khuôn mặt thật) để kiểm tra
LOGIC; không dùng để đánh giá độ chính xác nhận diện.
Tự cô lập dữ liệu nếu chạy riêng lẻ.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

if not os.environ.get("SMART_ATTENDANCE_DATA_ROOT"):
    os.environ["SMART_ATTENDANCE_DATA_ROOT"] = tempfile.mkdtemp(prefix="sa_research_test_")
os.environ["SMART_ATTENDANCE_RESEARCH_LOG"] = "1"  # chỉ ghi vào thư mục tạm
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from core import face_recognizer as fr  # noqa: E402
from core import paths  # noqa: E402

RNG = np.random.default_rng(42)


def _gallery():
    centers = {0: RNG.normal(size=128), 1: RNG.normal(size=128)}
    centers = {k: v / np.linalg.norm(v) for k, v in centers.items()}
    encodings, labels = [], []
    for label, center in centers.items():
        for _ in range(4):
            encodings.append(center + RNG.normal(scale=0.01, size=128))
            labels.append(label)
    label_to_code = {0: "HS901", 1: "HS902"}
    metadata = fr._build_model_metadata(np.array(encodings), labels, label_to_code, {"HS901": 4, "HS902": 4})
    return centers, np.array(encodings), labels, label_to_code, metadata


class ClassifyTests(unittest.TestCase):
    def test_paths_are_isolated(self):
        self.assertNotEqual(paths.DATA_ROOT, paths.PROJECT_ROOT)

    def test_weighted_knn_accepts_close_sample(self):
        centers, enc, labels, l2c, meta = _gallery()
        result = fr.classify_encoding(centers[0], enc, labels, l2c, meta)
        self.assertTrue(result["is_match"])
        self.assertEqual(result["display_code"], "HS901")
        self.assertEqual(result["reject_reason"], "")

    def test_weighted_knn_rejects_far_sample(self):
        _, enc, labels, l2c, meta = _gallery()
        stranger = RNG.normal(size=128)
        stranger = stranger / np.linalg.norm(stranger) * 3
        result = fr.classify_encoding(stranger, enc, labels, l2c, meta)
        self.assertFalse(result["is_match"])
        self.assertEqual(result["display_code"], "Unknown")
        self.assertEqual(result["reject_reason"], "above_threshold")

    def test_margin_gap_rejects_ambiguous_sample(self):
        centers, enc, labels, l2c, meta = _gallery()
        midpoint = (centers[0] + centers[1]) / 2
        result = fr.classify_encoding(midpoint, enc, labels, l2c, meta, threshold_override=5.0)
        self.assertFalse(result["is_match"])
        self.assertIn(result["reject_reason"], {"margin_gap", "no_majority"})

    def test_baseline_strategy_uses_fixed_threshold(self):
        centers, enc, labels, l2c, meta = _gallery()
        result = fr.classify_encoding(centers[1], enc, labels, l2c, meta, strategy=fr.STRATEGY_NEAREST_1NN)
        self.assertTrue(result["is_match"])
        self.assertEqual(result["match_threshold"], fr.BASELINE_TOLERANCE)

    def test_invalid_strategy(self):
        centers, enc, labels, l2c, meta = _gallery()
        with self.assertRaises(ValueError):
            fr.classify_encoding(centers[0], enc, labels, l2c, meta, strategy="abc")

    def test_low_contrast_image_rejected(self):
        flat = np.full((200, 200, 3), 128, dtype=np.uint8)
        encoding, reason = fr.encode_face_crop(flat)
        self.assertIsNone(encoding)
        self.assertEqual(reason, "low_contrast")


class ResearchLogTests(unittest.TestCase):
    def test_log_roundtrip(self):
        from core import research_log

        research_log.log_recognition_event(
            {"predicted_code": "HS901", "display_code": "HS901", "is_match": True,
             "confidence": 0.31, "match_threshold": 0.48, "latency_ms": 120.5},
            source="unit_test",
        )
        research_log.log_teacher_decision("unit_test", "confirm", "IN", "face", "HS901", "HS901", 0.31)
        events = research_log.read_log(research_log.RECOGNITION_LOG)
        decisions = research_log.read_log(research_log.DECISION_LOG)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events.iloc[-1]["predicted_code"], "HS901")
        self.assertEqual(decisions.iloc[-1]["action"], "confirm")


class BackupTests(unittest.TestCase):
    def test_backup_and_restore(self):
        import sqlite3

        from core import backup

        paths.DATA_ROOT.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(paths.DB_PATH)
        connection.execute("CREATE TABLE IF NOT EXISTS probe (value TEXT)")
        connection.execute("DELETE FROM probe")
        connection.execute("INSERT INTO probe VALUES ('truoc')")
        connection.commit()
        connection.close()
        face_dir = paths.FACES_DIR / "HS901"
        face_dir.mkdir(parents=True, exist_ok=True)
        (face_dir / "1.jpg").write_bytes(b"fake-image-bytes")

        zip_path = backup.create_backup()
        manifest = backup.verify_backup(zip_path)
        self.assertTrue(manifest["has_database"])
        self.assertGreaterEqual(manifest["face_files"], 1)

        connection = sqlite3.connect(paths.DB_PATH)
        connection.execute("UPDATE probe SET value='sau'")
        connection.commit()
        connection.close()
        (face_dir / "1.jpg").unlink()

        safety = backup.restore_backup(zip_path)
        self.assertTrue(Path(safety).exists())
        connection = sqlite3.connect(paths.DB_PATH)
        value = connection.execute("SELECT value FROM probe").fetchone()[0]
        connection.close()
        self.assertEqual(value, "truoc")
        self.assertTrue((face_dir / "1.jpg").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
