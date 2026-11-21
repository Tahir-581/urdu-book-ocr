# Evaluation against hand-verified ground truth

14 pages, 2803 words.

## Accuracy (lower is better)

| Engine | Pages | CER | WER |
|---|---|---|---|
| gemini__gemini-3.5-flash | 14 | 0.29% | 0.88% |
| gemini__gemini-3.1-flash-lite | 14 | 1.17% | 2.99% |
| gemini__gemini-3.5-flash-lite | 14 | 1.29% | 3.89% |
| gemini__gemini-3-flash-preview | 8 | 1.64% | 2.52% |
| gemini__gemma-4-31b-it | 10 | 4.16% | 9.10% |
| openrouter__nvidia_nemotron-3.5-super-vl:free | 2 | 24.06% | 47.14% |
| archive.org OCR | 10 | 50.43% | 81.72% |

## Disagreement flagging (A = gemini__gemini-3.1-flash-lite, B = gemini__gemini-3.5-flash-lite + gemini__gemma-4-31b-it)

| Page | Words | A's errors | Caught by flag | Silent | Words flagged |
|---|---|---|---|---|---|
| toba-020 | 250 | 5 | 3 | 2 | 3 (1.2%) |
| toba-220 | 240 | 5 | 4 | 1 | 20 (8.4%) |
| toba-300 | 197 | 3 | 3 | 0 | 10 (5.1%) |
| toba-400 | 187 | 1 | 0 | 1 | 6 (3.2%) |
| umrao-010L | 237 | 5 | 5 | 0 | 14 (5.9%) |
| umrao-025L | 280 | 6 | 6 | 0 | 34 (12.1%) |
| umrao-025R | 194 | 9 | 7 | 2 | 17 (8.8%) |
| umrao-050L | 332 | 5 | 5 | 0 | 26 (7.8%) |
| umrao-050R | 469 | 15 | 11 | 4 | 78 (16.7%) |
| umrao-075L | 417 | 8 | 8 | 0 | 37 (8.9%) |
| **Total** | 2803 | 62 | 52 (84%) | 10 | 245 (8.7%) |

### Silent errors (wrong, but both models agreed)

- toba-020: model `صحیح` → truth `سچ`
- toba-020: model `(missing)` → truth `ــــ`
- toba-220: model `تلوں` → truth `تلووں`
- toba-400: model `ذرہ` → truth `ذرۂ`
- umrao-025R: model `زاہد` → truth `زاہدو`
- umrao-025R: model `آہا ہاہا` → truth `آہاہاہاہا`
- umrao-050R: model `رذیل` → truth `رزیل`
- umrao-050R: model `کندہے` → truth `کاندہے`
- umrao-050R: model `بہنا` → truth `پہنا`
- umrao-050R: model `گہٹ` → truth `کہٹ`
