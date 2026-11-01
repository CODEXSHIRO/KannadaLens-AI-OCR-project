"""Day 1 installation check. Run: python day1_check.py"""

import sys

import pytesseract

from core.tesseract_setup import configure_tesseract


def main():
    print("Python version:", sys.version.split()[0])
    try:
        exe, languages = configure_tesseract("kan")
    except RuntimeError as err:
        print("\n[FAIL]", err)
        return 1

    print("Tesseract path:", exe)
    print("Tesseract version:", pytesseract.get_tesseract_version())
    print("Installed languages:", ", ".join(languages))
    print("\n[OK] Tesseract and Kannada data are installed correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())