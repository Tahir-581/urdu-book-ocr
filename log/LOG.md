# AI usage log

Daily human notes. Full Claude Code transcripts: `~/.claude/projects/-home-tahir-Tahir-19-MUST-Quest/*.jsonl` (exported at the end).

## Day 0 — 2026-11-17 (choosing the problem)

- Asked Claude to analyse the quest brief. It read my CV/LinkedIn and project folders to suggest problems that fit my background.
- Rejected ideas: Punjabi voice-note orders, Urdu OCR (first pass), hardware unlocks, Reel auto-edit. My pushback: "AI can do all these 4 things perfectly."
- Claude's reframe: the quest title is "Use Your *Superpower*." Impossible means impossible for one person in 5 days without AI, not impossible for AI. The hard part is the system around the model call (reliability, scale, real use).
- Picked: scanned Urdu books → trustworthy text. Reason: I personally hit this as a reader/creator; there's a measurable target; it continues my OCR + Urdu-AI work.

## Day 1 — 2026-11-18

- Claude searched for existing tools. Found CLE Urdu OCR, i2OCR, UTRNet, eScriptorium. **Unlearned:** my claim that "no tools exist" was wrong. The real gap is trust and book scale, so I reframed the problem in intent.md.
- Found public-domain scans on archive.org: *Taubat-un-Nasuh* (475 pp, Naskh-style print, Marfat.com watermark) and *Umrao Jaan Ada* (100 images, Nastaliq, two-page spreads).
- **Key evidence:** archive.org's existing OCR text for both books is gibberish. The "searchable" layer is unusable.
- APIs chosen: Gemini free tier + OpenRouter.
- Repo made public with intent.md frozen: https://github.com/Tahir-581/urdu-book-ocr

### First baseline run (5 pages × 4 models)
- **What failed:** most calls failed on the first try.
  - Gemini 3.1 Pro: `429 quota exceeded` (free tier has no Pro quota).
  - Gemini 3.8 Flash: `503 high demand`.
  - Gemma 4 on OpenRouter free: `429` (shared free pool).
  - Gemini 2.5 Flash: no longer available.
  - Lesson: retries with backoff and model fallbacks have to be part of the pipeline, not an afterthought. Added exponential backoff to `baseline.py`.
- Working models: Gemini 3.5 Flash (slow, ~75 s with retries), Gemini 3.1 Flash-Lite (~6 s), Nemotron 3.5 VL free (slow).
- **Page 149 of Taubat-un-Nasuh (Naskh print):**
  - Gemini 3.5 Flash: essentially perfect, and keeps the book's original spelling (`ھو`, `ھے`).
  - Gemini 3.1 Flash-Lite: looks perfect but silently modernizes `ھے → ہے` on every line, drops a word (`اور میں ان کے → اور ان کے`), and misreads `چوں کہ → چوب کہ`.
  - Nemotron: fluent nonsense (`تمہاری` "your" → `تجارتی` "commercial"; page 149 → "189"). It reads like real Urdu, which is the dangerous kind of hallucination.
- **Unlearned:** I assumed "AI can do this perfectly." On clean print, the best model nearly can. The hard part is knowing *when* a model can't be trusted, because the bad outputs look just as fluent as the good ones.
- **Design decisions from this:**
  1. Use model disagreement as the trust signal. Flash and Flash-Lite disagreed exactly at Flash-Lite's errors.
  2. Normalize spelling variants (ھ/ہ, quote styles) *before* comparing, so style differences don't flag every line. Keep the book's original spelling in the output.

### Batch 2 (15 pages total, 2 models) + review tool
- Built `src/prep.py`: splits two-page spreads at the gutter (right page first) and blanks the bottom watermark band.
- Built `src/compare.py`: word-level alignment of two transcriptions after folding spelling variants (ھ/ہ, ی/ي, quote styles). With folding, page 149 dropped to 4 real disagreements.
- **Changed my success metric:** intent.md said "flag ≤ 25% of lines". On Nastaliq, up to 68% of lines contain at least one disagreement, but only 3–8% of *words* do. Word-level flagging is the honest unit.
- Agreement between Gemini 3.5 Flash and 3.1 Flash-Lite: Naskh pages 95–98.5%, Nastaliq pages 92–98%.
- **What failed:** Gemini 3.5 Flash returned **empty text with HTTP 200** for page 51 (it opens with a famous couplet). The script saved it as a successful result. A retry worked, so it's intermittent. Fix: empty output is now an error, never a result. Silent failures matter more than loud ones.
- New hard cases in the set: bleed-through from the back of the page (Taubat p.219), and poetry couplets with speaker labels (Umrao p.21).
- Built `scripts/review.py`: a ground-truth review page (scan | editable text, disagreements highlighted). Next: I hand-correct 15 pages.
