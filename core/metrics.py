"""Error-rate helpers for comparing OCR output with a correct reference text.

Characters are Unicode code points, not visible letters, because one Kannada
letter can be several code points. Whitespace differences are ignored.
"""


def edit_distance(a, b):
    """Levenshtein distance between two sequences."""
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


def error_counts(reference, hypothesis):
    """Return (char_errors, reference_chars, word_errors, reference_words)."""
    ref_chars = "".join(reference.split())
    hyp_chars = "".join(hypothesis.split())
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    return (
        edit_distance(ref_chars, hyp_chars),
        len(ref_chars),
        edit_distance(ref_words, hyp_words),
        len(ref_words),
    )