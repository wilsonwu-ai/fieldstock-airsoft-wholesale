#!/usr/bin/env python3
"""Turn the two scraped catalogs into one clean B2B product manifest.

Per product we keep: a recovered SKU, a taxonomy assignment, MSRP, derived
wholesale tiers, and a deduplicated ordered image list with the full-resolution
original first. Shared theme graphics (the "related products" strip, which the
Journal3 theme repeats on every page) are excluded.
"""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

SIZE_SUFFIX = re.compile(r"-\d+x\d+[a-z]*$", re.I)
SKU_PAT = re.compile(r"^([A-Z]{2,4}(?:-[A-Z0-9]+){1,4})", re.I)

# MSRP -> dealer cost. Standard hardgoods distribution: dealers buy at ~50-60%
# of MSRP depending on volume. These are modelling defaults, not quoted terms.
TIERS = [
    ("Tier 3 — Stocking Dealer", 1, 0.62),
    ("Tier 2 — Volume Dealer", 10, 0.55),
    ("Tier 1 — Master Dealer", 25, 0.48),
]


def base_name(fn):
    stem, ext = os.path.splitext(fn)
    return SIZE_SUFFIX.sub("", stem), ext


def pixels(path):
    """Cheap dimension probe for jpg/png without importing an image library."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return int.from_bytes(head[16:20], "big") * int.from_bytes(head[20:24], "big")
    except Exception:
        pass
    try:
        return os.path.getsize(path)
    except Exception:
        return 0


def classify(name, desc, site):
    n = (name + " " + desc[:300]).lower()
    if site == "matador":
        if "magazine" in n or "shell" in n:
            return "Magazines & Shells", "Shotgun Shells"
        if "kinetic" in n or "coil" in n:
            return "Shotguns", "Kinetic Coil"
        if re.search(r"\b(tsg|csg|ssg)\b", n) or "shotgun" in n:
            return "Shotguns", "Gas Pump Action"
        return "Parts & Accessories", "Accessories"

    # Raven
    if "hpa" in n or "engine" in n or "polarstar" in n:
        return "HPA Systems", "HPA"
    if "bolt" in n or "sniper" in n or re.search(r"\bsrs\b", n):
        return "Rifles", "Bolt Action"
    if "lmg" in n or "m249" in n or "support" in n:
        return "Rifles", "LMG / Support"
    if "pistol" in n or "gbb" in n or "hi-capa" in n or "glock" in n:
        return "Pistols", "Gas Blowback"
    if "magazine" in n or re.search(r"\bmag\b", n):
        return "Magazines", "Magazines"
    if "battery" in n or "charger" in n:
        return "Parts & Accessories", "Batteries & Charging"
    if any(k in n for k in ("rail", "handguard", "grip", "stock", "suppressor",
                            "silencer", "barrel", "hop", "gearbox", "motor",
                            "piston", "gear", "nozzle", "spring", "mosfet")):
        return "Parts & Accessories", "Parts"
    if re.search(r"\b(ak|akm|ak47|ak74)\b", n):
        return "Rifles", "AK Platform"
    if re.search(r"\b(m4|ar15|416|mk18|cqb)\b", n) or "elite" in n or "ore" in n or "neo" in n or "evo" in n:
        return "Rifles", "M4 / AR Platform"
    return "Parts & Accessories", "Accessories"


def line_of(name, site):
    if site == "matador":
        m = re.search(r"\b(TSG|CSG|SSG)\b", name, re.I)
        return m.group(1).upper() if m else "Matador"
    m = re.search(r"\bRaven\s+(ELITE|ORE|NEO|BOLT|EVO|HPA)\b", name, re.I)
    if m:
        return "Raven " + m.group(1).upper()
    for k in ("ELITE", "ORE", "NEO", "BOLT", "EVO", "HPA"):
        if re.search(r"\b" + k + r"\b", name, re.I):
            return "Raven " + k
    return "Raven"


def main():
    out = []
    for site, brand in (("raven", "Raven Evolution"), ("matador", "Matador Tactical")):
        d = json.load(open(os.path.join(ROOT, "research", f"{site}_catalog.json")))
        ps = d["products"]

        # An image basename used by many products is a theme graphic, not a photo.
        freq = collections.Counter()
        for p in ps:
            for f in {os.path.basename(x).split("__", 1)[-1] for x in p["local_images"]}:
                freq[base_name(f)[0]] += 1
        shared_cut = max(3, len(ps) * 0.4)

        for p in ps:
            # Group this product's files by their size-stripped stem, keep the largest.
            groups = collections.defaultdict(list)
            for rel in p["local_images"]:
                fn = os.path.basename(rel).split("__", 1)[-1]
                stem, _ = base_name(fn)
                if freq[stem] >= shared_cut:
                    continue
                groups[stem].append(rel)

            imgs = []
            for stem, rels in groups.items():
                best = max(rels, key=lambda r: pixels(os.path.join(ROOT, r)))
                imgs.append((stem, best))
            imgs.sort(key=lambda t: (not re.search(r"_1$|-1$", t[0]), t[0]))
            image_list = [r for _, r in imgs]

            sku = ""
            for stem, _ in imgs:
                m = SKU_PAT.match(stem)
                if m and not m.group(1).lower().startswith(("poster", "title")):
                    sku = m.group(1).upper()
                    break
            if not sku:
                sku = f"{site[:3].upper()}-{p['product_id']}"

            try:
                msrp = float(str(p["price_raw"]).replace(",", ""))
            except Exception:
                msrp = 0.0

            cat, sub = classify(p["name"], p.get("description", ""), site)
            out.append({
                "id": f"{site}-{p['product_id']}",
                "sku": sku,
                "name": re.sub(r"\s+", " ", p["name"]).strip(),
                "brand": brand,
                "line": line_of(p["name"], site),
                "category": cat,
                "subcategory": sub,
                "msrp_cad": round(msrp, 2),
                "tiers": [{"name": t, "min_qty": q,
                           "unit_price": round(msrp * m, 2),
                           "margin_pct": round((1 - m) * 100)} for t, q, m in TIERS],
                "description": re.sub(r"\s+", " ", p.get("description", ""))[:1200],
                "source_url": p["url"],
                "images": image_list[:10],
                "image_count": len(image_list),
            })

    out.sort(key=lambda x: (x["brand"], x["category"], -x["msrp_cad"]))
    path = os.path.join(ROOT, "research", "products.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"products: {len(out)}   -> {path}")
    print(f"total images referenced: {sum(len(p['images']) for p in out)}")
    print(f"products with zero images: {sum(1 for p in out if not p['images'])}")
    print(f"products with no real SKU:  {sum(1 for p in out if re.match(r'^(RAV|MAT)-\\d+$', p['sku']))}")
    for key in ("brand", "category", "line"):
        c = collections.Counter(p[key] for p in out)
        print(f"\n-- by {key} --")
        for k, v in c.most_common():
            print(f"   {v:>4}  {k}")


if __name__ == "__main__":
    main()
