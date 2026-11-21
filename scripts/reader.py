"""Build the public web reader for one converted book (static site, no server needed).

  python scripts/reader.py umrao --title "امراؤ جان ادا" --author "مرزا ہادی رسوا"

Reads out/books/<book>/ (pages, compare JSON) and writes out/site/<book>/:
  index.html        scan | text side by side, flagged words highlighted, full-text search
  img/<id>.jpg      web-sized scans
  <book>.txt        plain text edition (model A's reading)
  <book>-flagged.txt same text with every disagreement marked as ⟦A ‖ B⟧ for proofreaders
"""
import argparse, json, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.book import order_key  # noqa: E402

CSS = """
:root{--bg:#f7f4ec;--fg:#1d1b16;--muted:#6b665a;--card:#fffdf8;--line:#e3ddcf;--flag:#ffe08a;--flag-fg:#1d1b16;--acc:#0b6e4f;--hit:#bfe6d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15140f;--fg:#ece8dd;--muted:#a49f92;--card:#1f1d17;--line:#38352b;--flag:#6b5612;--flag-fg:#fff3c9;--acc:#5fd3a6;--hit:#1f4a3b}}
:root[data-theme="dark"]{--bg:#15140f;--fg:#ece8dd;--muted:#a49f92;--card:#1f1d17;--line:#38352b;--flag:#6b5612;--flag-fg:#fff3c9;--acc:#5fd3a6;--hit:#1f4a3b}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.brand{display:flex;flex-direction:column;line-height:1.2;margin-inline-end:auto}
.brand b{font-family:'Noto Nastaliq Urdu',serif;font-size:20px;line-height:1.9}
.brand span{color:var(--muted);font-size:12px}.brand bdi{font-family:'Noto Nastaliq Urdu',serif}
.nav{display:flex;gap:6px;align-items:center}
button,select,input{font:inherit;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
button{cursor:pointer}button:hover{border-color:var(--acc)}
input[type=search]{width:min(260px,60vw);direction:rtl}
a{color:var(--acc)}
.dl{display:flex;gap:10px;font-size:13px}
.tabs{display:none}
main{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;padding:12px 16px;height:calc(100vh - 70px)}
.panel{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
.scan img{width:100%;display:block}
.text{padding:10px 18px}
.meta{color:var(--muted);font-size:13px;padding:4px 0 8px;border-bottom:1px solid var(--line);margin-bottom:6px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.ln{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu',serif;font-size:19px;line-height:2.3;padding:0 4px;border-radius:6px}
.ln.flash{background:var(--hit);transition:background 1.5s}
.f{background:var(--flag);color:var(--flag-fg);border-radius:4px;cursor:pointer;padding:0 2px}
.m{font-size:14px;vertical-align:super;color:var(--muted);cursor:pointer}
.sw{background:var(--flag);color:var(--flag-fg);border-radius:4px;padding:0 3px}
body.noflags .f{background:none;color:inherit;padding:0}body.noflags .m{display:none}
.empty{color:var(--muted);padding:24px;text-align:center}
#pop{position:absolute;z-index:20;max-width:min(420px,92vw);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;box-shadow:0 8px 28px rgba(0,0,0,.2);font-size:13px}
#pop[hidden]{display:none}#pop .u{font-family:'Noto Nastaliq Urdu',serif;font-size:19px;line-height:2.1;direction:rtl}
#results{position:fixed;z-index:15;top:64px;right:16px;width:min(460px,calc(100vw - 32px));max-height:70vh;overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 32px rgba(0,0,0,.2)}
#results[hidden]{display:none}
#results .r{padding:6px 12px;border-bottom:1px solid var(--line);cursor:pointer}
#results .r:hover{background:var(--hit)}
#results small{color:var(--muted)}#results .u{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu',serif;font-size:17px;line-height:2.1}
#results mark{background:var(--flag);color:var(--flag-fg)}
.legend{font-size:12px;color:var(--muted)}
@media (max-width:820px){
 main{grid-template-columns:1fr;height:auto}
 .tabs{display:flex;gap:6px}
 body[data-view="text"] .scan,body[data-view="scan"] .text{display:none}
 .panel{max-height:none}
}
"""

JS = r"""
const B = window.BOOK, P = B.pages, $ = s => document.querySelector(s);
const FOLD = {'ھ':'ہ','ۃ':'ہ','ة':'ہ','ه':'ہ','ي':'ی','ى':'ی','ئ':'ی','ك':'ک'};
const norm = s => s.normalize('NFC').replace(/[‌-‏‪-‮⁦-⁩ً-ٰٟ]/g,'')
  .replace(/[ھۃةهيىئك]/g, c => FOLD[c]).replace(/[۔،؟"“”‘’«».,?!:;()\[\]]/g,' ').replace(/\s+/g,' ').trim();
const lineText = l => l.map(([w]) => w).filter(Boolean).join(' ');
P.forEach(p => p.norm = p.lines ? p.lines.map(l => norm(lineText(l))) : []);
const sel = $('#pg'); let cur = 0;
P.forEach((p,i) => sel.add(new Option((p.printed ? 'ص ' + p.printed : p.id) + (p.lines ? '' : ' (pending)'), i)));
function render(i, flashLine){
  cur = Math.max(0, Math.min(P.length-1, i)); const p = P[cur]; sel.value = cur; $('#pop').hidden = true;
  $('#img').src = 'img/' + p.id + '.jpg'; $('#img').alt = 'Scan of ' + p.id;
  history.replaceState(null,'','#'+p.id);
  const t = $('#body'); t.innerHTML = '';
  $('#meta').innerHTML = `<span>${p.printed ? 'Printed page ' + p.printed + ' · ' : ''}${p.id}</span>` +
    (p.lines ? `<span>${p.stats.words} words · ${p.stats.flagged_words} flagged${p.fallback ? ' · text from fallback model ' + p.a : ''}</span>` : '');
  if (!p.lines){ t.innerHTML = '<div class="empty">This page has not been transcribed yet.</div>'; return; }
  p.lines.forEach((line, li) => { const d = document.createElement('div'); d.className = 'ln'; d.id = 'l'+li;
    line.forEach(([w,a],k) => { if (k) d.append(' ');
      if (a === null){ d.append(w); return; }
      const s = document.createElement('span'); s.dataset.a = w; s.dataset.b = a;
      if (w === ''){ s.className = 'm'; s.textContent = '⁺'; } else { s.className = 'f'; s.textContent = w; }
      d.appendChild(s); });
    t.appendChild(d); });
  if (flashLine != null){ const el = document.getElementById('l'+flashLine);
    if (el){ el.scrollIntoView({block:'center'}); el.classList.add('flash'); setTimeout(()=>el.classList.remove('flash'),1600); } }
  else $('#txt').scrollTop = 0, $('#scanp').scrollTop = 0;
}
$('#body').addEventListener('click', e => { const s = e.target.closest('.f,.m'); const pop = $('#pop'); if (!s){ pop.hidden = true; return; }
  const A = s.dataset.a, Bv = s.dataset.b;
  pop.innerHTML = s.classList.contains('m')
    ? `Only a checker model read a word here:<div class="u">${Bv}</div>Check the scan.`
    : (Bv ? `The models disagree. Shown: <div class="u">${A}</div>Checker model(s) read: <div class="u">${Bv}</div>Check the scan.`
          : `A checker model has no word here: it skipped this word, or it is the tail of the disagreement just before. Check the scan.`);
  const r = s.getBoundingClientRect(); pop.hidden = false;
  pop.style.top = (r.bottom + scrollY + 6) + 'px';
  pop.style.left = Math.max(8, Math.min(r.left + scrollX, innerWidth - pop.offsetWidth - 8)) + 'px'; });
sel.onchange = () => render(+sel.value);
$('#next').onclick = () => render(cur+1); $('#prev').onclick = () => render(cur-1);
document.addEventListener('keydown', e => { if (e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') render(cur+1); if (e.key === 'ArrowRight') render(cur-1);
  if (e.key === 'Escape'){ $('#pop').hidden = true; $('#results').hidden = true; } });
$('#flags').onchange = e => document.body.classList.toggle('noflags', !e.target.checked);
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => document.body.dataset.view = b.dataset.v);
let timer; $('#q').addEventListener('input', e => { clearTimeout(timer); timer = setTimeout(() => search(e.target.value), 200); });
function esc(s){ return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function search(q){ const box = $('#results'); q = norm(q); if (q.length < 2){ box.hidden = true; return; }
  const hits = []; P.forEach((p,i) => p.norm.forEach((n,li) => { const k = n.indexOf(q); if (k >= 0) hits.push([i,li,n,k]); }));
  box.innerHTML = `<div class="r"><small>${hits.length} result${hits.length===1?'':'s'}${hits.length>200?' (first 200 shown)':''}</small></div>` +
    hits.slice(0,200).map(([i,li,n,k]) => `<div class="r" data-i="${i}" data-l="${li}"><small>${P[i].printed ? 'Page ' + P[i].printed : P[i].id}</small>` +
      `<div class="u">${esc(n.slice(Math.max(0,k-40),k))}<mark>${esc(n.slice(k,k+q.length))}</mark>${esc(n.slice(k+q.length,k+q.length+40))}</div></div>`).join('');
  box.hidden = false; }
$('#results').onclick = e => { const r = e.target.closest('[data-i]'); if (!r) return; $('#results').hidden = true;
  document.body.dataset.view = 'text'; render(+r.dataset.i, +r.dataset.l); };
const start = P.findIndex(p => '#'+p.id === location.hash); render(start >= 0 ? start : 0);
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--width", type=int, default=1100, help="web scan width in px")
    a = ap.parse_args()

    src = ROOT / "out" / "books" / a.book
    site = ROOT / "out" / "site" / a.book
    (site / "img").mkdir(parents=True, exist_ok=True)

    pages, plain, flagged = [], [], []
    used, checkers = {}, set()
    for img in sorted((src / "pages").glob("*.png"), key=order_key):
        jpg = site / "img" / f"{img.stem}.jpg"
        if not jpg.exists() or jpg.stat().st_mtime < img.stat().st_mtime:
            im = Image.open(img).convert("L")
            if im.width > a.width:
                im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
            im.save(jpg, quality=72, optimize=True, progressive=True)
        cmp = src / "compare" / f"{img.stem}.json"
        if not cmp.exists():
            pages.append({"id": img.stem, "printed": None, "lines": None})
            plain.append(f"\n=== {img.stem} (not transcribed yet) ===\n")
            flagged.append(plain[-1])
            continue
        d = json.loads(cmp.read_text())
        printed = d["stats"].get("page_a")
        pages.append({"id": img.stem, "printed": printed, "lines": d["lines"], "stats": d["stats"],
                      "a": d["a"].split(":", 1)[1], "fallback": d.get("fallback", False)})
        used[d["a"]] = used.get(d["a"], 0) + 1
        checkers.update(d["b"] if isinstance(d["b"], list) else [d["b"]])
        head = f"\n=== {img.stem}" + (f" · page {printed}" if printed else "") + " ===\n"
        plain.append(head + "\n".join(" ".join(w for w, _ in line if w) for line in d["lines"]) + "\n")
        flagged.append(head + "\n".join(" ".join(
            w if alt is None else (f"⟦{w} ‖ {alt}⟧" if w else f"⟦+ ‖ {alt}⟧") if (alt or not w) else f"⟦{w}⟧"
            for w, alt in line) for line in d["lines"]) + "\n")

    done = [p for p in pages if p["lines"]]
    words = sum(p["stats"]["words"] for p in done)
    nflag = sum(p["stats"]["flagged_words"] for p in done)
    name = lambda spec: spec.split(":", 1)[1]
    models = ", ".join(f"{name(m)} ({n} pages)" for m, n in sorted(used.items(), key=lambda kv: -kv[1]))
    header = (f"{a.title}, {a.author}\nMachine transcription by {models}; checked against {', '.join(map(name, sorted(checkers)))}.\n"
              f"{len(done)}/{len(pages)} pages, {words} words, {nflag} words flagged where the models disagree.\n"
              "Source scan: archive.org (public domain). Built with https://github.com/Tahir-581/urdu-book-ocr\n")
    (site / f"{a.book}.txt").write_text(header + "".join(plain))
    (site / f"{a.book}-flagged.txt").write_text(header + "Flags: ⟦shown ‖ second model's reading⟧; ⟦shown⟧ alone = second model has no word there; ⟦+ ‖ x⟧ = only the second model read x\n" + "".join(flagged))

    book = {"id": a.book, "title": a.title, "author": a.author, "pages": pages}
    summary = f"{len(done)} of {len(pages)} pages · {words:,} words · {nflag/max(1,words):.1%} flagged"
    doc = f"""<!doctype html><html lang="ur"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{a.title} · Harf reader</title>
<meta name="description" content="{a.title} by {a.author}: searchable Urdu text beside the original scan, with uncertain words flagged.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap">
<style>{CSS}</style></head><body data-view="text">
<header>
 <div class="brand"><b>{a.title}</b><span><bdi dir="rtl">{a.author}</bdi> · <bdi dir="ltr">{summary}</bdi></span></div>
 <input id="q" type="search" placeholder="تلاش کریں… (search)" aria-label="Search the book">
 <div class="nav"><button id="next" title="Next page (←)" aria-label="Next page">‹</button><select id="pg" aria-label="Page"></select><button id="prev" title="Previous page (→)" aria-label="Previous page">›</button></div>
 <label class="legend"><input type="checkbox" id="flags" checked> <span class="sw">highlight</span> words the models disagree on</label>
 <div class="dl"><a href="{a.book}.txt" download>Text (.txt)</a><a href="{a.book}-flagged.txt" download>Text with flags</a></div>
 <div class="tabs"><button data-v="scan">Scan</button><button data-v="text">Text</button></div>
</header>
<div id="results" hidden></div><div id="pop" hidden></div>
<main><div class="panel scan" id="scanp"><img id="img" alt=""></div>
<div class="panel text" id="txt"><div class="meta" id="meta"></div><div id="body"></div></div></main>
<script>window.BOOK={json.dumps(book, ensure_ascii=False, separators=(",", ":"))};{JS}</script></body></html>"""
    (site / "index.html").write_text(doc)
    print(f"wrote {site/'index.html'}: {summary}")


if __name__ == "__main__":
    main()
