# Choosing a free checker model (day 2, 2026-11-19)

Gemini 3.5 Flash, the most accurate model (CER 0.53%), has a free-tier cap of **20 requests/day** (quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value 20; retries count). It cannot convert a 198-page book before the deadline. Decision: stay on free tiers. Gemini 3.1 Flash-Lite (CER 1.26%) becomes the primary text, and we need a checker whose disagreements reveal Flash-Lite's errors.

Measured on the same 8 hand-verified pages (2,219 words); A = gemini-3.1-flash-lite in every row:

| Checker B | Checker's own CER | A's errors | Caught | Silent | Words flagged |
|---|---|---|---|---|---|
| gemini__gemini-3.5-flash | 0.53% | 54 | 54 (100%) | 0 | 81 (3.7%) |
| gemini__gemini-3-flash-preview | 1.64% | 54 | 46 (85%) | 8 | 72 (3.2%) |
| gemini__gemini-3.5-flash-lite | 1.52% | 54 | 34 (63%) | 20 | 77 (3.5%) |

**Finding:** a checker from the *same family* (3.5 Flash-Lite) catches only 63%: the two Lite models make the same mistakes, so they agree on them. Disagreement is only a trust signal when the checker fails *differently*. 3 Flash preview is less accurate than Flash-Lite on its own (1.64% CER) but catches 85% of its errors, which meets the ≥80% target in intent.md.

Half of the 8 silent errors with the 3 Flash preview checker are izafat marks (`زاویۂ` written `زاویہ`, `ناقہٴ` → `ناقہ`): both models drop the hamza. That is a known blind spot to state in the reader.

## Update: every Gemini "Flash" model is capped at 20 requests/day

3 Flash preview also hit `GenerateRequestsPerDayPerProjectPerModel-FreeTier` = 20 after 8 test pages + 13 book pages, so it can't check a 198-page book either. The free models with a usable daily quota are the Flash-**Lite** models and Gemma 4. Gemma 4 31B through OpenRouter's free pool failed on every page (shared-pool 429); through the Gemini API it works but takes 2 to 6 min/page (503 "high demand" retries).

Single weak checkers miss different errors, so I tested flagging a word when **any** checker disagrees:

| Checker(s), A = 3.1 Flash-Lite | Caught | Words flagged |
|---|---|---|
| 3.5 Flash-Lite | 63% | 3.5% |
| Gemma 4 31B (7 pages) | 70% | 8.1% |
| 3 Flash preview | 85% | 3.2% |
| **3.5 Flash-Lite + Gemma 4 31B** (7 pages) | **80%** | **9.1%** |
| 3.5 Flash-Lite + 3 Flash preview | 91% | 4.9% |

**Decision for the book:** A = 3.1 Flash-Lite, checkers = 3.5 Flash-Lite + Gemma 4 31B. It meets the ≥80% target on free quotas; the price is a reader who checks ~9% of words instead of ~3%. Paying ~$7 for Gemini 3.5 Flash would give 100% / 3.5%: that is the trade-off to state in the write-up.

Reproduce: `python -m src.evaluate gemini__gemini-3.1-flash-lite gemini__gemini-3.5-flash-lite gemini__gemma-4-31b-it`
