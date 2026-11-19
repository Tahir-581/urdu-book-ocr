"""Score transcriptions against hand-verified ground truth.

Metrics (all computed on the normalized form from compare.norm, so ھ/ہ, quote styles and
spacing around punctuation don't count as errors):
  CER  character error rate  = edit distance / ground-truth characters
  WER  word error rate
For the two-model flagging (A = primary, B = checker):
  errors        word-level error chunks in A versus ground truth
  caught        error chunks where A and B disagreed (so the reader is told to look)
  silent        error chunks with no flag: wrong text presented as trustworthy
  burden        share of A's words that are flagged (what a human must check)

Usage:
  python -m src.evaluate                        # default model dirs, writes out/eval/report.md + .json
"""
import json, subprocess, sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.compare import parse, norm  # noqa: E402

GT = ROOT / "data" / "groundtruth"
BASE = ROOT / "out" / "baseline"
SCANS = ROOT / "data" / "scans"


def words(text):
    _, lines = parse(text)
    return [n for line in lines for w in line.split() if (n := norm(w))]


def levenshtein_slow(a, b):
    """Reference O(n*m) implementation, kept for the self-test."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def levenshtein(a, b):
    """Edit distance between two sequences (strings or word lists), bit-parallel (Myers/Hyyro).
    One Python big-int operation per item of b instead of len(a) operations: ~100x faster."""
    if not a:
        return len(b)
    m = len(a)
    full = (1 << m) - 1
    top = 1 << (m - 1)
    peq = {}
    for i, c in enumerate(a):
        peq[c] = peq.get(c, 0) | (1 << i)
    pv, mv, score = full, 0, m
    for c in b:
        eq = peq.get(c, 0)
        xv = eq | mv
        xh = (((eq & pv) + pv) ^ pv) | eq
        ph = (mv | ~(xh | pv)) & full
        mh = pv & xh
        if ph & top:
            score += 1
        elif mh & top:
            score -= 1
        ph = ((ph << 1) | 1) & full
        mh = (mh << 1) & full
        pv = (mh | ~(xv | ph)) & full
        mv = ph & xv
    return score


def cer_wer(hyp_words, ref_words):
    h, r = " ".join(hyp_words), " ".join(ref_words)
    cer = levenshtein(h, r) / max(1, len(r))
    wer = levenshtein(hyp_words, ref_words) / max(1, len(ref_words))
    return cer, wer


def flags_of(a_words, b_words):
    """Per A-word flag (A and B disagree), plus gap flags (B has words A lacks, before index i)."""
    flag = [False] * len(a_words)
    gap = set()
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a_words, b_words, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and "".join(a_words[i1:i2]) == "".join(b_words[j1:j2]):
            continue
        if tag == "insert":
            gap.add(i1)
        for k in range(i1, i2):
            flag[k] = True
    return flag, gap


def flag_eval(a_words, b_words, ref_words):
    flag, gap = flags_of(a_words, b_words)
    errors = caught = 0
    missed = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a_words, ref_words, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and "".join(a_words[i1:i2]) == "".join(ref_words[j1:j2]):
            continue  # spacing only
        errors += 1
        if tag == "insert":  # A is missing words: caught if B has a gap here or a neighbour is flagged
            hit = i1 in gap or (i1 > 0 and flag[i1 - 1]) or (i1 < len(flag) and flag[i1])
        else:
            hit = any(flag[i1:i2]) or i1 in gap
        if hit:
            caught += 1
        else:
            missed.append({"model": " ".join(a_words[i1:i2]) or "(missing)", "truth": " ".join(ref_words[j1:j2]) or "(extra)"})
    n_flag = sum(flag) + len(gap)
    return {"errors": errors, "caught": caught, "silent": errors - caught, "missed": missed,
            "flagged_words": n_flag, "burden": n_flag / max(1, len(a_words))}


def archive_org_words(stem):
    """archive.org's own OCR for the PDF page this image came from."""
    book, rest = stem.split("-", 1)
    page = int(rest.rstrip("RL"))
    pdf = SCANS / f"{book}_ia_text.pdf"
    if not pdf.exists():
        return None
    txt = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), str(pdf), "-"],
                         capture_output=True, text=True).stdout
    return [n for w in txt.split() if (n := norm(w))]


