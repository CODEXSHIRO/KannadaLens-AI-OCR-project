"""Locates Tesseract on Windows and checks that Kannada (kan) is installed."""

import os
import shutil

import pytesseract

COMMON_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]


def find_tesseract():
    """Return the path to tesseract.exe, or None if it can't be found."""
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    for path in COMMON_PATHS:
        if os.path.isfile(path):
            return path
    return None


def configure_tesseract(required_lang="kan"):
    """Point pytesseract at tesseract.exe and confirm the language is installed.

    Raises RuntimeError with a human-readable message if anything is wrong.
    """
    exe = find_tesseract()
    if exe is None:
        raise RuntimeError(
            "Tesseract was not found. Install it from the UB Mannheim page "
            "(https://github.com/UB-Mannheim/tesseract/wiki) and run this again."
        )
    pytesseract.pytesseract.tesseract_cmd = exe

    try:
        languages = pytesseract.get_languages(config="")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Tesseract was found at {exe} but could not run: {exc}")

    if required_lang not in languages:
        raise RuntimeError(
            f"Kannada language data ('{required_lang}') is missing. "
            f"Installed languages: {', '.join(languages)}. "
            "Copy kan.traineddata into the tessdata folder next to tesseract.exe."
        )
    return exe, languages