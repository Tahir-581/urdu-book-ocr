# AI usage log

Daily human notes. Full Claude Code transcripts: `~/.claude/projects/-home-tahir-Tahir-19-MUST-Quest/*.jsonl` (exported at the end).

## Day 0: 2026-11-17 (choosing the problem)

- Asked Claude to analyse the quest brief. It read my CV/LinkedIn and project folders to suggest problems that fit my background.
- Rejected ideas: Punjabi voice-note orders, Urdu OCR (first pass), hardware unlocks, Reel auto-edit. My pushback: "AI can do all these 4 things perfectly."
- Claude's reframe: the quest title is "Use Your *Superpower*." Impossible means impossible for one person in 5 days without AI, not impossible for AI. The hard part is the system around the model call (reliability, scale, real use).
- Picked: scanned Urdu books → trustworthy text. Reason: I personally hit this as a reader/creator; there's a measurable target; it continues my OCR + Urdu-AI work.

## Day 1: 2026-11-18

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
- **Changed my success metric:** intent.md said "flag ≤ 25% of lines". On Nastaliq, up to 68% of lines contain at least one disagreement, but only 3 to 8% of *words* do. Word-level flagging is the honest unit.
- Agreement between Gemini 3.5 Flash and 3.1 Flash-Lite: Naskh pages 95 to 98.5%, Nastaliq pages 92 to 98%.
- **What failed:** Gemini 3.5 Flash returned **empty text with HTTP 200** for page 51 (it opens with a famous couplet). The script saved it as a successful result. A retry worked, so it's intermittent. Fix: empty output is now an error, never a result. Silent failures matter more than loud ones.
- New hard cases in the set: bleed-through from the back of the page (Taubat p.219), and poetry couplets with speaker labels (Umrao p.21).
- Built `scripts/review.py`: a ground-truth review page (scan | editable text, disagreements highlighted). Next: I hand-correct 15 pages.

## Day 2: 2026-11-19

### Ground truth + first evaluation
- I hand-corrected 8 pages (2 Naskh, 6 Nastaliq; 2,220 words) using the review page. I had no Urdu keyboard on Linux, so Claude added a phonetic Urdu layout (CRULP) and changed the review page so a click on a flagged word picks model A / model B / type-your-own. Most fixes became one click.
- Claude wrote `src/evaluate.py`: CER/WER per engine, plus how many of model A's errors the A-vs-B disagreement actually caught.
- First numbers (before archive.org baseline):
  - Gemini 3.5 Flash: CER 0.56%, WER 1.67%.
  - Gemini 3.1 Flash-Lite: CER 1.30%, WER 3.47%.
  - Nemotron (free): CER 24%.
  - Disagreement flagging caught 28 of 30 of Flash's errors while flagging only 3.5% of words.
- **What failed (tool):** the first version of the review page kept a literal `+` from "only model B has this" words in the downloaded text. Caught when it showed up as a fake "silent error"; fixed in the file and the tool.
- **What failed (me):** one "silent error" was actually *my* ground-truth mistake. I wrote `دور`; the scan clearly shows `ڈور` (kite string). In another spot the models disagreed (`تلکل` vs `نکل`) and I picked A's reading, but the scan looks like `تکل`.
- **Unlearned:** "the human is the ground truth." A human reviewer choosing between two model readings anchors on them. The fix: zoomed crops for flagged words, and a second pass on disagreements where the reviewer picked a model reading.

