"""Whole-book pipeline: scanned PDF -> per-page transcriptions from two models -> disagreement flags.

  python -m src.book data/scans/umrao.pdf --pages 2-100
  python -m src.book data/scans/toba.pdf --pages 10-30 --mask-bottom 0.06

Re-running is safe: every finished step is on disk and is skipped, so an interrupted or
quota-limited run resumes where it stopped. Failed pages are simply retried next time.

Output in out/books/<book>/:
  pages/<id>.png                 cleaned single pages (spreads split, right page first)
  text/<engine>/<id>.txt         raw transcription from each model
  compare/<id>.json              A's text with B's disagreements marked, per line
  runs.jsonl                     one record per model call: seconds, tokens, status
  status.json                    summary: coverage, failures, time, tokens, flag rate
"""
import argparse, json, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.prep import prep  # noqa: E402
from src.compare import compare  # noqa: E402
from src.engines import load_env, transcribe, dirname, QuotaExhausted  # noqa: E402

DEFAULT_A = "gemini:gemini-3.1-flash-lite"
DEFAULT_B = "gemini:gemini-3.5-flash-lite,gemini:gemma-4-31b-it"  # see docs/checker-choice.md
_lock = threading.Lock()


def page_range(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def order_key(path: Path):
    """umrao-012R before umrao-012L (Urdu reads right to left)."""
    m = re.search(r"-(\d+)([RL]?)$", path.stem)
    return (int(m.group(1)), {"R": 0, "": 0, "L": 1}[m.group(2)]) if m else (0, 0)


def log(msg):
    with _lock:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


class Engine:
    def __init__(self, spec, book_dir, runs):
        self.spec = spec
        self.dir = book_dir / "text" / dirname(spec)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.runs = runs
        self.stopped = threading.Event()  # set when the daily quota is gone
        self.done = self.failed = 0

    def run(self, img: Path, attempts=2):
        dest = self.dir / f"{img.stem}.txt"
        if dest.exists() or self.stopped.is_set():
            return
        for attempt in range(1, attempts + 1):
            t = time.time()
            try:
                text, usage = transcribe(self.spec, img)
                dest.write_text(text)
                status = "ok"
            except QuotaExhausted as e:
                usage, status = None, f"quota: {e}"
                self.stopped.set()
            except Exception as e:  # noqa: BLE001 - every failure is recorded, never swallowed
                usage, status = None, f"error: {e}"
            dt = round(time.time() - t, 1)
            with _lock:
                self.runs.write(json.dumps({"model": self.spec, "page": img.stem, "sec": dt, "status": status,
                                            "attempt": attempt, "usage": usage, "ts": time.time()}) + "\n")
                self.runs.flush()
            log(f"{self.spec:32s} {img.stem:14s} {dt:6.1f}s {status[:100]}")
            if status == "ok":
                self.done += 1
                return
            if self.stopped.is_set():
                log(f"{self.spec}: daily quota exhausted, stopping this engine (re-run tomorrow to resume)")
                return
        self.failed += 1


def summarize(book_dir: Path, images, engines, wall):
    ids = [p.stem for p in images]
    have = {e.spec: {p.stem for p in e.dir.glob("*.txt")} for e in engines}
    words = flagged = lines = flagged_lines = fallback = 0
    for i in ids:
        f = book_dir / "compare" / f"{i}.json"
        if f.exists():
            d = json.loads(f.read_text())
            s = d["stats"]
            words += s["words"]; flagged += s["flagged_words"]
            lines += s["lines"]; flagged_lines += s["flagged_lines"]
            fallback += bool(d.get("fallback"))
    usage = {}
    for line in (book_dir / "runs.jsonl").read_text().splitlines():
        r = json.loads(line)
        u = usage.setdefault(r["model"], {"calls": 0, "ok": 0, "sec_ok": 0.0, "in_tokens": 0, "out_tokens": 0})
        u["calls"] += 1
        if r["status"] == "ok":
            u["ok"] += 1
            u["sec_ok"] = round(u["sec_ok"] + r["sec"], 1)
            m = r.get("usage") or {}
            u["in_tokens"] += m.get("promptTokenCount", m.get("prompt_tokens", 0)) or 0
            u["out_tokens"] += (m.get("candidatesTokenCount", m.get("completion_tokens", 0)) or 0) + \
                               (m.get("thoughtsTokenCount") or 0)
    st = {
        "pages": len(ids),
        "transcribed": {k: len(v & set(ids)) for k, v in have.items()},
        "missing": {k: sorted(set(ids) - v) for k, v in have.items()},
        "compared": sum((book_dir / "compare" / f"{i}.json").exists() for i in ids),
        "fallback_pages": fallback,
        "words": words, "flagged_words": flagged,
        "flag_rate": round(flagged / max(1, words), 4),
        "lines": lines, "flagged_lines": flagged_lines,
        "last_run_wall_sec": round(wall, 1),
        "usage_all_runs": usage,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (book_dir / "status.json").write_text(json.dumps(st, ensure_ascii=False, indent=1))
    return st


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--pages", required=True, help="PDF pages, e.g. 2-100 or 5,9,20-30")
    ap.add_argument("--a", default=DEFAULT_A, help="primary model (its text is the output)")
    ap.add_argument("--b", default=DEFAULT_B,
                    help="checker model(s), comma-separated; a word is flagged if any checker disagrees")
    ap.add_argument("--workers-a", type=int, default=2)
    ap.add_argument("--workers-b", default="4", help="workers per checker, comma-separated or one number")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--mask-bottom", type=float, default=0.0)
    args = ap.parse_args()
    load_env()
    checker_specs = [c.strip() for c in args.b.split(",") if c.strip()]
    wb = [int(x) for x in args.workers_b.split(",")]
    wb = (wb * len(checker_specs))[:len(checker_specs)] if len(wb) == 1 else wb

    book_dir = ROOT / "out" / "books" / args.pdf.stem
    pages_dir = book_dir / "pages"
    t0 = time.time()

    # 1+2. Prepare each page image, then hand it straight to every model (each engine has its own
    # worker pool and quota), so transcription starts while later pages are still being rendered.
    images = []
    with (book_dir / "runs.jsonl").open("a") as runs:
        a = Engine(args.a, book_dir, runs)
        checkers = [Engine(c, book_dir, runs) for c in checker_specs]
        pools = [ThreadPoolExecutor(args.workers_a)] + [ThreadPoolExecutor(w) for w in wb]
        try:
            futs = []
            for n in page_range(args.pages):
                ready = sorted(pages_dir.glob(f"{args.pdf.stem}-{n:03d}*.png"), key=order_key)
                if not ready:
                    ready = prep(args.pdf, [n], args.dpi, args.mask_bottom, out_dir=pages_dir)
                    log("prep " + " ".join(p.name for p in ready))
                for img in ready:
                    images.append(img)
                    futs += [pool.submit(e.run, img) for pool, e in zip(pools, [a] + checkers)]
            log(f"{len(images)} page images ready")
            for f in futs:
                f.result()
        finally:
            for pool in pools:
                pool.shutdown()

    # 3. Compare A against every checker that has the page. If A refused or failed the page
    # (e.g. RECITATION on famous text), the first checker with a text becomes the primary and is
    # flagged against the remaining checkers; the page is marked as fallback.
    (book_dir / "compare").mkdir(exist_ok=True)
    for img in images:
        texts = [(e.spec, e.dir / f"{img.stem}.txt") for e in [a] + checkers]
        texts = [(spec, f) for spec, f in texts if f.exists()]
        if len(texts) < 2:
            (book_dir / "compare" / f"{img.stem}.json").unlink(missing_ok=True)  # stale result from other models
            continue
        (primary, fa), rest = texts[0], texts[1:]
        lines, stats = compare(fa.read_text(), *(f.read_text() for _, f in rest))
        (book_dir / "compare" / f"{img.stem}.json").write_text(json.dumps(
            {"page": img.stem, "a": primary, "b": [spec for spec, _ in rest], "fallback": primary != args.a,
             "stats": stats, "lines": lines}, ensure_ascii=False))

    st = summarize(book_dir, images, [a] + checkers, time.time() - t0)
    log("done this run: " + "; ".join(f"{e.spec} +{e.done} ok / {e.failed} failed" for e in [a] + checkers))
    log("status: " + json.dumps({k: st[k] for k in ("pages", "transcribed", "compared", "fallback_pages", "flag_rate")}))
    missing = sum(len(v) for v in st["missing"].values())
    if missing:
        log(f"{missing} transcriptions still missing; re-run the same command to retry them")


if __name__ == "__main__":
    main()
