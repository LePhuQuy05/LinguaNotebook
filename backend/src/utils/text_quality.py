"""Text-quality helpers — tell a usable text layer from a garbage one.

A PDF can carry a text layer that is itself a bad OCR of the page image
(baked in when the scan was produced): it passes a char-count check but
the text is gibberish. These helpers measure how much of the text is
noise — symbols that never appear in prose — so the parse pipeline can
route such documents to the real OCR backend instead of trusting the
garbage layer.
"""

import re

# Symbols that never appear in natural prose but are common in bad-OCR
# output (`tf=fv7r- E6=EfrWt=ilfiffi`). Kept to ASCII so full-width CJK
# punctuation (、。「」) never counts as noise.
JUNK_CHARS = set("=^<>(){}[]|#@%&*+_~`;")

_WS = re.compile(r"\s")
_JUNK_CHARS_RE = re.compile(r"[=^<>(){}[\]|#@%&*+_~`;]")

# A text layer with this fraction of noise symbols on a scanned page is
# untrustworthy. Measured against real documents: clean prose is ~0.5%
# (paper.pdf), baked-in bad OCR is 7–17% (CHOUKAI).
JUNK_RATIO_BAD = 0.05


def junk_ratio(text: str) -> float:
    """Fraction of non-whitespace characters that are noise symbols.

    Returns 0.0 for empty or whitespace-only text, so callers can treat
    small pages as noise-free without special-casing the denominator.
    """
    nonws = _WS.sub("", text)
    if not nonws:
        return 0.0
    junk = len(_JUNK_CHARS_RE.findall(nonws))
    return junk / len(nonws)
