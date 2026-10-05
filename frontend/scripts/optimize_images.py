"""Resize + recompress the downloaded marketing photos.

The originals are 1280px-wide Commons thumbnails straight off the wire, several
of which are 400-500 KB. On a landing page that is the heaviest thing on the
page, so each image gets the largest width it is actually displayed at, saved
as progressive JPEG, and any EXIF/copyright metadata stripped.

Run from the repo root:
    venv\\Scripts\\python.exe frontend\\scripts\\optimize_images.py

Re-run it any time you swap a photo in public/images; it also rewrites
credits.json with the new dimensions so the attribution stays accurate.
"""

import json
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent / "public" / "images"

# slug -> max width. Hero is full-bleed so it gets the most pixels; cards are
# in a grid and never render wider than roughly a third of a 1440px viewport.
WIDTHS = {
    "hero": 1800,
    "destinations": 900,
    "categories": 800,
    "auth": 1100,
}
FALLBACK_WIDTH = 1200
QUALITY = 78


def optimize(path: pathlib.Path) -> None:
    folder = path.parent.name
    max_w = WIDTHS.get(folder, FALLBACK_WIDTH)

    before = path.stat().st_size
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_w:
            h = round(im.height * max_w / im.width)
            im = im.resize((max_w, h), Image.LANCZOS)
        im.save(path, "JPEG", quality=QUALITY, optimize=True, progressive=True)

    after = path.stat().st_size
    print(
        f"{folder}/{path.name:<22} {im.width:>5}x{im.height:<5} "
        f"{before / 1024:6.0f}KB -> {after / 1024:5.0f}KB"
    )


def main() -> None:
    files = sorted(ROOT.glob("*/*.jpg"))
    for f in files:
        optimize(f)

    total = sum(f.stat().st_size for f in files)
    print(f"\n{len(files)} images, {total / 1024:.0f} KB total")

    # keep credits.json in sync with what is actually on disk
    credits_path = ROOT / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8-sig"))
    for c in credits:
        img = ROOT / f"{c['slug']}.jpg"
        if img.exists():
            with Image.open(img) as im:
                c["width"], c["height"] = im.size
            c["bytes"] = img.stat().st_size
        else:
            c["missing"] = True
    credits_path.write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding="utf-8")
    print("credits.json updated with final dimensions")


if __name__ == "__main__":
    main()