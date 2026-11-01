"""Text helpers: OCR clean-up, search and highlighting.

All functions here are plain Python (no Streamlit), so they are easy to test.
"""

import html
import re

# Invisible joiners that Kannada text uses inside words (for example after a
# virama). A user typing a search word usually leaves them out, so searching
# ignores them.
JOINERS = ("\u200c", "\u200d")

ANUSVARA = "\u0c82"      # ಂ
DIGIT_ZERO = "\u0ce6"    # ೦ (Kannada digit zero, looks almost the same)

_LETTER_OR_VOWEL_SIGN = re.compile("[\u0c85-\u0cb9\u0cbe-\u0ccc]")
_KANNADA_DIGIT = re.compile("[\u0ce6-\u0cef]")


def fix_anusvara_zero(text):
    """Replace a Kannada digit zero with an anusvara when it sits inside a word.

    Tesseract often reads the anusvara (ಂ, a small ring after a letter) as the
    digit zero (೦). We only change a ೦ when:
      - the character before it is a Kannada letter or vowel sign, and
      - the character after it is not a Kannada digit.
    So real numbers such as ೧೦ or ೧೯೦೦ are left alone.

    Returns (fixed_text, number_of_characters_changed).
    """
    chars = list(text)
    changed = 0
    for i, ch in enumerate(chars):
        if ch != DIGIT_ZERO or i == 0:
            continue
        if not _LETTER_OR_VOWEL_SIGN.fullmatch(chars[i - 1]):
            continue
        if i + 1 < len(chars) and _KANNADA_DIGIT.fullmatch(chars[i + 1]):
            continue
        chars[i] = ANUSVARA
        changed += 1
    return "".join(chars), changed


def _strip_joiners(text):
    """Return (text without joiners, list mapping each kept char to its old index)."""
    kept = []
    index_map = []
    for i, ch in enumerate(text):
        if ch in JOINERS:
            continue
        kept.append(ch)
        index_map.append(i)
    return "".join(kept), index_map


def find_matches(text, query):
    """Return a list of (start, end) spans in `text` where `query` occurs.

    Case-insensitive for English. Ignores invisible joiners, so a typed word
    matches even if the OCR text contains a joiner inside it.
    """
    query = "".join(ch for ch in query.strip() if ch not in JOINERS)
    if not query:
        return []
    stripped, index_map = _strip_joiners(text)
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    spans = []
    for match in pattern.finditer(stripped):
        start = index_map[match.start()]
        end = index_map[match.end() - 1] + 1
        spans.append((start, end))
    return spans


def highlight_html(text, spans):
    """Return HTML with each span wrapped in <mark>. Text is HTML-escaped."""
    parts = []
    position = 0
    for start, end in spans:
        parts.append(html.escape(text[position:start]))
        parts.append("<mark>" + html.escape(text[start:end]) + "</mark>")
        position = end
    parts.append(html.escape(text[position:]))
    return "".join(parts).replace("\n", "<br>")