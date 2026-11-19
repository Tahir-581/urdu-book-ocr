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
ZW = re.compile("[\u200c\u200d\u200e\u200f\u202a-\u202e\u2066-\u2069\u064b-\u065f\u0670]")  # zero-width, bidi controls, harakat


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


def _align(na, words_b):
    """Disagreements of one checker against A's normalized words.
    Returns per-A-word reading (None = agrees), per-A-word group id, and B-only insertions."""
    nb = [norm(w) for w in words_b]
    alt = [None] * len(na)
    group = [None] * len(na)  # A words from the same disagreement share a group id
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
            inserted[i1] = b_span
            continue
        for k in range(i1, i2):
            alt[k], group[k] = b_span, gid
    return alt, group, inserted


def _join(readings):
    """One checker: its reading as is ('' = it has no word here). Several: 'x / —'."""
    readings = list(dict.fromkeys(readings))  # unique, in checker order
    if len(readings) == 1:
        return readings[0]
    return " / ".join(r or "—" for r in readings)


def compare(text_a: str, *texts_b: str):
    """Align each checker B against A word by word (across line breaks).

    Returns a list of lines; each line is a list of (word, alt) where alt is None when every
    checker agrees with A, or the disagreeing checkers' reading(s) otherwise ('' if the only
    disagreeing checker omitted the word; several readings are joined with ' / ').
    B-only insertions appear as ('', reading) so words missing from A are visible.
    """
    page_a, lines_a = parse(text_a)
    words_a = [(li, w) for li, line in enumerate(lines_a) for w in line.split()]
    na = [norm(w) for _, w in words_a]
    per_b = []
    page_b = None
    for text_b in texts_b:
        pb, lines_b = parse(text_b)
        page_b = page_b or pb
        per_b.append(_align(na, [w for line in lines_b for w in line.split()]))

    n = len(words_a)
    alt = [None] * n
    group = [None] * n
    inserted = {}
    for k in range(n + 1):
        ins = [b[2][k] for b in per_b if k in b[2]]
        if ins:
            inserted[k] = _join(ins)
        if k == n:
            break
        reads = [b[0][k] for b in per_b if b[0][k] is not None]
        if reads:
            alt[k] = _join(reads)
            group[k] = tuple(b[1][k] for b in per_b)

    def same_group(g1, g2):
        return g1 is not None and g2 is not None and any(x is not None and x == y for x, y in zip(g1, g2))

    out = [[] for _ in lines_a]
    prev_g = None
    for k, (li, w) in enumerate(words_a):
        if k in inserted:
            out[li].append(("", inserted[k]))
            prev_g = None
        g = group[k]
        # Merge consecutive A words of one disagreement (on the same line) into a single chunk.
        if same_group(g, prev_g) and out[li] and out[li][-1][1] is not None:
            out[li][-1] = (out[li][-1][0] + " " + w, out[li][-1][1])
        elif same_group(g, prev_g):
            out[li].append((w, ""))  # continuation on a new line: the reading is already on the first chunk
        else:
            out[li].append((w, alt[k]))
        prev_g = g
    if n in inserted and out:
        out[-1].append(("", inserted[n]))

    n_flag = sum(1 for line in out for w, a in line if a is not None)
    n_lines_flag = sum(1 for line in out if any(a is not None for _, a in line))
    stats = {
        "page_a": page_a, "page_b": page_b,
        "words": n, "flagged_words": n_flag,
        "lines": len(lines_a), "flagged_lines": n_lines_flag,
        "agreement": round(1 - n_flag / max(1, n), 4),
    }
    return out, stats
