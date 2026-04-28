"""
OpenCV Face Recognition Service — wraps Haar Cascades + LBPH.

Extracted from legacy/frs_0.0.0.3.py. Keeps the same LBPH algorithm
and confidence threshold but exposes it via clean function calls
instead of Tkinter callbacks.
"""
import os
import base64
import logging
import numpy as np
import cv2 as cv
from typing import Optional

from database import SAMPLES_DIR, ensure_dirs

logger = logging.getLogger(__name__)

# ── Haar Cascade Detector ───────────────────────────────────────
try:
    CASC_PATH = cv.data.haarcascades + "haarcascade_frontalface_default.xml"
except AttributeError:
    CASC_PATH = "haarcascade_frontalface_default.xml"

face_cascade = cv.CascadeClassifier(CASC_PATH)

# ── LBPH Recognizer ─────────────────────────────────────────────
recognizer = cv.face.LBPHFaceRecognizer_create()

# Confidence threshold (lower = stricter). Same as legacy code.
CONFIDENCE_THRESHOLD = 70

# Mapping from LBPH label index → membership_id
_label_to_id: list[str] = []


def decode_base64_image(b64_string: str) -> np.ndarray:
    """Decode a base64-encoded image string to an OpenCV BGR numpy array."""
    # Strip data URI prefix if present (e.g. "data:image/jpeg;base64,...")
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]

    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv.imdecode(nparr, cv.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image from base64 data")
    return img


def detect_face(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detect a single face in the image and return the grayscale ROI.
    Returns None if no face or multiple faces detected.
    """
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )

    if len(faces) != 1:
        logger.info("Expected 1 face, found %d", len(faces))
        return None

    x, y, w, h = faces[0]
    return gray[y : y + h, x : x + w]


def save_face_sample(membership_id: str, face_roi: np.ndarray) -> str:
    """Save a grayscale face ROI to disk. Returns the file path."""
    ensure_dirs()
    path = os.path.join(SAMPLES_DIR, f"{membership_id}.png")
    cv.imwrite(path, face_roi)
    logger.info("Saved face sample: %s", path)
    return path


def train_model() -> list[str]:
    """
    Re-train the LBPH recognizer from all saved face samples.
    Returns the ordered list of membership IDs (label → id mapping).
    """
    global _label_to_id, recognizer

    ensure_dirs()
    images = [
        os.path.join(SAMPLES_DIR, f)
        for f in os.listdir(SAMPLES_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    ids: list[str] = []
    faces: list[np.ndarray] = []
    labels: list[int] = []

    for idx, img_path in enumerate(images):
        img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
        if img is None:
            continue
        faces.append(img)
        labels.append(idx)
        member_id = os.path.splitext(os.path.basename(img_path))[0]
        ids.append(member_id)

    if faces:
        # Re-create recognizer to avoid stale state
        recognizer = cv.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(labels))
        logger.info("Trained LBPH model with %d samples", len(faces))
    else:
        logger.warning("No face samples found — model is empty")

    _label_to_id = ids
    return ids


def recognize_face(face_roi: np.ndarray) -> tuple[Optional[str], float]:
    """
    Run LBPH prediction on a face ROI.
    Returns (membership_id, confidence) or (None, 999) if unrecognized.
    """
    global _label_to_id
    
    # Ensure model is trained if possible
    if not _label_to_id:
        train_model()

    # If still no labels, we can't recognize anyone
    if not _label_to_id:
        logger.info("Recognition attempted but no members are registered yet.")
        return None, 999.0

    try:
        label, confidence = recognizer.predict(face_roi)
        
        if confidence > CONFIDENCE_THRESHOLD:
            return None, confidence

        if label < len(_label_to_id):
            return _label_to_id[label], confidence
            
    except cv.error as e:
        logger.error("OpenCV prediction error: %s. This usually happens if the model is not trained.", e)
        return None, 999.0

    return None, confidence


def delete_face_sample(membership_id: str) -> bool:
    """Remove a face sample file from disk."""
    path = os.path.join(SAMPLES_DIR, f"{membership_id}.png")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
