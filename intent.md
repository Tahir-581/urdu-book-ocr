# intent.md: Harf: scanned Urdu books → trustworthy text

> Written on day 1 (2026-11-18), before building. This file stays frozen; what changed is recorded in `directive.md` and the write-up.

## The problem

Most Urdu books (novels, classics, out-of-print literature) exist online only as **scanned page images**. You can read them, but you cannot search them, copy a line, quote them, listen to them with TTS, or feed them to any language tool.

"Searchable" versions exist, but they aren't usable. archive.org already ran OCR on the two books I picked. A line from *Taubat-un-Nasuh* (Deputy Nazir Ahmad, 1874) as archive.org stores it:

```
مواخذۂ عابتکا نص و( نڑھا ۔ کر نے ان
```

That is gibberish. Dedicated Urdu OCR tools exist (CLE Urdu OCR, i2OCR, Tesseract `urd`, research models like UTRNet), yet the books are still scans. The bottleneck isn't "no OCR exists." **No tool turns a whole book into a text edition you can trust, cheaply, without hours of manual proofreading.**

## Who has it

- Readers who want to search or quote an Urdu book (me included; I make Urdu book content).
- Students and researchers working with Urdu literature.
- Anyone building Urdu AI (TTS, search, LLMs), which all need clean text.

## Why it's hard (and not just "send the page to an LLM")

1. **Typefaces vary.** Nastaliq is cursive, with stacked letters on a slanting baseline. Older Naskh-style prints come with noise, skew and bleed-through.
2. **Real scans are messy.** Two-page spreads, watermarks (e.g. `Marfat.com`), page numbers, running headers and footnotes all have to be handled.
3. **Vision LLMs hallucinate.** They quietly "correct" words and autocomplete well-known text. In literature, a confident wrong word is worse than a visible gap.
4. **It has to work at book scale.** That means 100 to 500 pages with consistent output, on free-tier limits.
5. **Copy-pasted Urdu often breaks.** Right-to-left order and letter shaping are frequently wrong in PDF text layers.

## What I will build (in 5 days)

A pipeline plus a reader:

**scanned PDF in → page cleanup (split spreads, crop, deskew) → independent transcriptions from 2+ models → line-level agreement check → clean Unicode text with uncertain lines flagged → web reader (scan beside text, search) + EPUB/TXT export.**

### Must (by day 3)
- Pipeline runs on both test books.
- 15+ hand-verified ground-truth pages covering both typefaces.
- Baseline table: archive.org OCR vs. each raw model vs. my pipeline, measured as character error rate (CER).
- Disagreement flagging: uncertain lines are marked, not silently guessed.

### Should (by day 4)
- Web reader: scan | text side by side, full-text search, flagged lines highlighted.
- One full public-domain novel converted end to end and published.
- Cost and time per book reported.

### Could
- Searchable PDF with an invisible Urdu text layer that copies correctly.
- Poetry layout preserved.

## How I'll know it works (success criteria)

- Pipeline CER is **lower than the best single raw model** on the ground-truth set.
- Flagging catches **≥ 80% of lines that contain errors** while flagging **≤ 25% of all lines**. A reviewer then only checks the flagged lines.
- One full book is converted on free-tier APIs, with cost and time reported.

Numbers for each baseline will be measured on day 1 to 2 and reported honestly, including where the pipeline doesn't win.

## How I'll use AI

- **As the builder:** Claude Code writes and refactors the pipeline. I direct, review and test.
- **As the engine:** Gemini (free API) and vision models through OpenRouter do the transcription. Disagreement between them is the signal.
- **As the critic:** a model acts as a checker on flagged lines. It never overwrites text it isn't sure about.
- **I stay the judge:** I'm a native Urdu reader. I build the ground truth and decide what counts as an error.

Every session is logged in `log/` (daily notes + Claude Code transcripts).

## Constraints

- About 4 days remaining; solo.
- Free Gemini API + OpenRouter only. No GPU, no fine-tuning.
- **Public-domain books only** (authors who died over 50 years ago): *Taubat-un-Nasuh* (Nazir Ahmad, d. 1912), *Umrao Jaan Ada* (Mirza Hadi Ruswa, d. 1931).

## What I'm not doing

- Training an OCR model.
- Claiming 100% accuracy. The goal is "trustworthy + tells you where to look," not "perfect."
- Handwritten manuscripts.
