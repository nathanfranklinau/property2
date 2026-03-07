"""
Pool detection using a custom YOLO model trained on aerial imagery.

Detects swimming pools in satellite imagery. Pool detection runs on the
satellite_masked image (property boundary only, black outside) to avoid
false positives from neighbouring properties.

Custom pool model:
    The model must be a custom-trained YOLOv8 model for aerial pool detection.
    Copy it from the old project:
        ../realestateopportunities/identification-layer/models/pool_detection/best.pt
    or train a new one, then set YOLO_MODEL_PATH in data-layer/.env.

    yolov8s.pt (the standard COCO model) does NOT have a pool class and
    will always return 0 detections.

Download base YOLO weights (if training your own model):
    python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "./yolov8s.pt")

# Confidence threshold — detections below this are ignored
CONFIDENCE_THRESHOLD = 0.25

# Approximate m² per pixel at zoom level 20 for calibrating pool area.
# At ~-27° lat (Brisbane), a 640px image at zoom 20 covers ~45m → ~0.07m²/px
M2_PER_PIXEL = 0.07


def detect_pools(
    satellite_path: Path,
    lot_area_sqm: float,
    output_annotated_path: Path | None = None,
) -> dict:
    """
    Run YOLO pool detection on a (masked) satellite image.

    Args:
        satellite_path:         Path to the satellite image (ideally satellite_masked.jpg)
        lot_area_sqm:           Parcel area in m² (used for pixel→m² calibration)
        output_annotated_path:  If provided, save the satellite image with detection
                                bounding boxes drawn (yellow boxes + confidence labels)

    Returns:
        {
            "pool_count":  int,
            "pool_area_sqm": float,
            "detections": [{"bbox": [x1, y1, x2, y2], "confidence": float, "area_sqm": float}, ...]
        }
    """
    _empty = {"pool_count": 0, "pool_area_sqm": 0.0, "detections": []}

    if not Path(YOLO_MODEL_PATH).exists():
        log.warning(
            f"YOLO model not found at {YOLO_MODEL_PATH}. Pool detection skipped. "
            "Copy the custom pool model from the old project: "
            "../realestateopportunities/identification-layer/models/pool_detection/best.pt"
        )
        return _empty

    try:
        from ultralytics import YOLO
    except ImportError:
        log.warning("ultralytics not installed — pool detection skipped")
        return _empty

    model = YOLO(YOLO_MODEL_PATH)
    results = model(str(satellite_path), conf=CONFIDENCE_THRESHOLD, verbose=False)

    detections = []
    total_area = 0.0

    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox_area_px = (x2 - x1) * (y2 - y1)
            area_sqm = bbox_area_px * M2_PER_PIXEL

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": round(confidence, 3),
                "area_sqm": round(area_sqm, 1),
            })
            total_area += area_sqm

    # ── Save annotated image ───────────────────────────────────────────────
    if output_annotated_path and detections:
        _save_annotated(satellite_path, detections, output_annotated_path)

    log.info(f"Pool detection: {len(detections)} pool(s), ~{total_area:.1f}m² total")
    return {
        "pool_count": len(detections),
        "pool_area_sqm": round(total_area, 1),
        "detections": detections,
    }


def _save_annotated(
    satellite_path: Path,
    detections: list[dict],
    output_path: Path,
) -> None:
    """Draw detection bounding boxes on the satellite image and save as JPEG."""
    try:
        import cv2
    except ImportError:
        return

    img = cv2.imread(str(satellite_path))
    if img is None:
        return

    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
        conf = d["confidence"]
        # Yellow bounding box (matches old masked_raw_pool.jpg style)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        label = f"POOL {conf:.3f}"
        cv2.putText(img, label, (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Always save as JPEG
    out_path = str(output_path)
    if not out_path.lower().endswith(".jpg"):
        out_path = str(output_path.with_suffix(".jpg"))

    cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, 99])
    log.info(f"  pool annotated image saved: {Path(out_path).name}")
