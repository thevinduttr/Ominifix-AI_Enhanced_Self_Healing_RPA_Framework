# scripts/evaluate_vision.py
"""
Vision Strategy Evaluation (OpenCV Template Matching)

Evaluates template presence in screenshots using:
- Edge-based matching (Canny) for higher precision
- Per-template thresholds for better control

Folder conventions:
- Full screenshots:  data/raw/screenshots/full/*.png
- Templates:         data/raw/screenshots/templates/*.png

Run:
    python scripts/evaluate_vision.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import cv2


FULL_DIR = Path("data/raw/screenshots/full")
TEMPLATE_DIR = Path("data/raw/screenshots/templates")

# Edge detection parameters
CANNY_LOW = 50
CANNY_HIGH = 150

# Default threshold (used if template name not in THRESHOLDS)
DEFAULT_THRESHOLD = 0.70

# Tuned thresholds based on your current score distribution
THRESHOLDS: Dict[str, float] = {
    "checkbox.png": 0.85,
    "login_button.png": 0.55,        # lower to allow style/text change cases
    "dropdown_select.png": 0.65,     # dropdown edges match slightly lower
    "add_button.png": 0.74,
    "delete.png": 0.78,
}


def _load_edges(image_path: Path) -> Optional["cv2.Mat"]:
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None
    return cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)


def template_match_score(screenshot_path: Path, template_path: Path) -> Optional[float]:
    """
    Returns best match score in [0, 1] using normalized cross-correlation on edges.
    """
    screenshot = _load_edges(screenshot_path)
    template = _load_edges(template_path)

    if screenshot is None or template is None:
        return None

    if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
        return None

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, _max_loc = cv2.minMaxLoc(result)

    return float(max(0.0, min(1.0, max_val)))


def evaluate() -> List[dict]:
    if not FULL_DIR.exists():
        raise SystemExit(f"Missing folder: {FULL_DIR}")
    if not TEMPLATE_DIR.exists():
        raise SystemExit(f"Missing folder: {TEMPLATE_DIR}")

    full_images = sorted(FULL_DIR.glob("*.png"))
    templates = sorted(TEMPLATE_DIR.glob("*.png"))

    if not full_images:
        raise SystemExit(f"No PNG screenshots found in: {FULL_DIR}")
    if not templates:
        raise SystemExit(f"No PNG templates found in: {TEMPLATE_DIR}")

    print("\n=== Vision Strategy Evaluation (Edge-based Template Matching) ===\n")
    print(f"Full screenshots dir    : {FULL_DIR}")
    print(f"Templates dir           : {TEMPLATE_DIR}")
    print(f"Default threshold       : {DEFAULT_THRESHOLD}")
    print(f"Per-template thresholds : {THRESHOLDS}")
    print(f"Canny params            : low={CANNY_LOW}, high={CANNY_HIGH}\n")

    rows: List[dict] = []

    for full_img in full_images:
        for tpl in templates:
            score = template_match_score(full_img, tpl)
            if score is None:
                continue

            thr = THRESHOLDS.get(tpl.name, DEFAULT_THRESHOLD)
            detected = score >= thr

            row = {
                "screenshot": full_img.name,
                "template": tpl.name,
                "score": round(score, 4),
                "threshold": thr,
                "detected": detected,
            }
            rows.append(row)

    # Print sorted by screenshot then score desc
    rows_sorted = sorted(rows, key=lambda r: (r["screenshot"], -r["score"]))

    for r in rows_sorted:
        print(
            f"{r['screenshot']:<28} | {r['template']:<20} | "
            f"Score: {r['score']:.4f} | Thr: {r['threshold']:.2f} | "
            f"Detected: {str(r['detected']):<5}"
        )

    return rows_sorted


if __name__ == "__main__":
    evaluate()