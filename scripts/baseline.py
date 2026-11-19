"""Day-1 baseline: send page images to raw vision models and save their transcriptions.

Usage:
  python scripts/baseline.py --list                       # list usable vision models on each API
  python scripts/baseline.py gemini:MODEL openrouter:MODEL -- data/pages/*.png

Output: out/baseline/<provider>__<model>/<page>.txt plus a runs.jsonl with latency/usage.
Keys are read from .env (GEMINI_API_KEY, OPENROUTER_API_KEY) and never printed.
"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engines import load_env, http, gemini, openrouter  # noqa: E402

OUT = ROOT / "out" / "baseline"


def list_models():
    if os.environ.get("GEMINI_API_KEY"):
        r = http("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        print("== Gemini (generateContent)")
        for m in r.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print("  gemini:" + m["name"].split("/", 1)[1])
    else:
        print("GEMINI_API_KEY missing in .env")
    if os.environ.get("OPENROUTER_API_KEY"):
        r = http("https://openrouter.ai/api/v1/models")
        print("== OpenRouter vision models (free first)")
        rows = []
        for m in r["data"]:
            if "image" in m.get("architecture", {}).get("input_modalities", []):
                p = m.get("pricing", {})
                rows.append((float(p.get("prompt", 0) or 0), m["id"], p.get("prompt"), p.get("completion")))
        for cost, mid, pp, pc in sorted(rows)[:60]:
            print(f"  openrouter:{mid}  prompt={pp} completion={pc}")
    else:
        print("OPENROUTER_API_KEY missing in .env")


def main():
    load_env()
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        return list_models()
    sep = args.index("--")
    models, images = args[:sep], args[sep + 1:]
    OUT.mkdir(parents=True, exist_ok=True)
    runs = (OUT / "runs.jsonl").open("a")
    for spec in models:
        provider, model = spec.split(":", 1)
        fn = {"gemini": gemini, "openrouter": openrouter}[provider]
        d = OUT / f"{provider}__{model.replace('/', '_')}"
        d.mkdir(exist_ok=True)
        for img in images:
            dest = d / (Path(img).stem + ".txt")
            if dest.exists():
                continue
            t = time.time()
            try:
                text, usage = fn(model, img)
                dest.write_text(text)
                status = "ok"
            except Exception as e:
                usage, status = None, f"error: {e}"
            dt = round(time.time() - t, 1)
            print(f"{spec:55s} {Path(img).name:22s} {dt:6.1f}s {status[:120]}")
            runs.write(json.dumps({"model": spec, "page": Path(img).name, "sec": dt, "status": status,
                                   "usage": usage, "ts": time.time()}) + "\n")
            runs.flush()


if __name__ == "__main__":
    main()
