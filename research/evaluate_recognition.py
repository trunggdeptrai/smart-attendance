"""Đánh giá offline độ chính xác và thời gian xử lý của mô-đun nhận diện.

Công cụ này KHÔNG tạo số liệu: mọi chỉ số được tính từ ảnh kiểm thử thật do
nhóm nghiên cứu thu thập (có phiếu đồng ý IVd) hoặc từ ảnh mẫu đã đăng ký.

Hai chế độ:

1) --eval-dir: tập ảnh kiểm thử độc lập (KHÔNG trùng ảnh huấn luyện)
   Cấu trúc thư mục (một trong hai):
     <eval_dir>/<mã_học_sinh>/*.jpg                    -> điều kiện "default"
     <eval_dir>/<điều_kiện>/<mã_học_sinh>/*.jpg        -> vd: sang/, toi/, nghieng30/
   Người KHÔNG có trong mô hình (kiểm tra nhận nhầm): đặt thư mục mã bắt đầu bằng
   "NGOAI" (vd: NGOAI01). Hệ thống đúng khi trả về Unknown cho các ảnh này.
   Tuỳ chọn --manifest CSV (cột: file, true_code, condition) để ghi đè.

2) --loo: kiểm định chéo "bỏ ra một" (leave-one-out) trên chính ảnh mẫu đã đăng ký
   (data/faces). Mỗi ảnh lần lượt bị loại khỏi thư viện, ngưỡng riêng được
   hiệu chỉnh lại không có ảnh đó, rồi phân loại ảnh đó. Học sinh chỉ có 1 ảnh
   trở thành "người lạ" (kiểm tra khả năng từ chối).

So sánh các cấu hình (cùng một vector đặc trưng đầu vào):
  - baseline_1nn_t0.60 : láng giềng gần nhất + ngưỡng cố định 0.6 (cách dùng phổ biến
                         của thư viện face_recognition) — NHÓM ĐỐI CHỨNG
  - app_weighted_knn   : thuật toán hiện tại của ứng dụng (K-NN có trọng số, ngưỡng
                         riêng từng học sinh, kiểm tra khoảng cách biên, đa số phiếu)
  - app_weighted_knn_hog: như trên nhưng dò lại khuôn mặt bằng HOG trước khi mã hóa

Kết quả ghi vào research_results/<thời_điểm>/:
  per_image.csv, summary.csv, threshold_sweep.csv, run_info.json

Ví dụ:
  python -m research.evaluate_recognition --loo
  python -m research.evaluate_recognition --eval-dir D:/anh_kiem_thu
"""

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import face_recognizer as fr  # noqa: E402
from core.face_detect import detect_faces  # noqa: E402
from core.paths import FACES_DIR, RESEARCH_RESULT_DIR  # noqa: E402
from core.save_face import crop_and_resize_face  # noqa: E402

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
IMPOSTOR_PREFIX = "NGOAI"

CONFIGS = [
    {"name": "baseline_1nn_t0.60", "strategy": fr.STRATEGY_NEAREST_1NN, "locate": "full_crop", "threshold": 0.60},
    {"name": "app_weighted_knn", "strategy": fr.STRATEGY_WEIGHTED_KNN, "locate": "full_crop", "threshold": None},
    {"name": "app_weighted_knn_hog", "strategy": fr.STRATEGY_WEIGHTED_KNN, "locate": "hog_redetect", "threshold": None},
]
SWEEP_THRESHOLDS = [round(0.30 + 0.02 * i, 2) for i in range(21)]  # 0.30 -> 0.70


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect_eval_images(eval_dir, manifest=None):
    eval_dir = Path(eval_dir)
    items = []
    if manifest:
        with open(manifest, encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                items.append({
                    "file": str((eval_dir / row["file"]).resolve()),
                    "true_code": row["true_code"].strip(),
                    "condition": (row.get("condition") or "default").strip(),
                })
        return items

    def images_in(folder):
        return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)

    for first in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
        direct = images_in(first)
        if direct:  # <eval>/<code>/*.jpg
            items += [{"file": str(p), "true_code": first.name, "condition": "default"} for p in direct]
            continue
        for code_dir in sorted(p for p in first.iterdir() if p.is_dir()):  # <eval>/<cond>/<code>/*.jpg
            items += [{"file": str(p), "true_code": code_dir.name, "condition": first.name} for p in images_in(code_dir)]
    return items


