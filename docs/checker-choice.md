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
