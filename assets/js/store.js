/* FIELDSTOCK — shared data, auth and cart layer.
   Static demo: "auth" is a localStorage flag. No real credential is accepted or
   transmitted, and there is no backend. Pricing rules and stock behaviour are
   modelled faithfully so the flows are honest, but nothing here is a real order
   system. */

const FS = (() => {
  const BRAND = 'FIELDSTOCK';
  const LS_USER = 'fs.dealer';
  const LS_CART = 'fs.cart';
  const FX = 0.74;                    // CAD MSRP -> USD. Demo constant.

  let _products = null;

  /* ---------- data ---------- */
  async function products() {
    if (_products) return _products;
    const res = await fetch(basePath() + 'data/products.json');
    const raw = await res.json();
    _products = raw.map(decorate);
    return _products;
  }

  function basePath() {
    // Pages all live at the site root; keeps file:// preview working too.
    return '';
  }

  /* Deterministic pseudo-random from the SKU, so stock state is stable across
     reloads and pages instead of flickering. */
  function hash(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0) / 4294967295;
  }

  const CASE_PACKS = { 'Rifles': 4, 'Shotguns': 4, 'Pistols': 6, 'HPA Systems': 2,
                       'Magazines': 12, 'Magazines & Shells': 12, 'Parts & Accessories': 6 };

  function decorate(p) {
    const r = hash(p.sku);
    const msrp = Math.round(p.msrp_cad * FX * 100) / 100;

    // Deliberately mixed stock. "Everything in stock" is the dropshipper tell
    // the community explicitly calls out as a scam signal.
    let stock, onHand = 0, eta = null;
    if (r < 0.56)      { stock = 'in';   onHand = 8 + Math.floor(r * 180); }
    else if (r < 0.78) { stock = 'back'; eta = etaDate(r); }
    else if (r < 0.9)  { stock = 'in';   onHand = 1 + Math.floor(r * 9); }
    else               { stock = 'out'; }

    const pack = CASE_PACKS[p.category] || 6;
    return {
      ...p,
      msrp_usd: msrp,
      map_usd: Math.round(msrp * 0.88 * 100) / 100,
      tiers_usd: p.tiers.map(t => ({
        ...t, unit_usd: Math.round(t.unit_price * FX * 100) / 100
      })),
      stock, onHand, eta,
      casePack: pack,
      minQty: pack,
      increment: pack,
      slug: p.id,
      img: p.img || {},
      gallery: p.gallery || [],
      complianceTier: p.category === 'Parts & Accessories' || p.category === 'Magazines'
        ? 'n/a' : 'tier1'
    };
  }

  function etaDate(r) {
    const d = new Date(2026, 7, 13);
    d.setDate(d.getDate() + 14 + Math.floor(r * 60));
    return d.toISOString().slice(0, 10);
  }

  /* ---------- auth (demo only) ---------- */
  function user() {
    try { return JSON.parse(localStorage.getItem(LS_USER)); } catch { return null; }
  }
  function signIn(email) {
    const u = {
      email,
      company: 'Ridgeline Airsoft Supply',
      location: 'Columbus, OH',
      tier: 2,
      tierName: 'Tier 2 — Volume Dealer',
      rep: 'D. Almeida',
      repLine: '+1 617 555 0143',
      terms: 'Net 30',
      creditLimit: 40000,
      balance: 12480.55,
      since: '2026-03-04'
    };
    localStorage.setItem(LS_USER, JSON.stringify(u));
    return u;
  }
  function signOut() { localStorage.removeItem(LS_USER); localStorage.removeItem(LS_CART); }

  /** Dealer net price for a qty, or null when signed out — the price is the
      gate. We never render MSRP where a net price belongs. */
  function netPrice(p, qty) {
    const u = user();
    if (!u) return null;
    const eligible = p.tiers_usd.filter(t => qty >= t.min_qty);
    const t = eligible.length ? eligible[eligible.length - 1] : p.tiers_usd[0];
    return t.unit_usd;
  }
  function tierFor(p, qty) {
    const eligible = p.tiers_usd.filter(t => qty >= t.min_qty);
    return eligible.length ? eligible[eligible.length - 1] : p.tiers_usd[0];
  }
  function nextBreak(p, qty) {
    return p.tiers_usd.find(t => t.min_qty > qty) || null;
  }

  /* ---------- cart ---------- */
  function cart() {
    try { return JSON.parse(localStorage.getItem(LS_CART)) || []; } catch { return []; }
  }
  function saveCart(c) {
    localStorage.setItem(LS_CART, JSON.stringify(c));
    document.dispatchEvent(new CustomEvent('fs:cart', { detail: c }));
  }
  function addToCart(id, qty) {
    const c = cart();
    const row = c.find(r => r.id === id);
    if (row) row.qty += qty; else c.push({ id, qty });
    saveCart(c);
  }
  function setQty(id, qty) {
    let c = cart();
    if (qty <= 0) c = c.filter(r => r.id !== id);
    else { const row = c.find(r => r.id === id); if (row) row.qty = qty; }
    saveCart(c);
  }
  function cartCount() { return cart().reduce((n, r) => n + r.qty, 0); }

  const usd = n => n == null ? '—'
    : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  /* ---------- shared chrome ---------- */
  function header(active) {
    const u = user();
    const n = cartCount();
    return `
<div class="utility">
  <div class="wrap">
    <div class="utility-facts">
      <span>US stocked. US marked. GCC on file for every SKU we ship.</span>
      <span>Quincy, MA</span>
    </div>
    <div style="display:flex;gap:1.2rem">
      ${u ? `<a href="portal.html">${u.company}</a><a href="#" onclick="FS.signOut();location.reload();return false">Sign out</a>`
          : `<a href="login.html">Dealer sign in</a><a href="apply.html">Apply</a>`}
    </div>
  </div>
</div>
<header class="site-header" id="siteHeader">
  <div class="wrap">
    <a href="index.html" class="wordmark"><span class="tick"></span>
      <span>${BRAND}<br><small>SUPPLY CO.</small></span>
    </a>
    <nav class="nav">
      <a href="catalog.html" ${active==='catalog'?'aria-current="page"':''}>Catalog</a>
      <a href="inspector.html" ${active==='inspector'?'aria-current="page"':''}>Inspector</a>
      <a href="compliance.html" class="hide-sm" ${active==='compliance'?'aria-current="page"':''}>Compliance</a>
      ${u ? `<a href="portal.html" ${active==='portal'?'aria-current="page"':''}>Portal</a>
             <a href="cart.html" class="btn btn-sm">Cart ${n?`(${n})`:''}</a>`
          : `<a href="apply.html" class="btn btn-sm">Apply for pricing</a>`}
    </nav>
  </div>
</header>`;
  }

  function footer() {
    return `
<footer class="site-footer">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <div class="wordmark" style="margin-bottom:.9rem"><span class="tick"></span>
          <span>${BRAND}<br><small>SUPPLY CO.</small></span></div>
        <p style="color:var(--text-2);font-size:.86rem;max-width:34ch">
          Dealer-direct wholesale for Raven Evolution and Matador Tactical.
          US warehoused, US marked, sold only to approved retailers.</p>
      </div>
      <div><h4>Catalog</h4>
        <a href="catalog.html?category=Rifles">Rifles</a>
        <a href="catalog.html?category=Shotguns">Shotguns</a>
        <a href="catalog.html?category=HPA%20Systems">HPA</a>
        <a href="catalog.html?category=Parts%20%26%20Accessories">Parts</a></div>
      <div><h4>Dealers</h4>
        <a href="apply.html">Apply for an account</a>
        <a href="login.html">Sign in</a>
        <a href="portal.html">Portal</a>
        <a href="compliance.html">Compliance pack</a></div>
      <div><h4>Company</h4>
        <a href="index.html#brands">Brands we carry</a>
        <a href="compliance.html">Marking tiers</a>
        <a href="#">Contact</a></div>
    </div>
    <div class="legal">
      <span>&copy; 2026 Fieldstock Supply Co. Trade sales only. Not for sale to persons under 18.</span>
      <span>Compliance summaries are scoping notes, not legal advice.</span>
    </div>
  </div>
</footer>`;
  }

  function mountChrome(active) {
    const h = document.getElementById('chrome-header');
    if (h) h.innerHTML = header(active);
    const f = document.getElementById('chrome-footer');
    if (f) f.innerHTML = footer();
    const hdr = document.getElementById('siteHeader');
    if (hdr) {
      const onScroll = () => hdr.classList.toggle('stuck', window.scrollY > 12);
      onScroll(); addEventListener('scroll', onScroll, { passive: true });
    }
  }

  function revealOnScroll(sel = '.reveal') {
    const els = document.querySelectorAll(sel);
    if (!els.length) return;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach(e => e.classList.add('in')); return;
    }
    const io = new IntersectionObserver(es => {
      es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: .12, rootMargin: '0px 0px -8% 0px' });
    els.forEach(e => io.observe(e));
  }

  const STOCK_LABEL = {
    in: 'In stock', back: 'On the water', out: 'Sold out', blocked: 'Restricted'
  };

  function stockPill(p) {
    if (p.stock === 'in')   return `<span class="pill in">${p.onHand > 20 ? 'In stock' : `Low — ${p.onHand} left`}</span>`;
    if (p.stock === 'back') return `<span class="pill back">Due ${p.eta}</span>`;
    return `<span class="pill out">Sold out</span>`;
  }

  return { products, user, signIn, signOut, netPrice, tierFor, nextBreak,
           cart, addToCart, setQty, cartCount, saveCart, usd, header, footer,
           mountChrome, revealOnScroll, stockPill, STOCK_LABEL, BRAND, FX };
})();
