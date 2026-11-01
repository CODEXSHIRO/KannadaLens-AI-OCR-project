"""Day 6: does Tesseract's word confidence point at the words that are wrong?

Uses the same "testset" folder as day6_evaluate.py (image + .txt pairs) and
reads each image the way the app does by default (Enhance + clean-up).
For every word it records the confidence (0 to 100) and whether the word
matches your correct text. Then it shows what would happen if the editor
highlighted every word below a confidence limit.

Run:
    python day6_confidence_check.py
"""

import csv
import os
import sys
from difflib import SequenceMatcher

import pytesseract
from pytesseract import Output
from PIL import Image

from core.ocr import LANG, OCRError, TESS_CONFIG, prepare_image
from core.preprocess import preprocess
from core.tesseract_setup import configure_tesseract
from core.textutils import fix_anusvara_zero
from day6_evaluate import find_pairs, read_reference

THRESHOLDS = [40, 50, 60, 70, 80, 90]
OUT_DIR = "outputs"


def label_words(ocr_words, reference_words):
    """For each OCR word, True if it lines up with an identical reference word."""
    correct = [False] * len(ocr_words)
    matcher = SequenceMatcher(None, ocr_words, reference_words, autojunk=False)
    for block in matcher.get_matching_blocks():
        for i in range(block.a, block.a + block.size):
            correct[i] = True
    return correct


def read_words_with_confidence(image):
    """Return [(word, confidence)] as Tesseract reports them."""
    data = pytesseract.image_to_data(
        image, lang=LANG, config=TESS_CONFIG, output_type=Output.DICT
    )
    words = []
    for text, conf in zip(data["text"], data["conf"]):
        text = str(text).strip()
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            continue
        if not text or conf < 0:
            continue
        words.append((fix_anusvara_zero(text)[0], conf))
    return words


def summarize(rows):
    """Print the pooled results for all words."""
    total = len(rows)
    wrong = [r for r in rows if not r["correct"]]
    right = [r for r in rows if r["correct"]]
    wrong_rate = len(wrong) / total

    print("=" * 66)
    print(f"ALL IMAGES: {total} words read, {len(wrong)} do not match the reference "
          f"({wrong_rate:.1%})")
    if right and wrong:
        mean_right = sum(r["conf"] for r in right) / len(right)
        mean_wrong = sum(r["conf"] for r in wrong) / len(wrong)
        print(f"Average confidence: matching words {mean_right:.0f}, "
              f"non-matching words {mean_wrong:.0f}")
    print()
    print("If the editor highlighted every word BELOW the confidence limit:")
    print(f"{'Limit':>6} {'Highlighted':>12} {'Wrong words caught':>20} {'Highlighted that are wrong':>28}")
    for limit in THRESHOLDS:
        flagged = [r for r in rows if r["conf"] < limit]
        caught = [r for r in flagged if not r["correct"]]
        share_flagged = len(flagged) / total
        recall = len(caught) / len(wrong) if wrong else 0.0
        precision = len(caught) / len(flagged) if flagged else 0.0
        print(f"{limit:>6} {share_flagged:>11.0%} {recall:>19.0%} {precision:>27.0%}")
    print()
    print(f"For comparison, picking words at random would give about {wrong_rate:.0%} "
          f"in the last column.")


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

    try:
        configure_tesseract(LANG)
    except RuntimeError as err:
        print("[FAIL]", err)
        return 1

    rows = []
    print(f"Checking {len(pairs)} image(s) with the app's default settings...\n")
    for image_path, ref_path in pairs:
        stem = os.path.splitext(os.path.basename(image_path))[0]
        reference_words = read_reference(ref_path).split()
        try:
            image = prepare_image(Image.open(image_path))
            enhanced = preprocess(image, resize=True, denoise=True, contrast=True, threshold="None")
            words = read_words_with_confidence(enhanced)
        except OCRError as err:
            print("[FAIL]", err)
            return 1
        except Exception as err:  # noqa: BLE001
            print(f"[SKIP] {stem}: could not be processed ({err})")
            continue

        labels = label_words([w for w, _ in words], reference_words)
        wrong_count = labels.count(False)
        print(f"{stem}: {len(words)} words, {wrong_count} not matching "
              f"({wrong_count / max(len(words), 1):.0%})")
        for (word, conf), ok in zip(words, labels):
            rows.append(dict(image=stem, word=word, conf=conf, correct=ok))

    if not rows:
        print("[FAIL] No words were read.")
        return 1

    print()
    summarize(rows)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "confidence_words.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "word", "conf", "correct"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nEvery word with its confidence is saved in {path}")
    print("'Matching' means identical to a word in your correct text, so reading-order")
    print("differences count as wrong. Results apply only to this small test set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())