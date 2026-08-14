#!/usr/bin/env python3
"""Background-removal helper for product photography.

fal's birefnet cuts the outer silhouette well but leaves background showing
through enclosed holes (trigger guards, magwells, sling loops). Knocking out
every near-white pixel fixes the holes but also erases the white engraved
markings on the receiver, which are exactly the detail an airsoft buyer looks
for. So the knock-out is size-aware: only large connected near-white regions are
treated as background, and small ones (text glyphs, highlights) are kept.

No pixel here is generated. This is masking only — every image still traces back
to a real photograph of that exact SKU.
"""
import base64
import json
import os
import time
import urllib.request

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

FAL_KEY = os.environ.get("FAL_KEY", "")
ENDPOINT = "https://queue.fal.run/fal-ai/birefnet/v2"

# A near-white pixel is background only if it belongs to a blob at least this
# large. The trigger guard interior runs into the thousands of pixels; the
# tallest engraved glyph on a 1400px-wide receiver photo stays under ~400.
MIN_HOLE_AREA = 900


def _req(url, data=None):
    r = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(r, timeout=180))


def fal_cutout(path, timeout=240):
    """Return RGBA bytes with the outer silhouette masked, or None on failure."""
    with open(path, "rb") as f:
        raw = f.read()
    ext = "png" if path.lower().endswith(".png") else "jpeg"
    uri = f"data:image/{ext};base64," + base64.b64encode(raw).decode()
    try:
        q = _req(ENDPOINT, {"image_url": uri})
    except Exception as e:
        print(f"    fal submit failed: {e}")
        return None
    rid = q.get("request_id")
    if not rid:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        try:
            s = _req(f"https://queue.fal.run/fal-ai/birefnet/requests/{rid}/status")
        except Exception:
            continue
        if s.get("status") == "COMPLETED":
            break
    else:
        return None
    try:
        res = _req(f"https://queue.fal.run/fal-ai/birefnet/requests/{rid}")
        url = (res.get("image") or {}).get("url")
        if not url:
            return None
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    except Exception as e:
        print(f"    fal fetch failed: {e}")
        return None


def punch_enclosed_holes(im):
    """Drop backdrop showing through enclosed holes, while keeping highlights.

    Brightness alone cannot separate the two: the studio backdrop is exactly
    (255,255,255), and a blown specular highlight on brass or polished steel
    clips to 255 as well. The edge does separate them. A hole is bounded by the
    product, so the ring of pixels just outside it is dark and the transition is
    abrupt. A highlight sits in the middle of a lit surface, so its ring is a
    mid-bright ramp. We test that ring.
    """
    im = im.convert("RGBA")
    a = np.array(im)
    rgb = a[..., :3].astype(np.int16)
    alpha = a[..., 3]
    gray = rgb.mean(axis=2)

    near_white = (
        (rgb.min(axis=2) >= 246)
        & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 6)
        & (alpha > 8)
    )
    if not near_white.any():
        return im

    labels, n = ndimage.label(near_white)
    if not n:
        return im

    kill = np.zeros(n + 1, dtype=bool)
    objs = ndimage.find_objects(labels)
    for idx, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        # Work in a padded neighbourhood so the ring is fully inside the crop.
        pad = 4
        ys, xs = sl
        y0, y1 = max(0, ys.start - pad), min(a.shape[0], ys.stop + pad)
        x0, x1 = max(0, xs.start - pad), min(a.shape[1], xs.stop + pad)
        sub = labels[y0:y1, x0:x1] == idx
        area = int(sub.sum())
        if area < MIN_HOLE_AREA:
            continue
        ring = ndimage.binary_dilation(sub, iterations=3) & ~sub
        if not ring.any():
            continue
        ring_mean = float(gray[y0:y1, x0:x1][ring].mean())
        # Dark surround => bounded by product => a genuine hole.
        if ring_mean < 150:
            kill[idx] = True

    if kill.any():
        a[..., 3] = np.where(kill[labels], 0, alpha)

    out = Image.fromarray(a, "RGBA")
    # Feather the recovered edges so the holes don't alias against the dark page.
    out.putalpha(out.split()[3].filter(ImageFilter.GaussianBlur(0.6)))
    return out


def local_cutout(im):
    """Offline fallback: flood-fill the white studio background from the border."""
    im = im.convert("RGBA")
    a = np.array(im)
    rgb = a[..., :3].astype(np.int16)
    white = (rgb.min(axis=2) > 232) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 16)

    labels, n = ndimage.label(white)
    if n:
        border = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
        border.discard(0)
        bg = np.isin(labels, list(border))
        areas = ndimage.sum(white, labels, range(1, n + 1))
        keep = np.zeros(n + 1, dtype=bool)
        keep[1:] = areas >= MIN_HOLE_AREA
        a[..., 3] = np.where(bg | keep[labels], 0, 255)
    out = Image.fromarray(a, "RGBA")
    out.putalpha(out.split()[3].filter(ImageFilter.GaussianBlur(0.6)))
    return out


def cutout(path, use_fal=True):
    if use_fal and FAL_KEY:
        b = fal_cutout(path)
        if b:
            import io
            return punch_enclosed_holes(Image.open(io.BytesIO(b)))
    return local_cutout(Image.open(path))


def trim(im, pad=0.02):
    """Crop to the visible subject with a little breathing room."""
    bbox = im.split()[3].getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    px, py = int((x1 - x0) * pad), int((y1 - y0) * pad)
    return im.crop((max(0, x0 - px), max(0, y0 - py),
                    min(im.width, x1 + px), min(im.height, y1 + py)))


if __name__ == "__main__":
    import sys
    src = sys.argv[1]
    dst = sys.argv[2]
    im = trim(cutout(src))
    im.save(dst)
    print("wrote", dst, im.size)
