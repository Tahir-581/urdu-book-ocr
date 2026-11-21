# urdu-book-ocr

Scanned Urdu books → trustworthy, searchable text.

**Live reader:** https://tahir-581.github.io/urdu-book-ocr/ (*Umrao Jaan Ada*, 198 pages, scan beside text, flagged words highlighted, search, TXT download)

Most Urdu books online are image-only scans, and the OCR text that does exist (e.g. archive.org's, 50% character error rate) is gibberish. This project turns a whole scanned book into a clean Unicode text edition. A primary vision model transcribes each page, checker models from different families transcribe it again, and every word where they disagree is flagged for the reader instead of silently guessed.

## Results (14 hand-verified pages, 2,803 words)

| | CER | WER |
|---|---|---|
| archive.org OCR | 50.43% | 81.72% |
| Gemini 3.1 Flash-Lite (primary, free) | 1.17% | 2.99% |
| Gemini 3.5 Flash (best, 20 req/day free) | 0.29% | 0.88% |

Flags cover **84% of the primary's errors while marking 8.7% of words**, using free-tier APIs only. A full 198-page novel cost $0.

## Read more

- [`WRITEUP.md`](WRITEUP.md): problem, results, what I unlearned, how I used AI, what failed
- [`intent.md`](intent.md): the plan, frozen on day 1
- [`directive.md`](directive.md): what the plan became, and why
- [`log/LOG.md`](log/LOG.md): daily AI usage log
- [`docs/checker-choice.md`](docs/checker-choice.md): why the checker must fail differently
- [`docs/eval-final.md`](docs/eval-final.md): full evaluation, per page, with every silent error

## Run it

```
pip install pillow                    # plus poppler-utils (pdftoppm)
echo "GEMINI_API_KEY=..." > .env
python3 -m src.book data/scans/umrao.pdf --pages 2-100     # resumable
python3 scripts/reader.py umrao --title "امراؤ جان ادا" --author "مرزا ہادی رسوا"
python3 -m src.evaluate gemini__gemini-3.1-flash-lite gemini__gemini-3.5-flash-lite gemini__gemma-4-31b-it
```

Built in 5 days with AI (Claude Code) as the default way of working.