def main(model_a="gemini__gemini-3.5-flash", model_b="gemini__gemini-3.1-flash-lite"):
    models = sorted(p.name for p in BASE.iterdir() if p.is_dir())
    rows, flag_rows, ia_rows = [], [], []
    spreads = {}
    for gt in sorted(GT.glob("*.txt")):
        ref = words(gt.read_text())
        stem = gt.stem
        for m in models:
            f = BASE / m / gt.name
            if f.exists() and f.read_text().strip():
                c, w = cer_wer(words(f.read_text()), ref)
                rows.append({"page": stem, "model": m, "cer": c, "wer": w, "ref_words": len(ref)})
        fa, fb = BASE / model_a / gt.name, BASE / model_b / gt.name
        if fa.exists() and fb.exists():
            r = flag_eval(words(fa.read_text()), words(fb.read_text()), ref)
            flag_rows.append({"page": stem, "words": len(ref), **r})
        # archive.org: compare whole PDF page; Umrao images are spreads (R+L halves of one PDF page)
        key = stem.rstrip("RL")
        spreads.setdefault(key, []).append((stem, ref))
    for key, parts in spreads.items():
        parts.sort(key=lambda p: p[0].endswith("L"))  # right page first
        ref = [w for _, r in parts for w in r]
        ia = archive_org_words(parts[0][0])
        if ia is not None:
            c, w = cer_wer(ia, ref)
            ia_rows.append({"page": key, "halves": len(parts), "cer": c, "wer": w, "ref_words": len(ref)})

    # aggregate per model (weighted by ground-truth words)
    agg = {}
    for r in rows:
        a = agg.setdefault(r["model"], {"cer_w": 0, "wer_w": 0, "n": 0, "pages": 0})
        a["cer_w"] += r["cer"] * r["ref_words"]; a["wer_w"] += r["wer"] * r["ref_words"]
        a["n"] += r["ref_words"]; a["pages"] += 1
    if ia_rows:
        a = agg.setdefault("archive.org OCR", {"cer_w": 0, "wer_w": 0, "n": 0, "pages": 0})
        for r in ia_rows:
            a["cer_w"] += r["cer"] * r["ref_words"]; a["wer_w"] += r["wer"] * r["ref_words"]
            a["n"] += r["ref_words"]; a["pages"] += 1

    tot = {k: sum(r[k] for r in flag_rows) for k in ("words", "errors", "caught", "silent", "flagged_words")}
    out = ROOT / "out" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    md = ["# Evaluation against hand-verified ground truth", "",
          f"{len(set(r['page'] for r in rows))} pages, {tot['words']} words.", "",
          "## Accuracy (lower is better)", "", "| Engine | Pages | CER | WER |", "|---|---|---|---|"]
    for m, a in sorted(agg.items(), key=lambda kv: kv[1]["cer_w"] / kv[1]["n"]):
        md.append(f"| {m} | {a['pages']} | {a['cer_w']/a['n']:.2%} | {a['wer_w']/a['n']:.2%} |")
    md += ["", f"## Disagreement flagging (A = {model_a}, B = {model_b})", "",
           "| Page | Words | A's errors | Caught by flag | Silent | Words flagged |", "|---|---|---|---|---|---|"]
    for r in flag_rows:
        md.append(f"| {r['page']} | {r['words']} | {r['errors']} | {r['caught']} | {r['silent']} | {r['flagged_words']} ({r['burden']:.1%}) |")
    if tot["errors"]:
        md.append(f"| **Total** | {tot['words']} | {tot['errors']} | {tot['caught']} ({tot['caught']/tot['errors']:.0%}) | "
                  f"{tot['silent']} | {tot['flagged_words']} ({tot['flagged_words']/max(1,tot['words']):.1%}) |")
    md += ["", "### Silent errors (wrong, but both models agreed)", ""]
    for r in flag_rows:
        for m in r["missed"]:
            md.append(f"- {r['page']}: model `{m['model']}` → truth `{m['truth']}`")
    (out / "report.md").write_text("\n".join(md) + "\n")
    (out / "report.json").write_text(json.dumps({"per_page": rows, "flagging": flag_rows, "archive_org": ia_rows,
                                                 "totals": tot}, ensure_ascii=False, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:])
