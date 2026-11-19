"""Vision-model calls shared by the baseline script and the book runner.

Keys come from .env (GEMINI_API_KEY, OPENROUTER_API_KEY) and are never printed.
An engine spec looks like 'gemini:gemini-3.5-flash' or 'openrouter:vendor/model'.
"""
import base64, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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


class QuotaExhausted(RuntimeError):
    """Daily free-tier quota is used up. Retrying today is pointless; stop this engine."""


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip())


def _retry_delay(body: str):
    """Gemini 429 bodies carry e.g. "retryDelay": "34s"."""
    m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', body)
    return float(m.group(1)) if m else None


def http(url, body=None, headers=None, timeout=180, retries=4):
    """POST/GET JSON. Retries 429/5xx with backoff; raises QuotaExhausted on a per-day quota 429."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            full = e.read().decode(errors="replace")
            msg = full[:400]
            if e.code == 429 and "PerDay" in full:
                raise QuotaExhausted(f"HTTP 429 daily quota: {msg}") from None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = min(90, max(_retry_delay(full) or 0, 5 * 2 ** attempt))
                print(f"    retry in {wait:.0f}s after HTTP {e.code}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}") from None
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt < retries:
                wait = 5 * 2 ** attempt
                print(f"    retry in {wait}s after {e}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"network: {e}") from None


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
    cand = (r.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        # Empty output with HTTP 200 happens (e.g. finishReason RECITATION on famous text). Never save it as a result.
        raise RuntimeError(f"empty output, finishReason={cand.get('finishReason')} "
                           f"promptFeedback={r.get('promptFeedback')}")
    return text, r.get("usageMetadata")


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
    text = r["choices"][0]["message"].get("content") or ""
    if not text.strip():
        raise RuntimeError("empty output")
    return text, r.get("usage")


PROVIDERS = {"gemini": gemini, "openrouter": openrouter}


def transcribe(spec, image):
    provider, model = spec.split(":", 1)
    return PROVIDERS[provider](model, image)


def dirname(spec):
    """'gemini:gemini-3.5-flash' -> 'gemini__gemini-3.5-flash' (same layout as out/baseline)."""
    provider, model = spec.split(":", 1)
    return f"{provider}__{model.replace('/', '_')}"
