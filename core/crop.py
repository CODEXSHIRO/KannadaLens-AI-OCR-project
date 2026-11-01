"""Cut margins, side columns or pictures off a page before OCR."""

from PIL import Image

MIN_KEPT_PERCENT = 10  # at least this much of each direction must remain


def crop_box(size, left=0, right=0, top=0, bottom=0):
    """Return (x0, y0, x1, y1) after removing the given percent from each side.

    Returns None when nothing is cut. Raises ValueError when fewer than
    MIN_KEPT_PERCENT percent of the width or height would remain.
    """
    width, height = size
    if not (left or right or top or bottom):
        return None
    for value in (left, right, top, bottom):
        if value < 0 or value > 100:
            raise ValueError("Crop percentages must be between 0 and 100.")
    if 100 - left - right < MIN_KEPT_PERCENT or 100 - top - bottom < MIN_KEPT_PERCENT:
        raise ValueError("Too much is cut away. Leave at least 10% of the page.")
    x0 = round(width * left / 100)
    x1 = width - round(width * right / 100)
    y0 = round(height * top / 100)
    y1 = height - round(height * bottom / 100)
    if x1 - x0 < 1 or y1 - y0 < 1:
        raise ValueError("Too much is cut away. Leave at least 10% of the page.")
    return (x0, y0, x1, y1)


def crop_image(image, left=0, right=0, top=0, bottom=0):
    """Return the kept part of the image (the same image when nothing is cut)."""
    box = crop_box(image.size, left, right, top, bottom)
    if box is None:
        return image
    return image.crop(box)


def dim_outside(image, box, strength=0.6):
    """Return a copy with everything outside `box` darkened (for the preview)."""
    if box is None:
        return image
    dark = Image.blend(image, Image.new(image.mode, image.size, (0, 0, 0)), strength)
    dark.paste(image.crop(box), (box[0], box[1]))
    return dark