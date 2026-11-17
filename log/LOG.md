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
