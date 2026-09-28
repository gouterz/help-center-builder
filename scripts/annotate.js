/*
 * annotate.js: screenshot annotation overlay for help-center pages.
 * Paste the whole file into the browser's JavaScript tool (once per page load).
 * Everything it draws or changes is on-screen only; reload the page to undo it all.
 *
 * Targets can be:
 *   'css selector'                         first VISIBLE match
 *   {text: 'Save', within?, tag?, exact?}  visible element whose text matches
 *   Element | {el: Element}
 *   {x, y, w, h}                           viewport rectangle in CSS px
 *   {union: [target, target, ...]}         one box around several targets
 *
 * API (each call returns the rect it used, or throws with a helpful message):
 *   anno.box(t, {badge, label, side, arrow, pad, color})  box + optional badge/label
 *   anno.badge(t, n, {corner: 'tl'|'tr'|'bl'|'br'})        numbered badge only
 *   anno.label(t, text, {side, arrow})                     pill label (+ arrow)
 *   anno.arrow(fromTarget, toTarget)                       arrow between two targets
 *   anno.blur(t, {radius, round})                          blur what's behind (faces, text)
 *   anno.mask(t, {text})                                   solid block (secrets)
 *   anno.swapText(regexOrString, {within, with})           same-length placeholder text
 *   anno.setValue(t, value)                                set a React/Vue input on screen
 *   anno.find(text, {within})                              list visible matches + rects
 *   anno.rect(t)                                           rect + viewport + devicePixelRatio
 *   anno.config({color, font})                             style
 *   anno.clear()                                           remove every overlay
 */
