from pathlib import Path
import base64
import re

import cv2
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
