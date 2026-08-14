#!/usr/bin/env python3
"""Repair SKUs in the shipped product feed.

The first pass derived each SKU from the first image filename, which collided
badly: many products lead with a shared line poster or category banner, so 126
of 273 products ended up sharing 16 SKU values. A SKU is how a dealer orders,
so duplicates are a correctness bug, not a cosmetic one.

The fix: only take a SKU from an image filename that belongs to exactly one
product, ignore poster/banner/logo artwork, and fall back to a deterministic
per-product code. Also flags the 17 records with no published price so the UI
can say "on request" instead of rendering $0.00.
"""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FEED = os.path.join(ROOT, "site", "data", "products.json")

SIZE_SUFFIX = re.compile(r"-\d+x\d+[a-z]*$", re.I)
SKU_PAT = re.compile(r"^([A-Z]{2,5}(?:-[A-Z0-9]+){1,4})$", re.I)
ARTWORK = re.compile(r"poster|title|banner|logo|graphic|background|wallpaper|web[\s_-]?design",
                     re.I)

BRAND_PREFIX = {"Raven Evolution": "RAV", "Matador Tactical": "MAT"}


def stem(rel):
    fn = os.path.basename(rel).split("__", 1)[-1]
    s, _ = os.path.splitext(fn)
    return SIZE_SUFFIX.sub("", s)


def main():
    ps = json.load(open(FEED))

    # How many distinct products use each image stem?
    owners = collections.defaultdict(set)
    for p in ps:
        for rel in p.get("images", []):
            owners[stem(rel)].add(p["id"])

    assigned, changed, fallback = set(), 0, 0
    for p in ps:
        old = p["sku"]
        pick = None
        for rel in p.get("images", []):
            st = stem(rel)
            if len(owners[st]) != 1:        # shared artwork, not this product's SKU
                continue
            if ARTWORK.search(st):
                continue
            m = SKU_PAT.match(st)
            cand = (m.group(1) if m else st).upper()
            cand = re.sub(r"[^A-Z0-9-]", "-", cand).strip("-")
            if len(cand) < 4 or cand in assigned:
                continue
            pick = cand
            break

        if not pick:
            pick = f"{BRAND_PREFIX.get(p['brand'], 'FS')}-{p['product_id'] if 'product_id' in p else p['id'].split('-')[-1]}"
            fallback += 1
        if pick in assigned:                 # last-resort disambiguation
            n = 2
            while f"{pick}-{n}" in assigned:
                n += 1
            pick = f"{pick}-{n}"

        assigned.add(pick)
        if pick != old:
            changed += 1
        p["sku"] = pick

        # 17 records carry no published price. Render "on request", never $0.00.
        p["price_on_request"] = not p.get("msrp_cad")

    json.dump(ps, open(FEED, "w"), separators=(",", ":"))

    c = collections.Counter(p["sku"] for p in ps)
    dups = {k: v for k, v in c.items() if v > 1}
    print(f"products: {len(ps)}")
    print(f"unique SKUs: {len(c)}   duplicates remaining: {len(dups)}")
    print(f"changed: {changed}   generated fallbacks: {fallback}")
    print(f"price-on-request records: {sum(1 for p in ps if p['price_on_request'])}")
    print("\nsamples:")
    for p in ps[:6]:
        print(f"  {p['sku']:26} {p['name'][:52]}")


if __name__ == "__main__":
    main()
