"""Day-1 baseline: send page images to raw vision models and save their transcriptions.

Usage:
  python scripts/baseline.py --list                       # list usable vision models on each API
  python scripts/baseline.py gemini:MODEL openrouter:MODEL -- data/pages/*.png

Output: out/baseline/<provider>__<model>/<page>.txt plus a runs.jsonl with latency/usage.
Keys are read from .env (GEMINI_API_KEY, OPENROUTER_API_KEY) and never printed.
"""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "baseline"

PROMPT = (
    "Transcribe the Urdu text on this scanned book page exactly as printed.\n"
    "Rules:\n"
    "- Output Urdu in Unicode, one printed line per output line, in reading order.\n"
    "- Copy what is printed. Do not correct spelling, modernise, complete, or paraphrase anything.\n"
    "- If a word is unreadable, write [?] in its place instead of guessing.\n"
    "- Skip watermarks and website names that are not part of the book.\n"
    "- Put the printed page number, if any, on the first line as: PAGE: <number>\n"
    "- If the image shows two pages, transcribe the RIGHT page first, then a line '---', then the LEFT page.\n"
    "Output only the transcription."
)


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip())


def http(url, body=None, headers=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:400]}") from None


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def gemini(model, image):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": "image/png", "data": b64(image)}}]}],
        "generationConfig": {"temperature": 0},
    }
    r = http(url, body, {"x-goog-api-key": key})
    parts = r["candidates"][0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts), r.get("usageMetadata")


def openrouter(model, image):
    key = os.environ["OPENROUTER_API_KEY"]
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(image)}"}},
        ]}],
    }
    r = http("https://openrouter.ai/api/v1/chat/completions", body, {"Authorization": f"Bearer {key}"})
    if "error" in r:
        raise RuntimeError(str(r["error"])[:400])
    return r["choices"][0]["message"]["content"], r.get("usage")


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
