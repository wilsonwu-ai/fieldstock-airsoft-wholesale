#!/usr/bin/env python3
"""Scrape OpenCart (Journal3) catalogs for Raven Evolution and Matador Tactical.

Both sites run OpenCart 3.x with the Journal3 theme, so one scraper handles both.
Products are discovered from the sitemap, then each product page is parsed for
name / model / price / description / images. Originals (not the resized cache
variants) are downloaded where they can be resolved.
"""
import json
import os
import re
import sys
import time
import urllib.parse as up
from html import unescape
from concurrent.futures import ThreadPoolExecutor

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, ".."))

SITES = {
    "raven": "https://ravenevolution.com",
    "matador": "https://matadortactical.com",
}


def get(url, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return ""


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", s).strip()


def discover_products(base):
    """Find every product_id via the sitemap, then category pages as a fallback."""
    found = set()
    sm = get(f"{base}/index.php?route=information/sitemap")
    found |= set(re.findall(r"product_id=(\d+)", sm))

    cats = set(re.findall(r"route=product/category&(?:amp;)?path=([\d_]+)", sm))
    home = get(f"{base}/")
    cats |= set(re.findall(r"route=product/category&(?:amp;)?path=([\d_]+)", home))
    found |= set(re.findall(r"product_id=(\d+)", home))

    def crawl_cat(path):
        ids = set()
        url = f"{base}/index.php?route=product/category&path={path}&limit=100"
        html = get(url)
        ids |= set(re.findall(r"product_id=(\d+)", html))
        # follow pagination
        for pg in set(re.findall(r"path=" + re.escape(path) + r"&(?:amp;)?limit=100&(?:amp;)?page=(\d+)", html)):
            h2 = get(f"{url}&page={pg}")
            ids |= set(re.findall(r"product_id=(\d+)", h2))
        return ids

    if cats:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for ids in ex.map(crawl_cat, sorted(cats)):
                found |= ids
    return sorted(found, key=int), sorted(cats)


def parse_product(base, pid):
    url = f"{base}/index.php?route=product/product&product_id={pid}"
    html = get(url)
    if not html:
        return None

    def meta(prop):
        m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % prop, html, re.I)
        return unescape(m.group(1)).strip() if m else ""

    name = meta("og:title") or ""
    if not name:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        name = strip_tags(m.group(1)) if m else ""
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return None

    price = ""
    m = re.search(r'<meta[^>]+property="product:price:amount"[^>]+content="([^"]*)"', html, re.I)
    if m:
        price = m.group(1).strip()
    if not price:
        m = re.search(r'"price"\s*:\s*"?([\d.,]+)"?', html)
        price = m.group(1) if m else ""

    model = ""
    m = re.search(r"(?:Product Code|Model|SKU)\s*:?\s*</?[^>]*>?\s*([A-Za-z0-9\-_/\. ]+)", html, re.I)
    if m:
        model = m.group(1).strip()[:60]

    avail = ""
    m = re.search(r"Availability\s*:?\s*</?[^>]*>?\s*([A-Za-z0-9\- ]+)", html, re.I)
    if m:
        avail = m.group(1).strip()[:40]

    desc = ""
    m = re.search(r'id="tab-description"[^>]*>(.*?)</div>\s*(?:<div[^>]+id="tab-|</div>\s*</div>)', html, re.S | re.I)
    if not m:
        m = re.search(r'<div[^>]+class="[^"]*tab-content[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S | re.I)
    if m:
        desc = strip_tags(m.group(1))[:4000]
    if not desc:
        desc = meta("description")[:2000]

    imgs = set()
    for pat in (r'href="([^"]*/image/cache/catalog/[^"]+\.(?:jpg|jpeg|png|webp))"',
                r'(?:src|data-src|data-zoom-image|content)="([^"]*/image/(?:cache/)?catalog/[^"]+\.(?:jpg|jpeg|png|webp))"'):
        for u in re.findall(pat, html, re.I):
            imgs.add(unescape(u))

    cleaned = set()
    for u in imgs:
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = base + u
        if "/Logo/" in u or "logo" in u.rsplit("/", 1)[-1].lower():
            continue
        cleaned.add(u)

    # Map the resized cache path back to the original asset when possible.
    originals = set()
    for u in cleaned:
        if "/image/cache/" in u:
            o = u.replace("/image/cache/", "/image/")
            o = re.sub(r"-\d+x\d+[a-z]*(\.(?:jpg|jpeg|png|webp))$", r"\1", o)
            originals.add(o)
        else:
            originals.add(u)

    return {
        "product_id": pid,
        "url": url,
        "name": name,
        "model": model,
        "price_raw": price,
        "availability": avail,
        "description": desc,
        "images_cache": sorted(cleaned),
        "images_original": sorted(originals),
    }


def download_images(site, products):
    d = os.path.join(OUT, "assets", site)
    os.makedirs(d, exist_ok=True)
    jobs = []
    for p in products:
        for u in p["images_original"]:
            jobs.append((p["product_id"], u))
        for u in p["images_cache"]:
            jobs.append((p["product_id"], u))

    seen, saved = set(), {}

    def dl(job):
        pid, u = job
        key = u.rsplit("/", 1)[-1]
        base_name = up.unquote(key)
        base_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name)
        fn = f"{pid}__{base_name}"
        path = os.path.join(d, fn)
        if fn in seen:
            return None
        seen.add(fn)
        if os.path.exists(path) and os.path.getsize(path) > 2000:
            return (pid, u, path)
        try:
            r = S.get(u, timeout=40)
            if r.status_code == 200 and len(r.content) > 2000:
                with open(path, "wb") as f:
                    f.write(r.content)
                return (pid, u, path)
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(dl, jobs):
            if res:
                pid, u, path = res
                saved.setdefault(pid, []).append(os.path.relpath(path, OUT))
    return saved


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    summary = {}
    for site, base in SITES.items():
        if only and site != only:
            continue
        print(f"\n=== {site} ({base}) ===", flush=True)
        pids, cats = discover_products(base)
        print(f"  categories: {len(cats)}  products discovered: {len(pids)}", flush=True)

        products = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            for p in ex.map(lambda i: parse_product(base, i), pids):
                if p:
                    products.append(p)
        print(f"  products parsed: {len(products)}", flush=True)

        saved = download_images(site, products)
        for p in products:
            p["local_images"] = saved.get(p["product_id"], [])
        n_img = sum(len(v) for v in saved.values())
        print(f"  images downloaded: {n_img}", flush=True)

        out = os.path.join(OUT, "research", f"{site}_catalog.json")
        with open(out, "w") as f:
            json.dump({"site": site, "base": base, "categories": cats,
                       "product_count": len(products), "products": products}, f, indent=2)
        summary[site] = {"products": len(products), "images": n_img, "json": out}

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
