# Fieldstock Supply Co. — B2B airsoft wholesale prototype

A working prototype of a US dealer-direct wholesale storefront for **Raven Evolution**
(Canada, AEG platforms) and **Matador Tactical** (Hong Kong, gas shotguns).

**Live:** https://wilsonwu-ai.github.io/fieldstock-airsoft-wholesale/

Static site. No build step, no backend, no dependencies to install.

---

## What it is

| | |
|---|---|
| Products | **273** real SKUs, scraped from both manufacturers |
| Photography | **1,405** real manufacturer photos, background-removed |
| Pages | 10 |
| Checks passing | 40/40 (3 viewports × signed-out/in, all pages) |

### Pages

**Public (dark theme)**
- `index.html` — landing
- `catalog.html` — 273 SKUs, faceted, 48/page, filters in the URL
- `product.html` — PDP, `?id=<product-id>`
- `inspector.html` — 3D platform inspector (Three.js): orbit, explode, click any
  component to see its SKU and price
- `compliance.html` — the four US marking tiers and the do-not-ship list
- `login.html`, `apply.html` — dealer sign-in and 7-step application

**Dealer portal (light theme — a warehouse tool, not a marketing surface)**
- `portal.html` — credit position, reorder, top SKUs by volume
- `quick-order.html` — paste-a-list and CSV bulk order
- `cart.html` — draft order with live tier re-pricing and ZIP-level ship-to blocking

### Run locally

```sh
python3 -m http.server 8899   # then open http://localhost:8899
```

---

## Design decisions, and the evidence behind them

Every visual choice traces to research on what the airsoft community actually
respects. The full rules are in [`docs/DESIGN_CONTRACT.md`](docs/DESIGN_CONTRACT.md).

- **Near-black ground `#0D0F0E`, warm off-white text `#E4E0D9`, one accent
  `#FF6A00`.** Measured from American MilSim, Ballahack, Ferro Concepts and Krytac.
  Pure `#ffffff` body text on near-black is the fastest tell of an unconsidered
  dark theme. Orange is the community default.
- **Condensed display + neutral grotesque body** (Archivo + Inter + JetBrains Mono).
  The formula is consistent across eight measured sites. **No stencil, no Bank
  Gothic** — zero credible tactical brands use them.
- **No AI-generated imagery, anywhere.** This is the community's loudest fraud
  heuristic, not a style preference. Verbatim from r/airsoft: *"all these AI photos
  scream scam and I won't even browse the site further."* Airsofters read receivers
  at part level. `fal.ai` was used **only** for background removal on photographs we
  already had — never to generate a pixel of product.
- **Mixed, dated stock state.** A catalog where everything shows in stock reads as a
  dropshipper. Honest inventory is a trust feature here.
- **The price is the gate, not the product.** The catalog is public and crawlable;
  net pricing requires sign-in. A signed-out visitor is never shown a dealer price,
  and a signed-in dealer is never shown MSRP where their net price belongs — the
  category's signature failure, which one major competitor's own dealer application
  admits to in writing.

---

## Data provenance

Product records and photography were scraped from the manufacturers' own
storefronts (both run OpenCart 3 with the Journal3 theme — the shared stack is
itself corroboration that one operator is behind both brands).

`tools/scrape_catalog.py` → `tools/build_manifest.py` → `tools/build_assets.py`

**These images are the manufacturers' property.** They are used here to prototype a
distribution relationship that is under discussion, not concluded. Image rights
must be confirmed in writing before any public commercial launch.

---

## Honest limits

This is a prototype, and says so where it matters:

- **Sign-in is not authentication.** Any email and password will sign you in; the
  page says so above the fields. Nothing is transmitted or stored beyond a
  `localStorage` flag.
- **No order is ever placed.** The dealer application and the draft order both end
  in a confirmation stating plainly that nothing was submitted.
- **Prices are modelled, not quoted.** MSRP is real and scraped. USD conversion uses
  a fixed demo rate, and the dealer tiers (62% / 55% / 48% of MSRP) are standard
  hardgoods-distribution defaults — not terms anyone has agreed to.
- **Stock levels are generated** deterministically from each SKU, so they are stable
  across reloads. There is no warehouse behind them.
- **The 3D model is representative**, built from primitives. It is not a scan of a
  specific SKU, and the page says so.
- **The compliance page is a scoping summary, not legal advice.** It cites primary
  sources (eCFR, state statutes) and carries a review date. Counsel must confirm it
  before capital is committed.

## Two findings worth reading before the business case

1. **The premise checks out.** Raven Evolution and Matador Tactical have **zero** SKUs
   at Evike, AirsoftGI, US Airsoft, Airsoft Station or Airsoft Extreme. The US is
   genuinely open for both. Watch the trap: US searches for "Raven" return in-stock
   **NUPROL Raven Airsoft** pistols — a different company, different country,
   different product category. That near-miss makes it easy to conclude the opposite.
2. **But the brands may be winding down.** A Canadian dealer carries 51 Raven
   Evolution listings explicitly flagged *"produit discontinué"*, and 23 of 25 Matador
   products are unavailable at another. That is not "a healthy brand awaiting a US
   launch." Confirm current production status with the manufacturer before any
   inventory commitment — everything else is downstream of that answer.
