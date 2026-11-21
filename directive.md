# directive.md: what the plan became

`intent.md` was written on day 1, before any code. This file records what actually got built, what changed, and why. Every change was forced by a measurement, not a preference.

## Final directive

Turn a scanned Urdu book into a Unicode text edition that **tells the reader where not to trust it**, using only free-tier APIs:

1. Clean each page (split two-page spreads, mask watermarks).
2. Transcribe each page with a primary model (Gemini 3.1 Flash-Lite). Its text is the edition.
3. Transcribe it again with checker models that fail differently (Gemini 3.5 Flash-Lite and Gemma 4 31B).
4. Fold spelling variants (ھ/ہ, ی/ي, quote styles), align word by word, and flag every word where **any** checker disagrees.
5. Publish a static reader: scan beside text, flagged words highlighted with the checker's reading, full-text search, TXT downloads.

Success means: errors in the primary text are caught by flags at a rate of at least 80%, while the reader has to check only a small share of words.

## What changed from intent.md, and why

| intent.md said | What happened | Why |
|---|---|---|
| Flag uncertain **lines**, at most 25% of lines | Flag uncertain **words** | On Nastaliq up to 68% of lines contain one disagreement, but only 3 to 8% of words do. Line flags would ask the reader to check almost everything. |
| Best model = primary text | Gemini 3.5 Flash (CER 0.29%) could not be used for the book | Every Gemini "Flash" model is capped at 20 requests/day on the free tier, and retries count. A 198-page book would take 10 days. |
| "2+ models" is enough | The checker must come from a **different family**, and two weak checkers are combined | A same-family checker caught only 63% of the primary's errors: the models make the same mistakes and agree on them. Two different checkers together reach 84%. |
| Pipeline CER lower than the best single model | Not met, stated honestly | The free primary (1.17% CER) is worse than paid-tier-only Gemini 3.5 Flash (0.29%). The pipeline's value is the flags, not lower raw CER. |
| One full novel published | *Umrao Jaan Ada*, 198 pages, published in the reader | Done. Gemma's slow free quota means part of the book is checked by one checker only; the reader shows this. |
| Searchable PDF (could) | Dropped | Time went to the quota problem and evaluation instead. |
| Poetry layout (could) | Dropped | Couplets come out as lines; layout is not preserved. |

## New failure modes the directive now handles

- **Empty text with HTTP 200.** Treated as a failure, never as a result.
- **Daily quota exhaustion.** A daily-quota 429 stops that model cleanly; other 429s respect `retryDelay`. Runs are resumable from disk.
- **RECITATION refusals.** Google refuses some pages of a famous public-domain novel as "recitation". The first checker's text becomes the page text and the page is marked as fallback in the reader.
- **Human anchoring.** The human reviewer tends to pick one of the model readings. Ground truth disagreements get a second look against the scan.

## The honest trade-off

| Setup | Cost | Errors caught | Words a reader checks |
|---|---|---|---|
| Free: 3.1 Flash-Lite + (3.5 Flash-Lite, Gemma 4) | $0 | 84% (52/62) | 8.7% |
| Paid: 3.1 Flash-Lite + Gemini 3.5 Flash | about $7 per book on OpenRouter | 100% (8 pages) | 3.7% |
