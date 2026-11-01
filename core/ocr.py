"""Kannada OCR using Tesseract. Used by the Streamlit app."""

import pytesseract
from PIL import Image, ImageOps

from core.tesseract_setup import configure_tesseract

LANG = "kan"
TESS_CONFIG = "--oem 1 --psm 3"


class OCRError(Exception):
    """Raised with a user-friendly message when OCR cannot be completed."""


_configured = False


def _ensure_ready():
    """Locate Tesseract and verify Kannada data once per session."""
    global _configured
    if _configured:
        return
    try:
        configure_tesseract(LANG)
    except RuntimeError as err:
        raise OCRError(str(err)) from err
    _configured = True


def prepare_image(image):
    """Fix phone rotation and flatten transparency so OCR gets a clean RGB image."""
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[3])
        return background
    return image.convert("RGB")


def run_ocr_detailed(image):
    """Read an image and return a list of (separator_before, word, confidence).

    The separator is "", " ", "\\n" (new line) or "\\n\\n" (new paragraph or
    block), so joining separator + word for every item rebuilds the text.
    Confidence is Tesseract's own 0 to 100 score for that word.
    """
    _ensure_ready()
    prepared = prepare_image(image)
    try:
        data = pytesseract.image_to_data(
            prepared, lang=LANG, config=TESS_CONFIG, output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractNotFoundError as err:
        raise OCRError("Tesseract could not be started. Re-run day1_check.py.") from err
    except pytesseract.TesseractError as err:
        raise OCRError(f"Tesseract failed on this image: {err}") from err
    except Exception as err:  # noqa: BLE001
        raise OCRError(f"Unexpected OCR error: {err}") from err

    words = []
    previous = None
    for i, raw_text in enumerate(data["text"]):
        word = str(raw_text).strip()
        if not word:
            continue
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            continue
        if confidence < 0:
            continue

        position = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if previous is None:
            separator = ""
        elif position[:2] != previous[:2]:
            separator = "\n\n"
        elif position[2] != previous[2]:
            separator = "\n"
        else:
            separator = " "
        previous = position
        words.append((separator, word, confidence))
    return words


def run_ocr(image):
    """Run Kannada OCR on a PIL image and return the extracted text."""
    words = run_ocr_detailed(image)
    text = "".join(separator + word for separator, word, _ in words)
    return text.replace("\r\n", "\n").strip()