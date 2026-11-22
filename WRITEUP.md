# Write-up: scanned Urdu books to trustworthy text

**Demo:** https://tahir-581.github.io/urdu-book-ocr/ (full *Umrao Jaan Ada*, 198 pages)
**Repo:** https://github.com/Tahir-581/urdu-book-ocr
**Plan vs. result:** [`intent.md`](intent.md) (frozen day 1) and [`directive.md`](directive.md) (what it became)
**AI usage log:** [`log/LOG.md`](log/LOG.md)

## 1. The problem

Most Urdu literature online exists only as scanned page images. You cannot search it, quote it, run TTS on it, or use it to build Urdu language tools. The "searchable" versions are not usable: archive.org's OCR of the two test books has a **character error rate of 50%** and a word error rate of 82%. Example line from *Taubat-un-Nasuh*:

```
مواخذۂ عابتکا نص و( نڑھا ۔ کر نے ان
```

Vision LLMs read these pages far better, but they fail in the worst possible way: **fluently**. A wrong word looks exactly like a right one. In literature a confident wrong word is worse than a visible gap. So the real problem is not "OCR a page"; it is "convert a whole book, for free, and tell the reader exactly which words to doubt."

## 2. What I built

```
scanned PDF -> page prep (split spreads, mask watermark)
            -> primary model transcribes  (Gemini 3.1 Flash-Lite)
            -> checker models transcribe   (Gemini 3.5 Flash-Lite, Gemma 4 31B)
            -> fold spelling variants, align word by word
            -> flag a word if ANY checker disagrees
            -> static reader: scan | text, flags, search, TXT export
```

- `src/prep.py`: page cleanup. `src/engines.py`: model calls with quota-aware retries. `src/compare.py`: word alignment and flags. `src/book.py`: resumable whole-book runner with per-call time and token logs. `src/evaluate.py`: CER/WER and flag recall against ground truth.
- `scripts/review.py`: ground-truth review page (click a flagged word to pick a reading, phonetic Urdu keyboard). `scripts/reader.py`: the public reader.

## 3. Results

Ground truth: **14 hand-verified pages, 2,803 words**, both typefaces (6 Naskh pages from *Taubat-un-Nasuh*, 8 Nastaliq pages from *Umrao Jaan Ada*).

| Engine | Pages | CER | WER |
|---|---|---|---|
| Gemini 3.5 Flash (20 req/day free) | 14 | 0.29% | 0.88% |
| **Gemini 3.1 Flash-Lite (primary)** | 14 | **1.17%** | 2.99% |
| Gemini 3.5 Flash-Lite (checker) | 14 | 1.29% | 3.89% |
| Gemini 3 Flash preview | 8 | 1.64% | 2.52% |
| Gemma 4 31B (checker) | 10 | 4.16% | 9.10% |
| Nemotron 3.5 VL (OpenRouter free) | 2 | 24.06% | 47.14% |
| archive.org OCR | 10 | 50.43% | 81.72% |

**Flagging (the actual product):** the free setup flags **8.7% of words** and those flags contain **84% of the primary's errors** (52 of 62). Target in intent.md was at least 80%. Met.

**Full book:** *Umrao Jaan Ada*, 198 pages, 68,066 words, $0. Primary model about 21 s/page; checker 3.5 Flash-Lite about 12 s/page; Gemma 4 about 6 min/page under free-tier load. The two Flash-Lite passes finish a book in under an hour; Gemma is the bottleneck and its free pool spent most of the run returning 503.

**Not met:** intent.md said the pipeline's CER would beat the best single model. It does not: the best model (Gemini 3.5 Flash) is only usable for 20 pages a day for free. Paying about $7 for it would give 100% caught at 3.7% flagged on the original 8 pages.

**Known blind spot:** of the 10 errors that slip through, several are izafat and hamza marks (`ذرۂ` read as `ذرہ`) and old spellings (`رزیل` vs `رذیل`). All models drop or modernise them the same way, so disagreement cannot catch them.

## 4. What I unlearned

1. **"AI can do this perfectly."** On clean print the best model nearly can. The hard part is knowing *when* not to trust it, because bad outputs look as fluent as good ones. Nemotron turned "your" into "commercial" in perfect Urdu.
2. **"No tools exist."** Wrong. CLE Urdu OCR, UTRNet, i2OCR all exist. The gap is trust and book scale, so I reframed the problem on day 1.
3. **"A second model is a check."** A checker from the same family caught only 63% of errors; they share mistakes and agree on them. A *less accurate* model from another line (3 Flash preview, CER 1.64%) caught 85%. A checker's value is failing differently, not being better.
4. **"Line-level flags."** Nastaliq pages had disagreements on up to 68% of lines but only 3 to 8% of words. The honest unit is the word.
5. **"The human is the ground truth."** I wrote `دور` where the scan clearly says `ڈور`, and when shown two model readings I tended to pick one of them even when both were wrong. A reviewer choosing between machine options anchors on them.
6. **"Free tier means slow but possible."** Free tier means hard daily caps (20/day on every Gemini Flash model, retries included), 5x latency swings, and copyright refusals on public-domain classics. The pipeline design had to be shaped around quotas, not around accuracy alone.

## 5. How I used AI

- **Builder (Claude Code):** wrote and refactored all of the pipeline, the evaluator, the review tool and the reader; searched for existing tools and public-domain scans; replaced a 10-minute pure-Python edit distance with a bit-parallel version (1.6 s, checked against the old one on 3,000 random cases); screenshotted the reader in headless Chrome at desktop and phone widths.
- **Engine:** Gemini and Gemma models do the transcription. Their disagreement is the trust signal.
- **Critic:** checker models never overwrite the primary text; they only mark where to look.
- **Me:** I chose the problem, rejected AI's first suggestions, made the cost decisions (stay free, accept 8.7% flagged instead of paying), read Urdu, and built the ground truth. I decided what counts as an error.

## 6. What failed

- First baseline: almost every model call failed (Pro has no free quota, Flash returned 503, OpenRouter free pool 429, a model had been retired). Retries and fallbacks became part of the design.
- Gemini 3.5 Flash returned **empty text with HTTP 200** on a page opening with a famous couplet, and my script saved it as success. Empty output is now an error.
- The review tool leaked a literal `+` marker into ground truth; caught because it showed up as a fake "silent error".
- My own ground-truth mistakes (see unlearning 5).
- The first book run rendered all 99 spreads before calling any model (15 idle minutes). Rewritten to stream.
- Gemini 3.5 Flash, then 3 Flash preview, both hit the 20/day cap mid-book. Two checker plans died before the final one.
- Flash-Lite refused 6 pages of *Umrao Jaan Ada* with `RECITATION` (copyright filter on a public-domain novel).
- Gemma 4: OpenRouter's free pool failed on every page; via the Gemini API it worked but spent most calls on 503 retries (97 of 198 pages checked after the final resume on day 5).

## 7. Reproduce

```
python3 -m src.book data/scans/umrao.pdf --pages 2-100
python3 scripts/reader.py umrao --title "امراؤ جان ادا" --author "مرزا ہادی رسوا"
python3 -m src.evaluate gemini__gemini-3.1-flash-lite gemini__gemini-3.5-flash-lite gemini__gemma-4-31b-it
```

API keys go in `.env` (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`).
