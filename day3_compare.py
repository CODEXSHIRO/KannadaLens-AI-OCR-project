"""Compare OCR error rates under different preprocessing settings.

Usage: python day3_compare.py samples\\sample1.png samples\\sample1.txt
Lower error is better. Whitespace is ignored. Scores are on Unicode code points.
"""

import os
import sys

from PIL import Image

from core.ocr import OCRError, prepare_image, run_ocr
from core.preprocess import preprocess

OUT_DIR = os.path.join("outputs", "compare")

CONFIGS = [
    ("original (no preprocessing)", None),
    ("resize only", dict(resize=True, denoise=False, contrast=False, threshold="None")),
    ("contrast only", dict(resize=False, denoise=False, contrast=True, threshold="None")),
    ("resize+denoise+contrast", dict(resize=True, denoise=True, contrast=True, threshold="None")),
    ("Otsu only", dict(resize=False, denoise=False, contrast=False, threshold="Otsu")),
    ("resize+Otsu", dict(resize=True, denoise=False, contrast=False, threshold="Otsu")),
]


def edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, 1):
        current = [i]
        for j, item_b in enumerate(b, 1):
            cost = 0 if item_a == item_b else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def error_rates(reference, hypothesis):
    ref_chars = "".join(reference.split())
    hyp_chars = "".join(hypothesis.split())
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    cer = edit_distance(ref_chars, hyp_chars) / max(len(ref_chars), 1)
    wer = edit_distance(ref_words, hyp_words) / max(len(ref_words), 1)
    return cer, wer


def main():
    if len(sys.argv) < 3:
        print("Usage: python day3_compare.py <image> <reference.txt>")
        return 1

    image_path, ref_path = sys.argv[1], sys.argv[2]

    try:
        with open(ref_path, "r", encoding="utf-8-sig") as f:
            reference = f.read()
    except FileNotFoundError:
        print(f"[FAIL] Reference file not found: {ref_path}")
        return 1

    try:
        original = prepare_image(Image.open(image_path))
    except Exception as err:  # noqa: BLE001
        print(f"[FAIL] Could not open image: {err}")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Image: {image_path} ({original.size[0]} x {original.size[1]})")
    print(f"Reference: {ref_path}\n")
    print(f"{'Setting':30} {'Char err':>9} {'Word err':>9}")
    print("-" * 50)

    results = []
    for index, (name, cfg) in enumerate(CONFIGS, 1):
        try:
            image_in = original if cfg is None else preprocess(original, **cfg)
            text = run_ocr(image_in)
        except OCRError as err:
            print(f"{name:30} OCR failed: {err}")
            continue

        safe = "".join(c if c.isalnum() else "_" for c in name)
        with open(os.path.join(OUT_DIR, f"{index:02d}_{safe}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        image_in.save(os.path.join(OUT_DIR, f"{index:02d}_{safe}.png"))

        cer, wer = error_rates(reference, text)
        results.append((name, cer, wer))
        print(f"{name:30} {cer:9.1%} {wer:9.1%}")

    if results:
        best = min(results, key=lambda r: (r[1], r[2]))
        print(f"\nLowest error on this image: {best[0]}")
        print("This is one image. Do not generalize from it.")
        print(f"Texts and processed images saved in: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())