def largest_face(faces):
    return max(faces, key=lambda box: box[2] * box[3])


def prepare_crop(image_path):
    """Đọc ảnh -> phát hiện khuôn mặt (Haar, như ứng dụng) -> cắt. Trả về (crop, info)."""
    image = cv2.imread(str(image_path))
    if image is None:
        return None, {"status": "unreadable", "faces_detected": 0, "detect_ms": 0.0}
    started = time.perf_counter()
    faces, _ = detect_faces(image, return_gray=False)
    detect_ms = (time.perf_counter() - started) * 1000
    info = {
        "status": "ok" if faces else "no_face",
        "faces_detected": len(faces),
        "detect_ms": round(detect_ms, 2),
        "image_w": image.shape[1],
        "image_h": image.shape[0],
        "mean_brightness": round(float(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).mean()), 1),
    }
    if not faces:
        return None, info
    box = largest_face(faces)
    info["face_w"] = int(box[2])
    info["face_h"] = int(box[3])
    return crop_and_resize_face(image, box), info


def outcome(true_code, known_codes, result):
    """Phân loại kết quả theo chuẩn đánh giá nhận dạng tập mở (open-set)."""
    genuine = true_code in known_codes
    if result["is_match"]:
        if genuine and result["display_code"] == true_code:
            return "correct_accept"
        return "wrong_accept" if genuine else "false_accept"
    return "false_reject" if genuine else "correct_reject"


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["config"], row["condition"])].append(row)
        groups[(row["config"], "TẤT CẢ")].append(row)
    summary = []
    for (config, condition), items in sorted(groups.items()):
        counts = defaultdict(int)
        for item in items:
            counts[item["outcome"]] += 1
        genuine = counts["correct_accept"] + counts["wrong_accept"] + counts["false_reject"] + counts["no_face_genuine"]
        impostor = counts["false_accept"] + counts["correct_reject"] + counts["no_face_impostor"]
        total = len(items)
        latencies = [item["encode_classify_ms"] for item in items if item["encode_classify_ms"] != ""]

        def rate(numerator, denominator):
            return round(numerator / denominator, 4) if denominator else ""

        summary.append({
            "config": config,
            "condition": condition,
            "n_images": total,
            "n_genuine": genuine,
            "n_impostor": impostor,
            "correct_accept": counts["correct_accept"],
            "wrong_accept": counts["wrong_accept"],
            "false_reject": counts["false_reject"],
            "false_accept": counts["false_accept"],
            "correct_reject": counts["correct_reject"],
            "no_face": counts["no_face_genuine"] + counts["no_face_impostor"],
            "accuracy": rate(counts["correct_accept"] + counts["correct_reject"], total),
            "identification_rate": rate(counts["correct_accept"], genuine),
            "misidentification_rate": rate(counts["wrong_accept"], genuine),
            "false_reject_rate": rate(counts["false_reject"] + counts["no_face_genuine"], genuine),
            "false_accept_rate": rate(counts["false_accept"], impostor),
            "mean_encode_classify_ms": round(float(np.mean(latencies)), 2) if latencies else "",
            "median_encode_classify_ms": round(float(np.median(latencies)), 2) if latencies else "",
        })
    return summary


