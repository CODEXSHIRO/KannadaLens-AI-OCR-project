"""Basic image preprocessing to help Tesseract read Kannada.

Every step is optional because preprocessing does not always help OCR.
The numeric settings below are starting points chosen from a small test set.
"""

import cv2
import numpy as np
from PIL import Image

from core.textsize import estimate_glyph_height

THRESHOLD_CHOICES = ("None", "Otsu", "Adaptive")

# Tesseract read best when the marks of the letters were about this tall
# (in pixels). Chosen from our 5-image scale experiment, so it is a starting
# point and not a rule that is proven for all documents.
TARGET_GLYPH_HEIGHT = 20.0
MIN_UPSCALE = 1.05       # ignore enlargements smaller than this
MAX_UPSCALE = 3.0
MAX_WIDTH = 3500
DOWNSCALE_TARGET_WIDTH = 3000

# Used only if the text size cannot be measured (for example a nearly blank image).
MIN_WIDTH_BEFORE_UPSCALE = 1000
UPSCALE_TARGET_WIDTH = 1500


def _resize(gray):
    """Enlarge small text (never enlarge big text) and shrink huge images."""
    _, width = gray.shape
    glyph_height = estimate_glyph_height(Image.fromarray(gray))

    if glyph_height is not None:
        scale = min(MAX_UPSCALE, TARGET_GLYPH_HEIGHT / glyph_height, MAX_WIDTH / width)
        if scale >= MIN_UPSCALE:
            return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    elif width < MIN_WIDTH_BEFORE_UPSCALE:
        scale = min(MAX_UPSCALE, UPSCALE_TARGET_WIDTH / width)
        return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    if width > MAX_WIDTH:
        scale = DOWNSCALE_TARGET_WIDTH / width
        return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return gray


def preprocess(image, resize=True, denoise=True, contrast=True, threshold="None"):
    """Return a preprocessed grayscale PIL image.

    Order: grayscale -> resize -> denoise -> contrast (CLAHE) -> threshold.
    """
    if threshold not in THRESHOLD_CHOICES:
        raise ValueError(f"Unknown threshold mode: {threshold}")

    gray = np.array(image.convert("L"))

    if resize:
        gray = _resize(gray)

    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=7, templateWindowSize=7, searchWindowSize=21)

    if contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    if threshold == "Otsu":
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif threshold == "Adaptive":
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )

    return Image.fromarray(gray)