"""Day 6: evaluate the OCR pipeline on a small test set.

Folder layout (each image needs a correct text file with the same name):

    testset\\
        doc01.png     doc01.txt     (UTF-8 text of exactly what the image shows)
        doc02.jpg     doc02.txt

Run:
    python day6_evaluate.py              (uses the "testset" folder)
    python day6_evaluate.py my_folder

For every image it reads the text four ways (the same settings the app offers)
and compares with your correct text. Lower error is better. 0% = identical.
"""

import csv
import os
import sys

from PIL import Image

from core.metrics import error_counts
from core.ocr import OCRError, prepare_image, run_ocr
from core.preprocess import preprocess
from core.textutils import fix_anusvara_zero

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
OUT_DIR = "outputs"
TEXT_DIR = os.path.join(OUT_DIR, "evaluation")

SETTINGS = ["Off", "Off + clean-up", "Enhance", "Enhance + clean-up"]


def pct(errors, total):
    return errors / max(total, 1)


def read_reference(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def find_pairs(folder):
    """Return ([(image_path, reference_path)], [problem messages])."""
    pairs, problems = [], []
    for name in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in IMAGE_EXTENSIONS:
            continue
        ref_path = os.path.join(folder, stem + ".txt")
        if not os.path.isfile(ref_path):
            problems.append(f"{name}: skipped, no {stem}.txt next to it")
            continue
        if len("".join(read_reference(ref_path).split())) < 10:
            problems.append(f"{stem}.txt: skipped, the reference text is empty or too short")
            continue
        pairs.append((os.path.join(folder, name), ref_path))
    return pairs, problems


def read_four_ways(image):
    """Return {setting: text} for the four settings."""
    results = {}
    original = prepare_image(image)
    enhanced = preprocess(original, resize=True, denoise=True, contrast=True, threshold="None")
    for label, source in (("Off", original), ("Enhance", enhanced)):
        raw = run_ocr(source)
        results[label] = raw
        results[label + " + clean-up"] = fix_anusvara_zero(raw)[0]
    return results


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

    os.makedirs(TEXT_DIR, exist_ok=True)
    print(f"Evaluating {len(pairs)} image(s) from '{folder}'. This can take a while.\n")

    rows = []  # one row per (image, setting)
    for image_path, ref_path in pairs:
        stem = os.path.splitext(os.path.basename(image_path))[0]
        reference = read_reference(ref_path)
        try:
            image = Image.open(image_path)
            image.load()
            texts = read_four_ways(image)
        except OCRError as err:
            print("[FAIL]", err)
            return 1
        except Exception as err:  # noqa: BLE001
            print(f"[SKIP] {stem}: could not be processed ({err})")
            continue

        print(f"{stem}  ({image.size[0]} x {image.size[1]})")
        print(f"  {'Setting':22} {'Char err':>9} {'Word err':>9}")
        for setting in SETTINGS:
            text = texts[setting]
            with open(os.path.join(TEXT_DIR, f"{stem}__{setting.replace(' + ', '_').replace(' ', '_')}.txt"),
                      "w", encoding="utf-8") as f:
                f.write(text)
            c_err, c_total, w_err, w_total = error_counts(reference, text)
            rows.append(
                dict(image=stem, setting=setting, char_errors=c_err, ref_chars=c_total,
                     word_errors=w_err, ref_words=w_total)
            )
            print(f"  {setting:22} {pct(c_err, c_total):9.1%} {pct(w_err, w_total):9.1%}")
        print()

    if not rows:
        print("[FAIL] Nothing could be evaluated.")
        return 1

    images_done = len({r["image"] for r in rows})
    print("=" * 60)
    print(f"OVERALL on {images_done} image(s)")
    print("(total errors divided by total reference characters or words)")
    print(f"{'Setting':22} {'Char err':>9} {'Word err':>9}")
    overall = []
    for setting in SETTINGS:
        subset = [r for r in rows if r["setting"] == setting]
        c_err = sum(r["char_errors"] for r in subset)
        c_total = sum(r["ref_chars"] for r in subset)
        w_err = sum(r["word_errors"] for r in subset)
        w_total = sum(r["ref_words"] for r in subset)
        overall.append((setting, pct(c_err, c_total), pct(w_err, w_total)))
        print(f"{setting:22} {pct(c_err, c_total):9.1%} {pct(w_err, w_total):9.1%}")

    csv_path = os.path.join(OUT_DIR, "evaluation.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["image", "setting", "char_errors", "ref_chars", "word_errors", "ref_words"]
        )
        writer.writeheader()
        writer.writerows(rows)

    md_path = os.path.join(OUT_DIR, "evaluation.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# OCR evaluation on {images_done} image(s)\n\n")
        f.write("| Setting | Character error | Word error |\n|---|---|---|\n")
        for setting, c, w in overall:
            f.write(f"| {setting} | {c:.1%} | {w:.1%} |\n")
        f.write(
            "\nError rates compare the app's text with a correct reference text. "
            "Whitespace is ignored. Results apply only to this test set.\n"
        )

    print()
    print("These results apply only to this small test set. Do not present them")
    print("as general accuracy. Handwriting was not evaluated.")
    print(f"Saved: {csv_path}, {md_path} and the texts in {TEXT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())