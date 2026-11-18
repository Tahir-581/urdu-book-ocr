"""Step 1 of the pipeline: PDF page -> clean single-page PNGs.

- Renders a PDF page with pdftoppm.
- Splits two-page spreads (landscape images) into right and left pages, right first (Urdu reads RTL).
- Masks the bottom watermark band when asked (e.g. 'Marfat.com' on some scans).

Usage: python -m src.prep data/scans/umrao.pdf 10 20 30 --dpi 200
"""
import argparse, subprocess, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "data" / "pages"


def render(pdf: Path, page: int, dpi: int) -> Image.Image:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-f", str(page), "-l", str(page),
                        str(pdf), f"{td}/p"], check=True)
        f = next(Path(td).glob("p*.png"))
        return Image.open(f).convert("L").copy()


def split_spread(im: Image.Image):
    """Landscape image = two pages. Cut at the darkest-free (lightest) column near the middle."""
    w, h = im.size
    if w <= h:
        return [("", im)]
    band = range(int(w * 0.42), int(w * 0.58))
    px = im.load()
    step = max(1, h // 300)
    def ink(x):
        return sum(255 - px[x, y] for y in range(0, h, step))
    cut = min(band, key=ink)
    return [("R", im.crop((cut, 0, w, h))), ("L", im.crop((0, 0, cut, h)))]


def prep(pdf: Path, pages, dpi=200, mask_bottom=0.0):
    PAGES.mkdir(parents=True, exist_ok=True)
    out = []
    for n in pages:
        im = render(pdf, n, dpi)
        if mask_bottom:
            w, h = im.size
            im.paste(255, (0, int(h * (1 - mask_bottom)), w, h))
        for side, part in split_spread(im):
            dest = PAGES / f"{pdf.stem}-{n:03d}{side}.png"
            part.save(dest, optimize=True)
            out.append(dest)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("pages", type=int, nargs="+")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--mask-bottom", type=float, default=0.0, help="fraction of height to blank (watermark)")
    a = ap.parse_args()
    for p in prep(a.pdf, a.pages, a.dpi, a.mask_bottom):
        print(p.relative_to(ROOT))
