# HARDPOINT SUPPLY CO. — Design Contract (v1, frozen)

Every builder reads this file and nothing else for design decisions. Values are
measured from real sites in the research pass, not invented. Do not "improve"
tokens locally — change this file or leave them alone.

Working brand name: **HARDPOINT SUPPLY CO.** — placeholder, trivially renameable
(it lives in one JS constant and the `<title>`). "Hardpoint" is real technical
vocabulary (a mounting point), which the community reads as native, and it
carries no stolen-valor or mall-ninja freight.

**Positioning:** US dealer-direct wholesale distribution for Raven Evolution
(Canada, AEGs) and Matador Tactical (Hong Kong, gas shotguns). Neither brand
currently has US retail shelf presence. We are the import, compliance and
fulfillment layer between the factory and US e-commerce retailers.

**Tagline:** Dealer-direct airsoft distribution.

---

## 1. Color tokens

Measured from American MilSim (#0a0a0a/#121212 ground, #e2dfda warm off-white,
#ff7b00 orange), Ferro Concepts, Krytac (#f99f38 amber) and atlas.neuro2.ai
(near-monochrome + exactly one saturated accent).

```css
--bg:          #0a0a0a;  /* page ground — never pure #000 alone */
--surface:     #121212;  /* cards, panels */
--surface-2:   #1a1a1a;  /* raised / hover */
--surface-3:   #232323;  /* input wells, table stripes */
--border:      #2a2a2a;  /* hairlines */
--border-lit:  #3a3a3a;  /* hover hairlines */

--text:        #e2dfda;  /* warm off-white — NOT #ffffff */
--text-dim:    #8a8681;
--text-mute:   #5c5955;

--accent:      #ff7b00;  /* THE signal color. CTAs, active state, highlight */
--accent-warm: #f99f38;  /* amber, secondary emphasis only */
--accent-deep: #c25a00;  /* pressed state */

--ok:          #4a9d5f;  /* in stock */
--warn:        #d9a441;  /* backorder / low */
--danger:      #d22826;  /* restricted / out */
```

**Rule: exactly one saturated accent doing all CTA work.** Orange is the
community default. Do not introduce a second saturated hue for decoration.

## 2. Typography

- **Display:** `Oswald` (600/700) — condensed. Community-native; Evike runs
  Roboto Condensed, American MilSim runs Rift, Ferro runs Open Sans Condensed.
- **Body:** `Inter` (400/500/600) — neutral grotesque.
- **Mono:** `JetBrains Mono` (400/500) — SKUs, specs, prices, quantities.

Load from Google Fonts. Uppercase + `letter-spacing: 0.06em` on display for
section headers. **Banned: stencil faces, Bank Gothic, any "army font."** Bank
Gothic specifically is documented as the typographic equivalent of a lens flare.

## 3. Photography and imagery

Trust hierarchy (research-ranked, highest first):
1. Real field/action photography at named events
2. Full-kit loadout on a person in-environment
3. Technical teardown / internals / cutaway
4. Gear flatlay
5. Studio hero on seamless white

We hold #5 (1,405 real scraped studio shots). Use them, and compensate for the
missing top of the hierarchy with **technical density** — exploded views, spec
tables, internals — rather than with borrowed lifestyle imagery we do not own.

### AI imagery — hard rule

**Zero AI-generated product or field imagery. Anywhere. Ever.**

This is not stylistic. It is the community's single loudest fraud heuristic —
verbatim from r/airsoft: *"all these AI photos scream scam and I won't even
browse the site further at that point, even if it turns out to be a legit site."*
Airsofters read receivers and rails at part level and will spot generation
artifacts before they read a word of copy.

**fal.ai is therefore restricted to non-generative operations on photos we
already hold:** background removal/cutout, upscaling, denoise, relight. Never
`text-to-image`, never inventing a product, never a synthetic field scene. Every
pixel of every gun on the site must trace back to a real photograph of that
exact SKU.

## 4. Motion and 3D

Constants lifted from the atlas.neuro2.ai bundle (the user's cited reference):

- Three.js + `OrbitControls`, `enableDamping: true`, `dampingFactor: 0.05–0.08`
- `minDistance` / `maxDistance` bounded — the user can never fly inside the
  model or lose it
- `autoRotate` ~1.2 after idle, so the hero is never static
- `ACESFilmicToneMapping`, `toneMappingExposure ≈ 1.05`
- `setPixelRatio(Math.min(devicePixelRatio, 2))`

**The black-on-black problem is the defining technical constraint.** A matte
black rifle on a near-black ground is a silhouette with no readable form. Three
required fixes:
1. Strong **rim/edge lighting** — two cool rim lights at rear-left and
   rear-right to separate the silhouette from the ground
2. A subtle **radial gradient stage** behind the model, never flat black
3. PBR values: anodized aluminium `metalness .9 / roughness .35`; steel
   `metalness .85 / roughness .3`; polymer `metalness .02 / roughness .5`

**Film grain / dither on every dark gradient.** Not decoration — an 8-bit dark
gradient bands visibly without it.

Scroll: GSAP ScrollTrigger, three patterns only — pin, scrub (`scrub: 1`), and
reveal. Respect `prefers-reduced-motion` on all of it.

## 5. Layout

- Bento grid for **spec sheets**, not for the hero.
- Sticky category rail (McMaster-Carr is the canonical B2B reference).
- Dark-first. No light mode in v1.

## 6. Anti-patterns — automatic QA failures

From the community research. Any of these present = the page fails review.

- ❌ AI-generated imagery of any kind
- ❌ "Mall ninja" visual accumulation — decorative elements that aren't
  load-bearing. Every element earns its place, same standard the community
  applies to a rail.
- ❌ Badge encrustation, countdown timers, fake-urgency theater, testimonial
  carousels. Apex brands (Crye, Ferro) run zero of these.
- ❌ **"Everything in stock."** A catalog where every line shows available reads
  as a dropshipper tell. Stock state must be granular and mixed.
- ❌ Earnest military-operator voice, fake unit insignia, real qualification tabs.
- ❌ Pure `#ffffff` body text on the dark ground.
- ❌ A second saturated accent hue.
- ❌ Showing a dealer a price that is not that dealer's price.

## 7. B2B behavior contract

- **Two front doors.** Catalog is public and crawlable (specs, MSRP/MAP, brand
  story). **Price is the gate**, not the product. Logged-out users see
  "Sign in for dealer pricing", never a price we'd have to walk back.
- **Three independent quantity rules** modeled per variant: `min_qty`,
  `increment` (case pack), `max_qty`. Surface all three on the PDP and in cart.
  The qty stepper snaps to valid multiples.
- **Price-break table on the PDP**: qty range | unit price | extended | savings.
  Live cart nudge — "Add 4 more to reach the 25-unit tier, saves $184."
- **Tier ladder** (modelling defaults, not quoted terms):
  - Tier 3 Stocking Dealer — 1+ units — 62% of MSRP
  - Tier 2 Volume Dealer — 10+ units — 55% of MSRP
  - Tier 1 Master Dealer — 25+ units — 48% of MSRP
- **Dealer application** is a staged form with a published SLA
  ("most applications reviewed within 5 business days") and a resale-certificate
  upload — the resale cert is legally load-bearing, not a formality.
- **Reorder is the returning dealer's home screen**: last order, top SKUs by
  12-month volume, saved lists.
- **Quick order by SKU**: paste box accepting comma / space / newline separated
  input, dedupes and sums repeats; plus CSV upload with a template.
- **Company-level accounts**, not user-level (company → locations → named
  buyers). Retrofitting this later is a rewrite.

## 8. Compliance surface — a moat, shown not hidden

The marking regime is real operational overhead that suppresses grey-market
competition. Show it as capability. Every gun SKU carries a compliance badge.

- Federal rule is **16 CFR Part 1272** (CPSC), color **SAE AMS STD 595A-17
  12199**. It is *not* 15 CFR 272 — that Commerce rule was removed effective
  2026-02-19. Never cite the old one.
- **Tier 1 (~40 states):** federal blaze-orange muzzle marking.
- **Tier 2 California:** federal marking + fluorescent trigger guard + two 2cm
  non-removable fluorescent bands (Penal Code 16700(b)(4), AB 1798).
- **Tier 3 New York:** strictest marking regime in the country, actively
  enforced against online sellers shipping into NY.
- **Blocked at cart by ZIP, not state:** New Jersey statewide; NYC, Chicago and
  Philadelphia municipally. Chicago Municipal Code 4-144-190 is the clearest
  genuine ban. A state-level rule alone misses a Manhattan or Chicago ZIP.

Every compliance string on the site must be accompanied by the standing note
that this is a scoping summary and **not a legal opinion** — counsel confirms
before capital is committed.

## 9. Copy voice

Practitioner, self-aware, declarative. "For players, by players" is the
category's shared register. State verifiable specifics — founding year, address,
phone, named people, dated archives. Adjectives ("premium", "elite", "tactical")
prove nothing; dates and part numbers do.

Never: earnest operator cosplay, stolen valor, hype.