### Whole-book runner + reader (evening)
- Claude wrote `src/book.py`: one command converts a PDF range (prep → both models in parallel → compare). Everything finished is on disk, so a crash or quota stop resumes on re-run. Every call is logged with time and tokens (`runs.jsonl`, `status.json`).
- Model calls moved into `src/engines.py`. A 429 that says the *daily* quota is gone now stops that model cleanly instead of retrying all night; other 429s respect Google's `retryDelay`; timeouts are retried.
- Smoke test (Umrao PDF page 3, two pages): works, 1.6% of words flagged. But Gemini 3.5 Flash took **~5 minutes per page** under load (two read timeouts, then 503 "high demand") versus ~55 s yesterday. Flash-Lite: ~18 s. Free-tier latency swings 5×, so "time per book" has to be reported as a range.
- **What failed (pipeline design):** the first full run rendered all 99 spreads before sending any page to a model (~9 s each, ~15 min idle). Restarted so each page goes to the models as soon as it's rendered; already-rendered pages were reused.
- Full *Umrao Jaan Ada* run started: PDF pages 2 to 100 (page 1 is the cover) = 198 pages.
- Claude wrote `scripts/reader.py`: a static reader site (scan | text, flagged words highlighted with the other model's reading on tap, full-text search that folds ھ/ہ etc., `.txt` and "text with flags" downloads, phone layout). Checked with headless Chrome screenshots on desktop and phone width.

### Quota wall → choosing a free checker (night)
- **What failed:** the full run finished Flash-Lite (192/198 pages, ~35 min) but Gemini 3.5 Flash stopped after 3 pages: its free tier is **20 requests/day**, and the earlier 503/timeout retries counted against it. 198 pages would take 10 days.
- Also: Flash-Lite refused 6 pages with `finishReason=RECITATION`. Google's copyright filter treats *Umrao Jaan Ada* as famous text it must not reproduce, even though it's public domain. A transcription system for classics has to plan around the model refusing the most famous pages.
- Options I was given: pay ~$7 on OpenRouter for Flash, enable Google billing, or stay free with Flash-Lite as the primary. **I chose to stay free.**
- Tested free checkers on the 8 ground-truth pages (`docs/checker-choice.md`). **Unlearned:** I expected "a second model" to be enough. Gemini 3.5 Flash-Lite as checker caught only 63% of 3.1 Flash-Lite's errors: same family, same mistakes, so they agree on them. Gemini 3 Flash preview is worse on its own (CER 1.64% vs 1.26%) yet caught 85% (3.2% of words flagged). The checker's value is *failing differently*, not being more accurate.
- The evaluator took >10 min with 6 models (pure-Python edit distance). Claude replaced it with a bit-parallel algorithm, checked against the old one on 3,000 random cases: 1.6 s.
- Restarted the book run: A = 3.1 Flash-Lite (reused), B = 3 Flash preview.
- **What failed (again):** 3 Flash preview hit the same 20/day cap after 13 book pages. Every Gemini "Flash" model is capped at 20/day on the free tier; only the Flash-Lite models and Gemma have room for a whole book. Gemma via OpenRouter's free pool: 429 on every page.
- Gemma 4 31B alone catches 70% (but flags 8%); 3.5 Flash-Lite alone 63%. They miss *different* errors, so Claude extended the comparison to flag a word when **any** checker disagrees: together they catch 80% at 9.1% of words flagged. That's the free configuration for the book. The honest trade-off for the write-up: free = a reader checks ~9% of words; ~$7 of Gemini 3.5 Flash = 100% caught at 3.5%.
- RECITATION pages: the first checker's text becomes the page's text and is flagged against the other checker; the reader marks those pages as "text from fallback model".
- Book run restarted overnight with this setup (Gemma is the slow part, 2 to 6 min/page).

## Day 3 to 4: 2026-11-20 to 2026-11-21

- The overnight book run kept going on free quotas. By the end, both Flash-Lite models had 197 of 198 pages. Gemma 4 had only 95: most of its calls (531 in total) ended in 503 "high demand" retries, at about 6 minutes per successful page.
- I reviewed 6 more ground-truth pages (4 Naskh, 2 Nastaliq) and approved the model draft unchanged after checking each one against the scan. That gives 14 pages and 2,803 words, more Naskh coverage than the first 8 (which were mostly Nastaliq).
- **Caveat I'm stating openly:** pages approved without edits can only show errors where the model draft differed from what I approved. If I missed an error that matched the draft, it counts as correct. This is the anchoring problem from day 2 again. A second reviewer would fix it.
- Re-ran the evaluation on all 14 pages with the final free setup (A = 3.1 Flash-Lite, checkers = 3.5 Flash-Lite + Gemma 4): **84% of errors caught (52/62), 8.7% of words flagged.** It still meets the 80% target with more pages.

## Day 5: 2026-11-22 (submission)

- Resumed the book run for Gemma's remaining pages, then rebuilt the reader.
- Claude wrote `directive.md` (what changed from intent.md and why) and `WRITEUP.md` (problem, results, unlearning, AI usage, failures), updated the README, and published the reader on GitHub Pages.
- **What failed (small):** the resume command failed at first with exit code 127, because `python` doesn't exist on this machine (only `python3`) and the old virtualenv was gone. Reran with `python3`.
- I removed every em dash from the docs and the reader output. That included a punctuation-only edit to `intent.md`; its wording is unchanged.
