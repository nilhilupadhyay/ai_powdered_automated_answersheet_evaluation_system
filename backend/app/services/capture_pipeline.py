from pathlib import Path
import base64
import re

import cv2
import numpy as np
import requests

from app.core.config import settings


def decode_qr_payload(image_path: str) -> str | None:
    image = cv2.imread(image_path)
    if image is None:
        return None

    detector = cv2.QRCodeDetector()
    decoded_text, _, _ = detector.detectAndDecode(image)
    if decoded_text:
        return decoded_text
    return None


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def align_document(image_path: str) -> None:
    image = cv2.imread(image_path)
    if image is None:
        return
    
    orig = image.copy()
    ratio = image.shape[0] / 500.0
    image = cv2.resize(image, (int(image.shape[1] / ratio), 500))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    screen_cnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screen_cnt = approx
            break

    if screen_cnt is not None:
        pts = screen_cnt.reshape(4, 2) * ratio
        rect = order_points(pts)
        (tl, tr, br, bl) = rect

        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (max_width, max_height))
        cv2.imwrite(image_path, warped)


def extract_roll_number(image_path: str) -> tuple[str | None, float]:
    if settings.ocr_provider == "google_vision":
        roll_number, confidence = extract_roll_number_google_vision(image_path)
        if roll_number:
            return roll_number, confidence
    return extract_roll_number_local_fallback(image_path)


def extract_roll_number_google_vision(image_path: str) -> tuple[str | None, float]:
    if not settings.google_vision_api_key:
        return None, 0.0

    file_bytes = Path(image_path).read_bytes()
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(file_bytes).decode("utf-8")},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }
    endpoint = (
        "https://vision.googleapis.com/v1/images:annotate"
        f"?key={settings.google_vision_api_key}"
    )
    response = requests.post(endpoint, json=payload, timeout=20)
    if response.status_code != 200:
        return None, 0.0

    data = response.json()
    annotations = data.get("responses", [{}])[0].get("textAnnotations", [])
    if not annotations:
        return None, 0.0

    full_text = annotations[0].get("description", "")
    match = re.search(r"\b([A-Za-z0-9]{4,20})\b", full_text)
    if not match:
        return None, 0.0
    return match.group(1), 0.85


def extract_roll_number_local_fallback(image_path: str) -> tuple[str | None, float]:
    # Local fallback keeps pipeline functional without cloud credentials.
    # If filename contains roll-like token, we use it for testing/dev.
    stem = Path(image_path).stem
    match = re.search(r"roll[-_]?([A-Za-z0-9]{3,20})", stem, re.IGNORECASE)
    if not match:
        return None, 0.0
    return match.group(1), 0.5


def ensure_uploads_dir() -> Path:
    upload_dir = Path(settings.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir
