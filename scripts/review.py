"""Build a ground-truth review page: scan on the left, editable transcription on the right,
with words the two models disagree on highlighted (hover/tap shows the other model's reading).

Usage:
  python scripts/review.py MODEL_DIR_A MODEL_DIR_B data/pages/*.png
Writes out/review/index.html (one page per scan, with a 'Download corrected text' button).
Corrected files go into data/groundtruth/<page>.txt.
"""
import html, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.compare import compare  # noqa: E402

CSS = """
:root{--bg:#faf8f3;--fg:#1d1b16;--muted:#6b665a;--card:#fff;--line:#e5e0d4;--flag:#ffe08a;--miss:#ffb4a8;--acc:#0b6e4f}
@media (prefers-color-scheme:dark){:root{--bg:#16150f;--fg:#ece8dd;--muted:#a49f92;--card:#211f18;--line:#3a372c;--flag:#6b5612;--miss:#6e2a20;--acc:#5fd3a6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
select,button{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
button.primary{background:var(--acc);color:#fff;border:0}
main{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px 16px;height:calc(100vh - 60px)}
@media (max-width:800px){main{grid-template-columns:1fr;height:auto}}
.scan{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
.scan img{width:100%;display:block}
.text{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.ln{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',serif;font-size:22px;line-height:2.3;padding:2px 6px;border-bottom:1px dashed var(--line);outline:none}
.ln:focus{background:color-mix(in srgb,var(--acc) 10%,transparent)}
.f{background:var(--flag);border-radius:4px;cursor:help}
.m{background:var(--miss);border-radius:4px;font-size:16px;cursor:help}
.stats{color:var(--muted);font-size:13px}
.f.ok,.m.ok{background:color-mix(in srgb,var(--acc) 25%,transparent)}
#pop{position:absolute;z-index:10;display:flex;gap:6px;flex-wrap:wrap;max-width:min(560px,92vw);padding:8px;background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.18)}
#pop[hidden]{display:none}
#pop button{display:flex;flex-direction:column;align-items:center;min-width:90px;cursor:pointer}
#pop small{color:var(--muted);font-size:11px}
#pop .u{font-family:'Noto Nastaliq Urdu',serif;font-size:20px;line-height:2;direction:rtl}
#pop .pa{border-color:#c9a227}#pop .pb{border-color:#7a9cc6}
#left{font-size:13px;font-weight:600}
"""

JS = """
const pages = window.PAGES; const sel = document.getElementById('pg'); const pop = document.getElementById('pop');
pages.forEach((p,i)=>sel.add(new Option(p.name+'  ('+p.stats.flagged_words+' flags)', i)));
function left(){const n=document.querySelectorAll('#txt .f:not(.ok),#txt .m:not(.ok)').length;
 document.getElementById('left').textContent=n?n+' highlighted words left to decide':'All highlights decided. Now read the whole page once more.';}
function show(i){const p=pages[i];document.getElementById('img').src=p.img;pop.hidden=true;
 document.getElementById('stats').textContent=`printed page ${p.stats.page_a??'?'} · ${p.stats.words} words · ${p.stats.flagged_words} disagreements`;
 const t=document.getElementById('txt');t.innerHTML='';
 const head=document.createElement('div');head.className='ln';head.contentEditable=true;head.textContent='PAGE: '+(p.stats.page_a??'');t.appendChild(head);
 p.lines.forEach(line=>{const d=document.createElement('div');d.className='ln';d.contentEditable=true;
  line.forEach(([w,a],k)=>{ if(k) d.append(' ');
   if(a===null){d.append(w);return}
   const s=document.createElement('span');s.contentEditable=false;s.dataset.a=w;s.dataset.b=a;
   if(w===''){s.className='m';s.textContent='+'+a;} else {s.className='f';s.textContent=w;}
   d.appendChild(s)});t.appendChild(d)});left()}
function choose(s,text){ if(text===''){ s.remove(); } else { s.textContent=text; s.classList.add('ok'); } pop.hidden=true; left(); }
function editable(s){ const t=document.createTextNode(s.classList.contains('m')?s.dataset.b:s.textContent);
 s.replaceWith(t); pop.hidden=true; const r=document.createRange(); r.selectNodeContents(t);
 const g=getSelection(); g.removeAllRanges(); g.addRange(r); t.parentElement.focus(); left(); }
document.getElementById('txt').addEventListener('click',e=>{const s=e.target.closest('.f,.m'); if(!s) return;
 e.preventDefault(); pop.innerHTML='';
 const opt=(label,fn,cls)=>{const b=document.createElement('button');b.innerHTML=label;if(cls)b.className=cls;b.onclick=fn;pop.appendChild(b)};
 const A=s.dataset.a, B=s.dataset.b;
 if(s.classList.contains('m')){ opt('<small>Add (only B saw it)</small><span class=u>'+B+'</span>',()=>choose(s,B));
   opt('<small>Not on the page</small>Skip',()=>choose(s,'')); }
 else { opt('<small>Model A</small><span class=u>'+A+'</span>',()=>choose(s,A),'pa');
   opt(B?'<small>Model B</small><span class=u>'+B+'</span>':'<small>Model B</small>Delete word',()=>choose(s,B),'pb'); }
 opt('<small>Neither is right</small>✎ Type it',()=>editable(s));
 const r=s.getBoundingClientRect(); pop.hidden=false;
 pop.style.top=(r.bottom+window.scrollY+6)+'px'; pop.style.left=Math.max(8,Math.min(r.left+window.scrollX, innerWidth-pop.offsetWidth-8))+'px';});
document.addEventListener('keydown',e=>{if(e.key==='Escape')pop.hidden=true});
sel.onchange=()=>show(sel.value);show(0);
document.getElementById('dl').onclick=()=>{const p=pages[sel.value];
 const clone=document.getElementById('txt').cloneNode(true);
 clone.querySelectorAll('.m:not(.ok)').forEach(s=>s.remove());   // undecided B-only words are left out
 const text=[...clone.querySelectorAll('.ln')].map(d=>d.textContent.replace(/\\s+/g,' ').trim()).filter(Boolean).join('\\n')+'\\n';
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
 a.download=p.name+'.txt';a.click()};
"""


def main():
    dir_a, dir_b, *images = sys.argv[1:]
    out = ROOT / "out" / "review"
    out.mkdir(parents=True, exist_ok=True)
    pages = []
    for img in images:
        stem = Path(img).stem
        fa, fb = Path(dir_a) / f"{stem}.txt", Path(dir_b) / f"{stem}.txt"
        if not (fa.exists() and fb.exists()):
            print("skip (missing transcription):", stem)
            continue
        lines, stats = compare(fa.read_text(), fb.read_text())
        rel = Path("../../") / Path(img).resolve().relative_to(ROOT)
        pages.append({"name": stem, "img": str(rel), "lines": lines, "stats": stats})
        print(f"{stem:14s} {stats}")
    doc = f"""<!doctype html><html lang="ur"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ground-truth review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap">
<style>{CSS}</style></head><body>
<header><b>Ground-truth review</b><select id="pg"></select><span id="stats" class="stats"></span>
<span id="left"></span>
<span class="stats">Click a yellow/red word to choose the right reading. To fix any other word, click in the text and type (Urdu keyboard: Super+Space).</span>
<button class="primary" id="dl">Download corrected text</button></header>
<div id="pop" hidden></div>
<main><div class="scan"><img id="img" alt="scan"></div><div class="text" id="txt"></div></main>
<script>window.PAGES={json.dumps(pages, ensure_ascii=False)};{JS}</script></body></html>"""
    (out / "index.html").write_text(doc)
    print("wrote", out / "index.html")


if __name__ == "__main__":
    main()
