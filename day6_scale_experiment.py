"""Day 6 experiment: which image scale reads best for each text size?

Uses the same "testset" folder as day6_evaluate.py (image + .txt pairs).
For each image it resizes by several factors, reads the text, applies the
digit-zero clean-up, and reports the character error for each factor.

Run:
    python day6_scale_experiment.py
"""

import os
import sys

import cv2
import numpy as np
from PIL import Image

from core.metrics import error_counts
from core.ocr import OCRError, prepare_image, run_ocr
from core.textsize import estimate_glyph_height
from core.textutils import fix_anusvara_zero
from day6_evaluate import find_pairs, read_reference

SCALES = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
MAX_SIDE = 6000


def rescale(image, factor):
    """Resize a PIL image by `factor` (smooth when shrinking, cubic when enlarging)."""
    if factor == 1.0:
        return image
    array = np.array(image)
    method = cv2.INTER_AREA if factor < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(array, None, fx=factor, fy=factor, interpolation=method)
    return Image.fromarray(resized)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "testset"
    if not os.path.isdir(folder):
        print(f"[FAIL] Folder not found: {folder}")
        return 1
    pairs, problems = find_pairs(folder)
    for message in problems:
        print("[SKIP]", message)
    if not pairs:
        print("[FAIL] No usable image + text pairs found.")
        return 1

    print(f"Scale experiment on {len(pairs)} image(s). Character error (%) for each scale:\n")
    header = "".join(f"{('x' + str(s)):>8}" for s in SCALES)
    print(f"{'Image':8} {'Text size':>10}{header}   Best")
    print("-" * (22 + 8 * len(SCALES) + 8))

    summary = []
    for image_path, ref_path in pairs:
        stem = os.path.splitext(os.path.basename(image_path))[0]
        reference = read_reference(ref_path)
        try:
            image = prepare_image(Image.open(image_path))
        except Exception as err:  # noqa: BLE001
            print(f"[SKIP] {stem}: could not be opened ({err})")
            continue

        height = estimate_glyph_height(image)
        errors = {}
        for factor in SCALES:
            if max(image.size) * factor > MAX_SIDE:
                continue
            try:
                text = run_ocr(rescale(image, factor))
            except OCRError as err:
                print("[FAIL]", err)
                return 1
            text = fix_anusvara_zero(text)[0]
            c_err, c_total, _, _ = error_counts(reference, text)
            errors[factor] = c_err / max(c_total, 1)

        best = min(errors, key=lambda k: (errors[k], abs(k - 1.0)))
        cells = "".join(
            f"{errors[s] * 100:8.1f}" if s in errors else f"{'-':>8}" for s in SCALES
        )
        height_text = f"{height:.0f} px" if height else "?"
        print(f"{stem:8} {height_text:>10}{cells}   x{best}")
        summary.append((stem, height, best))

    print()
    print("Text size = median height of the letter marks, a rough index only.")
    print("'Best' = the scale with the lowest character error on that image.")
    if summary:
        print("\nText size x best scale (about the same number = a good target size):")
        for stem, height, best in summary:
            if height:
                print(f"  {stem}: {height:.0f} x {best} = {height * best:.0f}")
    print("\nResults apply only to this small test set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())