def threshold_sweep(samples, gallery_fn):
    """samples: list of (true_code, encoding, sample_index). Quét ngưỡng cho 1-NN."""
    rows = []
    for threshold in SWEEP_THRESHOLDS:
        counts = defaultdict(int)
        for true_code, encoding, index in samples:
            encs, labels, label_to_code, metadata = gallery_fn(index)
            known = set(label_to_code.values())
            result = fr.classify_encoding(
                encoding, encs, labels, label_to_code, metadata,
                strategy=fr.STRATEGY_NEAREST_1NN, threshold_override=threshold,
            )
            counts[outcome(true_code, known, result)] += 1
            counts["genuine" if true_code in known else "impostor"] += 1
        total = counts["genuine"] + counts["impostor"]
        rows.append({
            "threshold": threshold,
            "n": total,
            "accuracy": round((counts["correct_accept"] + counts["correct_reject"]) / total, 4) if total else "",
            "identification_rate": round(counts["correct_accept"] / counts["genuine"], 4) if counts["genuine"] else "",
            "false_reject_rate": round(counts["false_reject"] / counts["genuine"], 4) if counts["genuine"] else "",
            "misidentification_rate": round(counts["wrong_accept"] / counts["genuine"], 4) if counts["genuine"] else "",
            "false_accept_rate": round(counts["false_accept"] / counts["impostor"], 4) if counts["impostor"] else "",
        })
    return rows


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_eval_dir(args):
    items = collect_eval_images(args.eval_dir, args.manifest)
    if not items:
        raise SystemExit("Không tìm thấy ảnh kiểm thử trong thư mục đã chọn.")
    known_encodings, known_labels, label_to_code, metadata = fr.load_model()
    known_codes = set(label_to_code.values())

    training_hashes = {sha256_file(p) for p in FACES_DIR.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS}
    overlap = [item["file"] for item in items if sha256_file(item["file"]) in training_hashes]
    if overlap and not args.allow_overlap:
        raise SystemExit(
            f"{len(overlap)} ảnh kiểm thử TRÙNG với ảnh huấn luyện -> kết quả sẽ sai lệch. "
            "Loại bỏ các ảnh này hoặc dùng --allow-overlap (không khuyến nghị)."
        )

    rows = []
    sweep_samples = []
    for index, item in enumerate(items):
        crop, info = prepare_crop(item["file"])
        is_genuine = item["true_code"] in known_codes
        encodings_by_mode = {}
        for config in CONFIGS:
            base = {
                "file": Path(item["file"]).name,
                "true_code": item["true_code"],
                "condition": item["condition"],
                "config": config["name"],
                **info,
            }
            if crop is None:
                rows.append({**base, "outcome": "no_face_genuine" if is_genuine else "no_face_impostor",
                             "predicted_code": "", "distance": "", "threshold": "", "reject_reason": info["status"],
                             "encode_classify_ms": ""})
                continue
            if config["locate"] not in encodings_by_mode:
                enc_started = time.perf_counter()
                encoded = fr.encode_face_crop(crop, locate_mode=config["locate"])
                encodings_by_mode[config["locate"]] = (*encoded, (time.perf_counter() - enc_started) * 1000)
            encoding, reason, encode_ms = encodings_by_mode[config["locate"]]
            started = time.perf_counter()
            if encoding is None:
                result = fr._unknown_result(reason=reason)
            else:
                result = fr.classify_encoding(
                    encoding, known_encodings, known_labels, label_to_code, metadata,
                    strategy=config["strategy"], threshold_override=config["threshold"],
                )
            elapsed = encode_ms + (time.perf_counter() - started) * 1000
            rows.append({**base, "outcome": outcome(item["true_code"], known_codes, result),
                         "predicted_code": result["predicted_code"], "distance": round(float(result["confidence"]), 4),
                         "threshold": round(float(result["match_threshold"]), 4),
                         "reject_reason": result.get("reject_reason", ""), "encode_classify_ms": round(elapsed, 2)})
        full = encodings_by_mode.get("full_crop")
        if full and full[0] is not None:
            sweep_samples.append((item["true_code"], full[0], index))

    sweep = threshold_sweep(sweep_samples, lambda _i: (known_encodings, known_labels, label_to_code, metadata))
    return rows, sweep, {"mode": "eval_dir", "n_items": len(items), "training_overlap": len(overlap)}


