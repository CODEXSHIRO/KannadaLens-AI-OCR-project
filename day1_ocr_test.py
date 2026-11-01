"""Day 1 OCR test. Run: python day1_ocr_test.py samples\\sample1.png"""

import os
import sys

import pytesseract
from PIL import Image, UnidentifiedImageError

from core.tesseract_setup import configure_tesseract

# Windows consoles often can't print Kannada; force UTF-8 where possible.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

OUTPUT_FILE = os.path.join("outputs", "day1_output.txt")


def count_kannada_chars(text):
    """Count characters in the Kannada Unicode block (U+0C80 to U+0CFF)."""
    return sum(1 for ch in text if "\u0c80" <= ch <= "\u0cff")


def main():
    if len(sys.argv) < 2:
        print("Usage: python day1_ocr_test.py <path-to-image>")
        return 1

    image_path = sys.argv[1]

    try:
        configure_tesseract("kan")
    except RuntimeError as err:
        print("[FAIL]", err)
        return 1

    try:
        image = Image.open(image_path)
    except FileNotFoundError:
        print(f"[FAIL] File not found: {image_path}")
        return 1
    except UnidentifiedImageError:
        print(f"[FAIL] Not a readable image: {image_path}")
        return 1

    print(f"Image loaded: {image.size[0]} x {image.size[1]} pixels")
    print("Running Kannada OCR...")

    text = pytesseract.image_to_string(image, lang="kan", config="--oem 1 --psm 3")

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)

    kannada_chars = count_kannada_chars(text)
    print("\n--- Extracted text ---")
    print(text if text.strip() else "(empty result)")
    print("----------------------")
    print(f"Total characters: {len(text)} | Kannada characters: {kannada_chars}")
    print(f"Saved (UTF-8) to: {OUTPUT_FILE}")

    if kannada_chars == 0:
        print("\n[WARNING] No Kannada characters found. See the troubleshooting list.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())