(() => {
  if (window.anno && window.anno._off) { window.anno.clear(); window.anno._off(); }
  const S = { color: '#E11D48', font: '600 13px system-ui,-apple-system,Segoe UI,Roboto,sans-serif', pad: 4 };
  const items = [];
  let root, svg, swaps = [];

  const visible = (el) => {
    if (!(el instanceof Element)) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return false;
    const cx = Math.min(Math.max(r.left + r.width / 2, 0), innerWidth - 1);
    const cy = Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1);
    const hit = document.elementFromPoint(cx, cy);
    return !hit || el === hit || el.contains(hit) || hit.contains(el);
  };
  const byText = (q) => {
    const scope = q.within ? document.querySelector(q.within) : document.body;
    if (!scope) throw new Error(`anno: container "${q.within}" not found`);
    const want = q.text.trim().toLowerCase();
    const all = [...scope.querySelectorAll(q.tag || '*')].filter((el) => {
      const t = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().toLowerCase();
      return q.exact === false ? t.includes(want) : t === want;
    });
    // smallest visible element wins (the button, not the whole card around it)
    return all.filter(visible).sort((a, b) => (a.innerText || "").length - (b.innerText || "").length)[q.index || 0];
  };
  const resolve = (t) => {
    if (t instanceof Element) return t;
    if (t && t.el) return t.el;
    if (typeof t === 'string') {
      const all = [...document.querySelectorAll(t)];
      const el = all.find(visible);
      if (!el) throw new Error(`anno: no visible match for "${t}" (${all.length} matches, all hidden or covered)`);
      return el;
    }
    if (t && t.text) {
      const el = byText(t);
      if (!el) throw new Error(`anno: no visible element with text "${t.text}". Try anno.find("${t.text}")`);
      return el;
    }
    return t;
  };
  const rectOf = (t) => {
    if (t && t.union) {
      const rs = t.union.map(rectOf);
      const x = Math.min(...rs.map((r) => r.x)), y = Math.min(...rs.map((r) => r.y));
      return { x, y, w: Math.max(...rs.map((r) => r.x + r.w)) - x, h: Math.max(...rs.map((r) => r.y + r.h)) - y };
    }
    const el = resolve(t);
    if (el instanceof Element) { const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }
    if (el && 'x' in el && 'w' in el) return { x: el.x, y: el.y, w: el.w, h: el.h };
    throw new Error('anno: unsupported target ' + JSON.stringify(t));
  };

  const ensureRoot = () => {
    if (root && root.isConnected) return;
    root = document.createElement('div');
    root.id = '__anno_root';
    root.setAttribute('popover', 'manual');
    root.style.cssText = 'all:initial;position:fixed;inset:0;width:100vw;height:100vh;margin:0;padding:0;border:0;background:transparent;overflow:visible;pointer-events:none;z-index:2147483647;';
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%');
    svg.style.cssText = 'all:initial;position:absolute;inset:0;overflow:visible';
    root.appendChild(svg);
    document.documentElement.appendChild(root);
  };
  // Re-open as a popover so the overlay sits above <dialog> modals (the browser "top layer").
  const raise = () => { try { if (root.matches(':popover-open')) root.hidePopover(); root.showPopover(); } catch (e) { /* no popover support: z-index is enough */ } };
  // all:initial keeps the page's own CSS (e.g. div { opacity: .8 }) off the overlay
  const div = (css, text) => { const d = document.createElement('div'); d.style.cssText = 'all:initial;' + css; if (text != null) d.textContent = text; root.appendChild(d); return d; };

  const drawArrow = (x1, y1, x2, y2, color) => {
    const ns = 'http://www.w3.org/2000/svg';
    const ang = Math.atan2(y2 - y1, x2 - x1), L = 12;
    const line = document.createElementNS(ns, 'line');
    Object.entries({ x1, y1, x2: x2 - Math.cos(ang) * 6, y2: y2 - Math.sin(ang) * 6, stroke: color, 'stroke-width': 3, 'stroke-linecap': 'round' }).forEach(([k, v]) => line.setAttribute(k, v));
    const head = document.createElementNS(ns, 'polygon');
    const p = (a) => `${x2 - L * Math.cos(ang + a)},${y2 - L * Math.sin(ang + a)}`;
    head.setAttribute('points', `${x2},${y2} ${p(0.45)} ${p(-0.45)}`);
    head.setAttribute('fill', color);
    svg.append(line, head);
  };
  const edgePoint = (r, px, py) => ({ x: Math.min(Math.max(px, r.x), r.x + r.w), y: Math.min(Math.max(py, r.y), r.y + r.h) });

  const placeLabel = (r, text, o, color) => {
    const el = div(`position:absolute;font:${S.font};color:#fff;background:${color};padding:5px 10px;border-radius:999px;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.25)`, text);
    const lw = el.offsetWidth, lh = el.offsetHeight, gap = o.arrow ? 36 : 10, m = 8;
    const spots = {
      right: [r.x + r.w + gap, r.y + r.h / 2 - lh / 2], left: [r.x - gap - lw, r.y + r.h / 2 - lh / 2],
      bottom: [r.x + r.w / 2 - lw / 2, r.y + r.h + gap], top: [r.x + r.w / 2 - lw / 2, r.y - gap - lh],
    };
    const fits = ([x, y]) => x >= m && y >= m && x + lw <= innerWidth - m && y + lh <= innerHeight - m;
    const side = o.side || ['right', 'left', 'bottom', 'top'].find((s) => fits(spots[s])) || 'bottom';
    let [x, y] = spots[side];
    x = Math.min(Math.max(x, m), innerWidth - lw - m); y = Math.min(Math.max(y, m), innerHeight - lh - m);
    el.style.left = x + 'px'; el.style.top = y + 'px';
    if (o.arrow) {
      const cx = x + lw / 2, cy = y + lh / 2;
      const from = edgePoint({ x, y, w: lw, h: lh }, r.x + r.w / 2, r.y + r.h / 2);
      const to = edgePoint(r, cx, cy);
      drawArrow(from.x, from.y, to.x, to.y, color);
    }
  };
  const placeBadge = (r, n, corner, color) => {
    const d = 24, cx = corner.includes('r') ? r.x + r.w : r.x, cy = corner.includes('b') ? r.y + r.h : r.y;
    const x = Math.min(Math.max(cx - d / 2, 2), innerWidth - d - 2), y = Math.min(Math.max(cy - d / 2, 2), innerHeight - d - 2);
    div(`position:absolute;left:${x}px;top:${y}px;width:${d}px;height:${d}px;border-radius:50%;background:${color};color:#fff;font:700 13px system-ui,sans-serif;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 2px #fff,0 2px 6px rgba(0,0,0,.3)`, String(n));
  };

  const render = () => {
    ensureRoot();
    [...root.children].forEach((c) => c !== svg && c.remove());
    svg.innerHTML = '';
    for (const it of items) {
      let r;
      try { r = rectOf(it.t); } catch (e) { continue; }
      const c = it.o.color || S.color, pad = it.o.pad ?? S.pad;
      const pr = { x: r.x - pad, y: r.y - pad, w: r.w + pad * 2, h: r.h + pad * 2 };
      if (it.kind === 'box') div(`position:absolute;left:${pr.x}px;top:${pr.y}px;width:${pr.w}px;height:${pr.h}px;border:3px solid ${c};border-radius:8px;box-sizing:border-box`);
      if (it.kind === 'blur') div(`position:absolute;left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px;backdrop-filter:blur(${it.o.radius || 10}px);-webkit-backdrop-filter:blur(${it.o.radius || 10}px);background:rgba(255,255,255,.05);border-radius:${it.o.round ? '50%' : '4px'}`);
      if (it.kind === 'mask') div(`position:absolute;left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px;background:${it.o.fill || '#CBD5E1'};border-radius:4px;display:flex;align-items:center;justify-content:center;font:${S.font};color:#475569`, it.o.text || '');
      if (it.kind === 'arrow') { const a = rectOf(it.t2); const f = edgePoint(r, a.x + a.w / 2, a.y + a.h / 2), to = edgePoint(a, r.x + r.w / 2, r.y + r.h / 2); drawArrow(f.x, f.y, to.x, to.y, c); }
      if (it.o.badge != null) placeBadge(pr, it.o.badge, it.o.corner || 'tl', c);
      if (it.o.label) placeLabel(pr, it.o.label, it.o, c);
    }
    raise();
  };
  let queued = false;
  const onMove = () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; if (items.length) render(); }); } };
  addEventListener('scroll', onMove, true);
  addEventListener('resize', onMove);

  const add = (kind, t, o = {}, t2) => { const r = rectOf(t); if (t2) rectOf(t2); items.push({ kind, t, o, t2 }); render(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) }; };
  const mask = (s) => s.replace(/[A-Za-z]/g, 'x').replace(/[0-9]/g, '0');

  window.anno = {
    box: (t, o) => add('box', t, o),
    badge: (t, n, o = {}) => add('none', t, { ...o, badge: n }),
    label: (t, text, o = {}) => add('none', t, { ...o, label: text }),
    arrow: (from, to, o) => add('arrow', from, o, to),
    blur: (t, o) => add('blur', t, o),
    mask: (t, o) => add('mask', t, o),
    swapText(pattern, o = {}) {
      const scope = o.within ? document.querySelector(o.within) : document.body;
      const re = typeof pattern === 'string' ? new RegExp(pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g') : new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g');
      const sub = (m) => (o.with != null ? o.with : mask(m));
      let n = 0;
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      for (let node; (node = walker.nextNode());) {
        const next = node.nodeValue.replace(re, (m) => { n++; return sub(m); });
        if (next !== node.nodeValue) { swaps.push([node, node.nodeValue]); node.nodeValue = next; }
      }
      scope.querySelectorAll('input,textarea').forEach((el) => {
        const next = el.value.replace(re, (m) => { n++; return sub(m); });
        if (next !== el.value) { swaps.push([el, el.value, true]); el.value = next; }
      });
      return `${n} replacement(s); reload the page (or anno.restoreText()) when done`;
    },
    restoreText() { swaps.reverse().forEach(([n, v, isInput]) => (isInput ? (n.value = v) : (n.nodeValue = v))); swaps = []; },
    setValue(t, value) {
      const el = resolve(t);
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set on screen only: do not click Save outside the demo workspace';
    },
    find(text, o = {}) {
      const scope = o.within ? document.querySelector(o.within) : document.body;
      const want = text.trim().toLowerCase();
      return [...scope.querySelectorAll('*')].filter((el) => visible(el) && (el.innerText || el.value || '').trim().toLowerCase().includes(want))
        .sort((a, b) => (a.innerText || "").length - (b.innerText || "").length).slice(0, 8)
        .map((el) => { const r = el.getBoundingClientRect(); return { tag: el.tagName.toLowerCase(), text: (el.innerText || el.value || '').trim().slice(0, 60), rect: [r.left, r.top, r.width, r.height].map(Math.round) }; });
    },
    rect: (t) => ({ ...rectOf(t), innerWidth, innerHeight, dpr: devicePixelRatio }),
    config(o) { Object.assign(S, o); if (items.length) render(); return { ...S }; },
    clear() { items.length = 0; if (root) root.remove(); root = null; },
    _off() { removeEventListener('scroll', onMove, true); removeEventListener('resize', onMove); },
  };
  return 'anno ready';
})();
