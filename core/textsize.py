"""Estimate how large the text in an image is (a rough index, in pixels).

We find the dark marks (letters and parts of letters) and take the median
height of the reasonably sized ones. It is only used to compare images with
each other, not as an exact font size.
"""

import cv2
import numpy as np


def estimate_glyph_height(image):
    """Return the median height in pixels of text marks, or None if none found."""
    gray = np.array(image.convert("L"))
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Text should be the minority colour. If most pixels are "ink", flip.
    if binary.mean() > 127:
        binary = 255 - binary

    _, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    heights = stats[1:, cv2.CC_STAT_HEIGHT]
    widths = stats[1:, cv2.CC_STAT_WIDTH]
    areas = stats[1:, cv2.CC_STAT_AREA]

    image_height = gray.shape[0]
    keep = (areas >= 6) & (heights >= 3) & (heights < image_height * 0.5) & (widths < gray.shape[1] * 0.5)
    if keep.sum() < 10:
        return None
    return float(np.median(heights[keep]))