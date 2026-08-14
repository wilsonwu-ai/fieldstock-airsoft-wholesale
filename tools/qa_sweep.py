#!/usr/bin/env python3
"""Full-site QA sweep.

Every page, signed out and signed in, at three widths. Fails on console errors,
failed requests, horizontal overflow, and — the one that matters commercially —
any dealer price leaking to a signed-out visitor.
"""
import json
import re
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8899"
PAGES = ["index", "catalog", "product", "inspector", "compliance",
         "login", "apply", "portal", "quick-order", "cart"]
WIDTHS = [(380, 780), (768, 900), (1440, 900)]

SIGN_IN = """() => {
  localStorage.setItem('fs.dealer', JSON.stringify({
    email:'buyer@ridgeline.example', company:'Ridgeline Airsoft Supply',
    location:'Columbus, OH', tier:2, tierName:'Tier 2 — Volume Dealer',
    rep:'D. Almeida', repLine:'+1 617 555 0143', terms:'Net 30',
    creditLimit:40000, balance:12480.55, since:'2026-03-04'}));
}"""

results = []


def check(pw, page_name, width, height, signed_in):
    url = f"{BASE}/{page_name}.html"
    if page_name == "product":
        url += "?id=raven-470"

    errors, failed = [], []
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height})
    if signed_in:
        ctx.add_init_script("(" + SIGN_IN + ")()")
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text[:180]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)[:180]))
    pg.on("requestfailed",
          lambda r: (None if (r.failure or "").find("ERR_ABORTED") >= 0
                     else failed.append(f"{r.url.split('/')[-1]} {r.failure}"[:120])))


    try:
        pg.goto(url, wait_until="networkidle", timeout=25000)
    except Exception as e:
        errors.append("NAV: " + str(e)[:120])

    pg.wait_for_timeout(1200)

    doc_w = pg.evaluate("document.documentElement.scrollWidth")
    overflow = doc_w > width + 2
    text = pg.evaluate("document.body.innerText")

    # A signed-out visitor must never be shown a dealer net price. Every page
    # states its gate in words instead.
    leak = None
    if not signed_in:
        if re.search(r"your (dealer )?(net )?(price|cost)\s*[:\-]?\s*\$", text, re.I):
            leak = "net price rendered while signed out"

    gate = ("sign in for" in text.lower()) or ("sign in to" in text.lower())

    browser.close()
    return {
        "page": page_name, "w": width, "signed_in": signed_in,
        "errors": errors[:4], "failed": failed[:4],
        "overflow": overflow, "docW": doc_w,
        "leak": leak, "gate": gate, "textLen": len(text),
    }


def main():
    with sync_playwright() as pw:
        for name in PAGES:
            for (w, h) in WIDTHS:
                for signed in (False, True):
                    if w != 1440 and signed:
                        continue          # signed-in only needs one width per page
                    results.append(check(pw, name, w, h, signed))
                    r = results[-1]
                    flag = "FAIL" if (r["errors"] or r["failed"] or r["overflow"] or r["leak"]) else "ok  "
                    print(f"{flag} {name:12} {w:>5}px signed_in={str(signed):5} "
                          f"len={r['textLen']:>6} {'OVERFLOW ' + str(r['docW']) if r['overflow'] else ''}"
                          f"{' LEAK:' + r['leak'] if r['leak'] else ''}", flush=True)
                    for e in r["errors"]:
                        print("      err:", e, flush=True)
                    for f in r["failed"]:
                        print("      req:", f, flush=True)

    bad = [r for r in results if r["errors"] or r["failed"] or r["overflow"] or r["leak"]]
    print(f"\n=== {len(results) - len(bad)}/{len(results)} checks passed ===")
    json.dump(results, open("research/qa_results.json", "w"), indent=2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
