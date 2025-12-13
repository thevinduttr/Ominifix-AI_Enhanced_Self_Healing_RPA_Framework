import cv2
import numpy as np


def load_images(page_screenshot_path: str, template_path: str):
    page = cv2.imread(page_screenshot_path)
    tmpl = cv2.imread(template_path)
    if page is None or tmpl is None:
        return None, None
    return page, tmpl


def find_template_orb(page, template):
    orb = cv2.ORB_create()

    kp1, des1 = orb.detectAndCompute(template, None)
    kp2, des2 = orb.detectAndCompute(page, None)

    if des1 is None or des2 is None:
        return None, 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    if len(matches) == 0:
        return None, 0.0

    # sort by quality
    matches = sorted(matches, key=lambda x: x.distance)
    good = matches[: min(30, len(matches))]

    pts = np.float32([kp2[m.trainIdx].pt for m in good])
    x, y = np.mean(pts, axis=0)

    similarity = len(good) / len(matches)
    return (float(x), float(y)), float(similarity)


def estimate_element_screen_distance(candidate_bbox_center, template_center):
    # candidate_bbox_center: (cx, cy)
    # template_center: (x, y)
    cx, cy = candidate_bbox_center
    tx, ty = template_center
    dx = cx - tx
    dy = cy - ty
    dist = np.sqrt(dx * dx + dy * dy)
    return float(dist)
