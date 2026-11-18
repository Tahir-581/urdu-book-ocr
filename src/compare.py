"""Compare two independent transcriptions of a page and mark the words where they disagree.

Comparison runs on a *normalized* form (spelling variants such as ھ/ہ, quote styles and
Arabic/Urdu code points are folded) so that style differences are not flagged as errors.
The output keeps transcription A's original spelling.
"""
import re
import unicodedata
from difflib import SequenceMatcher

# Folds applied only for comparison, never to the output text.
FOLD = str.maketrans({
    "ھ": "ہ", "ۃ": "ہ", "ة": "ہ", "ه": "ہ",
    "ي": "ی", "ى": "ی", "ئ": "ی",
    "ك": "ک",
    "”": '"', "“": '"', "’": '"', "‘": '"', "«": '"', "»": '"',
    "۔": ".", "-": ".", "،": ",", "؟": "?",
})
ZW = re.compile(r"[‌‍‎‏ً-ٰٟ]")  # zero-width + harakat


def norm(word: str) -> str:
    w = unicodedata.normalize("NFC", word)
    w = ZW.sub("", w).translate(FOLD)
    w = w.replace("''", '"')
    return w.strip(".,\"?!:;()[]")


def parse(text: str):
    """Return (page_number, lines). Drops the PAGE: header line and blank lines."""
    page, lines = None, []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.upper().startswith("PAGE:"):
            page = s.split(":", 1)[1].strip()
            continue
        lines.append(s)
    return page, lines


def compare(text_a: str, text_b: str):
    """Align B against A word by word (across line breaks).

    Returns a list of lines; each line is a list of (word, alt) where alt is None when both
    models agree, or B's reading ('' if B omitted the word) when they disagree.
    Also returns the B-only insertions so missing words in A are visible.
    """
    page_a, lines_a = parse(text_a)
    page_b, lines_b = parse(text_b)
    words_a = [(li, w) for li, line in enumerate(lines_a) for w in line.split()]
    words_b = [w for line in lines_b for w in line.split()]
    na = [norm(w) for _, w in words_a]
    nb = [norm(w) for w in words_b]

    alt = [None] * len(words_a)
    group = [None] * len(words_a)  # A words from the same disagreement share a group id
    inserted = {}  # index in A before which B has extra words
    sm = SequenceMatcher(None, na, nb, autojunk=False)
    for gid, (tag, i1, i2, j1, j2) in enumerate(sm.get_opcodes()):
        if tag == "equal":
            continue
        # Space-only differences ("نا کام" vs "ناکام") are not real disagreements.
        if tag == "replace" and "".join(na[i1:i2]) == "".join(nb[j1:j2]):
            continue
        b_span = " ".join(words_b[j1:j2])
        if tag == "insert":
            inserted.setdefault(i1, []).append(b_span)
            continue
        for k in range(i1, i2):
            alt[k], group[k] = b_span, gid

    out = [[] for _ in lines_a]
    prev_gid = None
    for k, (li, w) in enumerate(words_a):
        if k in inserted:
            out[li].append(("", " ".join(inserted[k])))
            prev_gid = None
        g = group[k]
        # Merge consecutive A words of one disagreement (on the same line) into a single chunk.
        if g is not None and g == prev_gid and out[li] and out[li][-1][1] is not None:
            out[li][-1] = (out[li][-1][0] + " " + w, out[li][-1][1])
        elif g is not None and g == prev_gid:
            out[li].append((w, ""))  # continuation on a new line: B's text already shown on the first chunk
        else:
            out[li].append((w, alt[k]))
        prev_gid = g
    if len(words_a) in inserted and out:
        out[-1].append(("", " ".join(inserted[len(words_a)])))

    n_words = len(words_a)
    n_flag = sum(1 for line in out for w, a in line if a is not None)
    n_lines_flag = sum(1 for line in out if any(a is not None for _, a in line))
    stats = {
        "page_a": page_a, "page_b": page_b,
        "words": n_words, "flagged_words": n_flag,
        "lines": len(lines_a), "flagged_lines": n_lines_flag,
        "agreement": round(1 - n_flag / max(1, n_words), 4),
    }
    return out, stats
