# urdu-book-ocr

Scanned Urdu books → trustworthy, searchable text.

Most Urdu books online are image-only scans, and the OCR text that does exist (e.g. archive.org's) is gibberish. This project turns a whole scanned book into a clean Unicode text edition. Multiple vision models transcribe each page independently, and lines where they disagree are flagged for review instead of silently guessed.

Built in 5 days with AI as the default way of working. See [`intent.md`](intent.md) for the plan and [`log/LOG.md`](log/LOG.md) for the daily AI usage log.

Status: day 1. Pipeline in progress.