def run_loo(args):
    from core.face_dataset import load_training_data

    encodings, labels, label_to_code, _ = load_training_data()
    if len(encodings) < 2:
        raise SystemExit("Cần ít nhất 2 ảnh mẫu đã đăng ký để chạy leave-one-out.")
    encodings = np.asarray(encodings)
    labels = np.asarray(labels)

    def gallery_without(index):
        mask = np.arange(len(encodings)) != index
        g_enc, g_lab = encodings[mask], labels[mask]
        present = sorted(set(g_lab.tolist()))
        g_map = {lbl: label_to_code[lbl] for lbl in present}
        counts = {code: int((g_lab == lbl).sum()) for lbl, code in g_map.items()}
        metadata = fr._build_model_metadata(g_enc, g_lab.tolist(), g_map, counts)
        return g_enc, g_lab.tolist(), g_map, metadata

    rows, sweep_samples = [], []
    for index in range(len(encodings)):
        true_code = label_to_code[int(labels[index])]
        g_enc, g_lab, g_map, metadata = gallery_without(index)
        known = set(g_map.values())
        for config in CONFIGS:
            if config["locate"] != "full_crop":
                continue  # LOO dùng vector đã mã hóa khi huấn luyện
            started = time.perf_counter()
            result = fr.classify_encoding(encodings[index], g_enc, g_lab, g_map, metadata,
                                          strategy=config["strategy"], threshold_override=config["threshold"])
            elapsed = (time.perf_counter() - started) * 1000
            rows.append({"file": f"sample_{index}", "true_code": true_code, "condition": "loo",
                         "config": config["name"], "outcome": outcome(true_code, known, result),
                         "predicted_code": result["predicted_code"], "distance": round(float(result["confidence"]), 4),
                         "threshold": round(float(result["match_threshold"]), 4),
                         "reject_reason": result.get("reject_reason", ""), "encode_classify_ms": round(elapsed, 3)})
        sweep_samples.append((true_code, encodings[index], index))

    sweep = threshold_sweep(sweep_samples, gallery_without)
    return rows, sweep, {"mode": "leave_one_out", "n_samples": int(len(encodings)),
                         "n_people": len(label_to_code),
                         "note": "Chỉ so sánh bước phân loại; vector lấy từ bước huấn luyện (dò HOG)."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--eval-dir", help="Thư mục ảnh kiểm thử độc lập")
    mode.add_argument("--loo", action="store_true", help="Leave-one-out trên ảnh mẫu đã đăng ký")
    parser.add_argument("--manifest", help="CSV: file,true_code,condition (tuỳ chọn)")
    parser.add_argument("--allow-overlap", action="store_true", help="Cho phép ảnh kiểm thử trùng ảnh huấn luyện")
    parser.add_argument("--output-dir", default=str(RESEARCH_RESULT_DIR))
    parser.add_argument("--tag", default="", help="Nhãn ngắn cho lần chạy, vd: lop_demo_lan1")
    args = parser.parse_args(argv)

    started = datetime.now()
    rows, sweep, info = run_loo(args) if args.loo else run_eval_dir(args)
    summary = summarize(rows)

    run_name = started.strftime("%Y%m%d-%H%M%S") + (f"_{args.tag}" if args.tag else "")
    out_dir = Path(args.output_dir) / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "per_image.csv", rows)
    write_csv(out_dir / "summary.csv", summary)
    write_csv(out_dir / "threshold_sweep.csv", sweep)

    import dlib
    import face_recognition
    run_info = {
        **info,
        "started_at": started.isoformat(timespec="seconds"),
        "duration_s": round((datetime.now() - started).total_seconds(), 1),
        "args": vars(args),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "opencv": cv2.__version__,
        "dlib": dlib.__version__,
        "face_recognition": getattr(face_recognition, "__version__", "unknown"),
        "configs": CONFIGS,
        "app_constants": {
            "DEFAULT_MATCH_THRESHOLD": fr.DEFAULT_MATCH_THRESHOLD,
            "STRICT_MATCH_THRESHOLD": fr.STRICT_MATCH_THRESHOLD,
            "KNN_K": fr.KNN_K,
            "MARGIN_GAP_THRESHOLD": fr.MARGIN_GAP_THRESHOLD,
        },
    }
    (out_dir / "run_info.json").write_text(json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Đã ghi kết quả vào: {out_dir}")
    for row in summary:
        if row["condition"] == "TẤT CẢ":
            print(f"  {row['config']:<24} n={row['n_images']:<4} accuracy={row['accuracy']} "
                  f"FRR={row['false_reject_rate']} FAR={row['false_accept_rate']} "
                  f"nhầm={row['misidentification_rate']}")
    return out_dir


if __name__ == "__main__":
    main()
