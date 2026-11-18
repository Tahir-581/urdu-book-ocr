# Evaluation against hand-verified ground truth

8 pages, 2219 words.

## Accuracy (lower is better)

| Engine | Pages | CER | WER |
|---|---|---|---|
| gemini__gemini-3.5-flash | 8 | 0.53% | 1.58% |
| gemini__gemini-3.1-flash-lite | 8 | 1.26% | 3.38% |
| openrouter__nvidia_nemotron-3.5-super-vl:free | 1 | 24.23% | 48.40% |
| archive.org OCR | 5 | 52.23% | 86.53% |

## Disagreement flagging (A = gemini__gemini-3.5-flash, B = gemini__gemini-3.1-flash-lite)

| Page | Words | A's errors | Caught by flag | Silent | Words flagged |
|---|---|---|---|---|---|
| toba-020 | 250 | 1 | 1 | 0 | 5 (2.0%) |
| toba-400 | 187 | 6 | 6 | 0 | 8 (4.3%) |
| umrao-010L | 237 | 0 | 0 | 0 | 5 (2.1%) |
| umrao-010R | 270 | 2 | 2 | 0 | 9 (3.3%) |
| umrao-025L | 280 | 3 | 3 | 0 | 8 (2.9%) |
| umrao-025R | 194 | 5 | 5 | 0 | 12 (6.1%) |
| umrao-050L | 332 | 2 | 2 | 0 | 7 (2.1%) |
| umrao-050R | 469 | 9 | 9 | 0 | 24 (5.1%) |
| **Total** | 2219 | 28 | 28 (100%) | 0 | 78 (3.5%) |

### Silent errors (wrong, but both models agreed)

