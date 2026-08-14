#!/usr/bin/env python3
"""Capture presentation screenshots of the finished site."""
import os

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8899"
OUT = os.path.expanduser("~/Downloads/airsoft-wholesale/shots")
os.makedirs(OUT, exist_ok=True)

SIGN_IN = """() => {
  localStorage.setItem('fs.dealer', JSON.stringify({
    email:'buyer@ridgeline.example', company:'Ridgeline Airsoft Supply',
    location:'Columbus, OH', tier:2, tierName:'Tier 2 — Volume Dealer',
    rep:'D. Almeida', repLine:'+1 617 555 0143', terms:'Net 30',
    creditLimit:40000, balance:12480.55, since:'2026-03-04'}));
  localStorage.setItem('fs.cart', JSON.stringify([
    {id:'raven-470', qty:8}, {id:'matador-53', qty:12}, {id:'raven-390', qty:4}]));
}"""

SHOTS = [
    ("01-home",       "/index.html",      False, 0,    None),
    ("02-catalog",    "/catalog.html",    False, 260,  None),
    ("03-product",    "/product.html?id=raven-470", False, 0, None),
    ("04-inspector",  "/inspector.html",  False, None, "inspector"),
    ("05-compliance", "/compliance.html", False, 560,  None),
    ("06-portal",     "/portal.html",     True,  0,    None),
    ("07-cart",       "/cart.html",       True,  0,    None),
    ("08-quickorder", "/quick-order.html", True, 0,    None),
    ("09-apply",      "/apply.html",      False, 0,    None),
    ("10-login",      "/login.html",      False, 0,    None),
]


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name, path, signed, scroll, special in SHOTS:
            ctx = b.new_context(viewport={"width": 1440, "height": 900},
                                device_scale_factor=2)
            if signed:
                ctx.add_init_script("(" + SIGN_IN + ")()")
            pg = ctx.new_page()
            pg.goto(BASE + path, wait_until="networkidle", timeout=30000)
            pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
            pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")

            if special == "inspector":
                pg.wait_for_timeout(3500)
                pg.evaluate("""() => {
                    const s=document.getElementById('explode');
                    s.value=42; s.dispatchEvent(new Event('input'));
                    document.querySelector('.part-btn[data-key="gearbox"]').click();
                    const st=document.getElementById('stage');
                    const r=st.getBoundingClientRect();
                    scrollTo(0, scrollY + r.top - 100);
                }""")
                pg.wait_for_timeout(1600)
            else:
                if scroll:
                    pg.evaluate(f"scrollTo(0,{scroll})")
                pg.wait_for_timeout(1400)

            pg.screenshot(path=f"{OUT}/{name}.png")
            print("wrote", name, flush=True)
            ctx.close()
        b.close()


if __name__ == "__main__":
    main()
