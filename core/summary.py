"""A simple EXTRACTIVE summary, document statistics and a text preview.

This is not AI. It copies existing sentences from the text and chooses them by
how often their words are repeated in the document. It does not understand,
rewrite or translate anything.
"""

import re
from collections import Counter

PAGE_MARKER = re.compile(r"^---\s*Page\s+\d+\s*---\s*$", re.IGNORECASE | re.MULTILINE)
_SENTENCE_END = re.compile(r"(?<=[.?!\u0964])\s+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_EDGE_PUNCTUATION = ".,;:!?()[]{}\"'\u201c\u201d\u2018\u2019*_-\u2013\u2014/\\|\u2022\u00b7\u2026"
_JOINERS = ("\u200c", "\u200d")

MIN_SENTENCE_CHARS = 25
MIN_SENTENCE_WORDS = 5


def remove_page_markers(text):
    return PAGE_MARKER.sub("", text)


def split_sentences(text):
    """Split text into sentences. Hard line breaks inside a paragraph are joined."""
    sentences = []
    for paragraph in _PARAGRAPH_BREAK.split(remove_page_markers(text)):
        joined = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        for piece in _SENTENCE_END.split(joined):
            piece = piece.strip().lstrip("*_\u2022- ").strip()
            if piece:
                sentences.append(piece)
    return sentences


def extract_words(text):
    """Return the words in `text` (punctuation trimmed, joiners removed)."""
    words = []
    for token in remove_page_markers(text).split():
        token = "".join(ch for ch in token if ch not in _JOINERS)
        token = token.strip(_EDGE_PUNCTUATION)
        if token and any(ch.isalpha() for ch in token):
            words.append(token)
    return words


def kannada_share(text):
    """Share (0 to 1) of non-space characters that are in the Kannada block."""
    chars = [ch for ch in remove_page_markers(text) if not ch.isspace()]
    if not chars:
        return 0.0
    kannada = sum(1 for ch in chars if "\u0c80" <= ch <= "\u0cff")
    return kannada / len(chars)


def stats(text):
    clean = remove_page_markers(text)
    return {
        "words": len(extract_words(text)),
        "sentences": len(split_sentences(text)),
        "lines": sum(1 for line in clean.splitlines() if line.strip()),
        "kannada_share": kannada_share(text),
    }


def top_words(text, count=8, min_chars=4):
    """Most repeated words (exact spelling, no stop-word filtering)."""
    counter = Counter(w for w in extract_words(text) if len(w) >= min_chars)
    return [(w, n) for w, n in counter.most_common(count) if n >= 2]


def key_sentences(text, count=3):
    """Pick `count` sentences, returned in their original order.

    Score = average repetition of the sentence's words across the document.
    Ties are broken in favour of earlier sentences.
    """
    sentences = split_sentences(text)
    frequency = Counter(w for w in extract_words(text) if len(w) >= 3)

    candidates = []
    for position, sentence in enumerate(sentences):
        words = extract_words(sentence)
        if len(sentence) < MIN_SENTENCE_CHARS or len(words) < MIN_SENTENCE_WORDS:
            continue
        score = sum(frequency[w] for w in words if len(w) >= 3) / len(words)
        candidates.append((-score, position, sentence))

    chosen = sorted(candidates)[:count]
    return [sentence for _, _, sentence in sorted(chosen, key=lambda item: item[1])]


def preview(text, max_chars=300):
    """The beginning of the document, cut at a word boundary."""
    clean = " ".join(remove_page_markers(text).split()).lstrip("*_\u2022- ")
    if len(clean) <= max_chars:
        return clean
    cut = clean[:max_chars].rsplit(" ", 1)[0]
    return cut + " \u2026"