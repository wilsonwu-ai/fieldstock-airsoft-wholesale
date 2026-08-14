#!/usr/bin/env python3
"""Turn 668MB of scraped studio photography into a web asset set.

For each product: a transparent cutout at three sizes (card / hero / thumb) plus
up to three untouched gallery frames. Cutouts use fal birefnet for the marquee
guns and a local border flood-fill for the long tail — the source photography is
clean white studio, which the local path handles reliably.

Nothing here generates pixels. Masking and resizing only.
"""
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import cutout, trim, local_cutout, punch_enclosed_holes  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "site", "assets", "img")
SIZES = {"card": 720, "hero": 1400, "thumb": 340}

# Guns carry the visual load, so they get the higher-quality remote cutout.
FAL_CATEGORIES = {"Rifles", "Shotguns", "Pistols", "HPA Systems"}


def save_variants(im, stem):
    made = {}
    for label, w in SIZES.items():
        if im.width <= 0:
            continue
        h = max(1, round(im.height * (w / im.width)))
        r = im.resize((w, h), Image.LANCZOS) if im.width > w else im.copy()
        p = os.path.join(OUT, f"{stem}.{label}.webp")
        r.save(p, "WEBP", quality=84, method=5)
        made[label] = f"assets/img/{stem}.{label}.webp"
    return made


def gallery_variant(src, stem, i):
    try:
        im = Image.open(src).convert("RGB")
        w = 1100
        if im.width > w:
            im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        p = os.path.join(OUT, f"{stem}.g{i}.webp")
        im.save(p, "WEBP", quality=82, method=5)
        return f"assets/img/{stem}.g{i}.webp"
    except Exception:
        return None


def do_product(p):
    stem = p["id"]
    rec = {"id": stem, "cutout": {}, "gallery": []}
    imgs = [os.path.join(ROOT, r) for r in p["images"]]
    imgs = [i for i in imgs if os.path.exists(i)]
    if not imgs:
        return rec

    use_fal = p["category"] in FAL_CATEGORIES
    try:
        im = cutout(imgs[0], use_fal=use_fal)
        im = trim(im)
        # A cutout that kept almost everything means the mask failed open.
        alpha = im.split()[3]
        opaque = sum(alpha.histogram()[250:])
        if opaque > 0.985 * (im.width * im.height):
            im = trim(local_cutout(Image.open(imgs[0])))
        rec["cutout"] = save_variants(im, stem)
    except Exception:
        rec["error"] = traceback.format_exc(limit=1)
        try:
            rec["cutout"] = save_variants(trim(local_cutout(Image.open(imgs[0]))), stem)
        except Exception:
            pass

    for i, src in enumerate(imgs[1:4], start=1):
        g = gallery_variant(src, stem, i)
        if g:
            rec["gallery"].append(g)
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    products = json.load(open(os.path.join(ROOT, "research", "products.json")))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if limit:
        products = products[:limit]

    results, done = {}, 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(do_product, p): p for p in products}
        for f in as_completed(futs):
            p = futs[f]
            try:
                r = f.result()
            except Exception:
                r = {"id": p["id"], "cutout": {}, "gallery": [], "error": "task failed"}
            results[r["id"]] = r
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(products)}", flush=True)

    for p in products:
        r = results.get(p["id"], {})
        p["img"] = r.get("cutout", {})
        p["gallery"] = r.get("gallery", [])

    with open(os.path.join(ROOT, "site", "data", "products.json"), "w") as f:
        json.dump(products, f, separators=(",", ":"))

    ok = sum(1 for p in products if p.get("img"))
    print(f"\ndone: {ok}/{len(products)} products have cutouts")
    errs = [r for r in results.values() if r.get("error")]
    print(f"errors: {len(errs)}")


if __name__ == "__main__":
    main()
