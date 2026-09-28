#!/usr/bin/env python3
"""Build a single static HTML page that shows new help pages with their images, so the
founder can read everything before it's published. Use it when the docs platform can't
preview a branch, or when the pages will be pasted into a hosted help center.

Usage:
  python build_review.py DOCS_ROOT --pages a.md b.md ... --out REVIEW_DIR
                         [--overview handoff.md] [--title "Help center review"]
                         [--static DIR] [--site-url https://docs.example.com]

Understands GitBook blocks ({% hint %}, {% tabs %}, {% embed %}, {% content-ref %}),
Docusaurus admonitions (:::note ... :::) and common Mintlify callouts
(<Note>, <Tip>, <Info>, <Warning>, <Check>, <Frame>, <Steps>/<Step>).
Links between pages in the set become in-page links; links to other pages point to
--site-url when given. Images are copied into REVIEW_DIR/assets.

The output may include your internal handoff note: keep it private and out of the repo.
Needs markdown-it-py: pip install markdown-it-py
"""
import argparse
import html
import os
import re
import shutil

from markdown_it import MarkdownIt

MD = MarkdownIt('commonmark', {'html': True}).enable('table')
CALLOUT_CSS = {'info': 'info', 'note': 'info', 'tip': 'success', 'success': 'success', 'check': 'success',
               'warning': 'warning', 'caution': 'warning', 'danger': 'danger', 'error': 'danger'}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def split_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        return {}, text
    fm, body = {}, text[m.end():]
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        k = re.match(r'^(\w[\w-]*):\s*(.*)$', lines[i])
        if k:
            key, val = k.group(1), k.group(2).strip()
            if val in ('>-', '>', '|', '|-'):
                parts = []
                while i + 1 < len(lines) and (lines[i + 1].startswith(' ') or not lines[i + 1].strip()):
                    i += 1
                    parts.append(lines[i].strip())
                val = ' '.join(p for p in parts if p)
            fm[key] = val.strip('"\'')
        i += 1
    return fm, body


def callout(kind, inner, title=''):
    css = CALLOUT_CSS.get(kind.lower(), 'info')
    head = f'<p class="co-title">{html.escape(title)}</p>' if title else ''
    return f'\n\n<div class="callout {css}">{head}\n\n{inner.strip()}\n\n</div>\n\n'


def preprocess(body):
    # GitBook
    body = re.sub(r'{%\s*hint\s+style="(\w+)"\s*%}(.*?){%\s*endhint\s*%}', lambda m: callout(m.group(1), m.group(2)), body, flags=re.S)
    body = re.sub(r'{%\s*tab\s+title="([^"]*)"\s*%}', lambda m: f'\n\n<p class="tab-title">{html.escape(m.group(1))}</p>\n\n', body)
    body = re.sub(r'{%\s*(?:tabs|endtabs|endtab|endcontent-ref)\s*%}', '\n', body)
    body = re.sub(r'{%\s*content-ref\s+url="[^"]*"\s*%}', '\n', body)
    body = re.sub(r'{%\s*embed\s+url="([^"]*)"[^%]*%}', r'\n\n[Embedded: \1](\1)\n\n', body)
    # Docusaurus admonitions
    body = re.sub(r'^:::(\w+)[ \t]*(.*?)\n(.*?)^:::[ \t]*$', lambda m: callout(m.group(1), m.group(3), m.group(2)), body, flags=re.S | re.M)
    # Mintlify-style components
    body = re.sub(r'<(Note|Tip|Info|Warning|Check|Danger)(?:\s[^>]*)?>(.*?)</\1>', lambda m: callout(m.group(1), m.group(2)), body, flags=re.S)
    body = re.sub(r'<Frame(?:\s+caption="([^"]*)")?[^>]*>(.*?)</Frame>',
                  lambda m: f'\n\n<figure>{m.group(2).strip()}' + (f'<figcaption>{html.escape(m.group(1))}</figcaption>' if m.group(1) else '') + '</figure>\n\n', body, flags=re.S)
    body = re.sub(r'<Steps>', '\n\n<div class="steps">\n\n', body)
    body = re.sub(r'</Steps>', '\n\n</div>\n\n', body)
    body = re.sub(r'<Step\s+title="([^"]*)"[^>]*>', lambda m: f'\n\n<div class="step"><p class="step-title">{html.escape(m.group(1))}</p>\n\n', body)
    body = re.sub(r'</Step>', '\n\n</div>\n\n', body)
    body = re.sub(r'^(import|export)\s.*$', '', body, flags=re.M)  # MDX imports
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root')
    ap.add_argument('--pages', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--overview')
    ap.add_argument('--title', default='Help center review')
    ap.add_argument('--static')
    ap.add_argument('--site-url', default='')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    static = os.path.abspath(a.static or root)
    os.makedirs(os.path.join(a.out, 'assets'), exist_ok=True)

    pages = [os.path.abspath(p) for p in a.pages]
    ids = {p: 'p-' + slug(os.path.relpath(p, root)) for p in pages}
    copied = {}

    def fix_src(page, src):
        if src.startswith(('http://', 'https://', 'data:')):
            return src
        base = static if src.startswith('/') else os.path.dirname(page)
        p = os.path.normpath(os.path.join(base, src.lstrip('/')))
        if not os.path.isfile(p):
            return src
        if p not in copied:
            name = f'{len(copied):03d}-{os.path.basename(p)}'
            shutil.copy2(p, os.path.join(a.out, 'assets', name))
            copied[p] = 'assets/' + name
        return copied[p]

    def fix_href(page, href):
        if href.startswith(('http://', 'https://', 'mailto:', '#')):
            return href
        target = href.split('#')[0]
        base = static if target.startswith('/') else os.path.dirname(page)
        p = os.path.normpath(os.path.join(base, target.lstrip('/')))
        for cand in (p, p + '.md', p + '.mdx'):
            if cand in ids:
                return '#' + ids[cand]
        if a.site_url:
            rel = os.path.relpath(p, root).replace('\\', '/')
            return a.site_url.rstrip('/') + '/' + re.sub(r'(README)?\.mdx?$', '', rel)
        return href

    sections, nav = [], []
    if a.overview:
        with open(a.overview, encoding='utf-8') as fh:
            sections.append(f'<section id="overview" class="page">{MD.render(preprocess(fh.read()))}</section>')
        nav.append(('', '<a href="#overview">Overview</a>'))
    for p in pages:
        with open(p, encoding='utf-8') as fh:
            fm, body = split_frontmatter(fh.read())
        out = MD.render(preprocess(body))
        out = re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)', lambda m: m.group(1) + fix_src(p, html.unescape(m.group(2))), out)
        out = re.sub(r'(<a\b[^>]*\bhref=")([^"]+)', lambda m: m.group(1) + fix_href(p, html.unescape(m.group(2))), out)
        title = fm.get('title') or (re.search(r'<h1>(.*?)</h1>', out) or [None, os.path.basename(p)])[1]
        desc = f'<p class="desc"><span>Description:</span> {html.escape(fm["description"])}</p>' if fm.get('description') else ''
        rel = os.path.relpath(p, root).replace('\\', '/')
        if fm.get('title') and '<h1>' not in out:
            out = f'<h1>{html.escape(fm["title"])}</h1>' + out
        sections.append(f'<section id="{ids[p]}" class="page"><p class="path">{html.escape(rel)}</p>{desc}{out}</section>')
        nav.append((os.path.dirname(rel), f'<a href="#{ids[p]}">{re.sub("<[^>]+>", "", title)}</a>'))

    nav_html, group = [], None
    for g, link in nav:
        if g != group:
            nav_html.append(f'<p class="group">{html.escape(g or "")}</p>')
            group = g
        nav_html.append(link)

    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(a.title)}</title><style>
:root{{--bg:#fff;--fg:#1f2937;--mute:#6b7280;--line:#e5e7eb;--side:#f9fafb;--link:#0e7490}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111827;--fg:#e5e7eb;--mute:#9ca3af;--line:#374151;--side:#0b1220;--link:#67e8f9}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
nav{{position:fixed;top:0;left:0;bottom:0;width:300px;overflow:auto;padding:20px 16px;background:var(--side);border-right:1px solid var(--line);font-size:14px}}
nav a{{display:block;padding:4px 0;color:var(--fg);text-decoration:none}}nav a:hover{{color:var(--link)}}
nav .group{{margin:16px 0 4px;color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.05em}}
main{{margin-left:300px;padding:24px 40px;max-width:1100px}}.page{{padding:24px 0 48px;border-bottom:1px solid var(--line)}}
.path{{font:12px ui-monospace,monospace;color:var(--mute);margin:0}}.desc{{color:var(--mute);font-size:14px}}.desc span{{font-weight:600}}
a{{color:var(--link)}}img{{max-width:100%;border:1px solid var(--line);border-radius:8px}}figure{{margin:16px 0}}figcaption{{color:var(--mute);font-size:14px;text-align:center}}
pre{{background:var(--side);padding:12px;border-radius:8px;overflow:auto}}code{{font-size:14px}}table{{border-collapse:collapse}}td,th{{border:1px solid var(--line);padding:6px 10px}}
.callout{{border-left:4px solid #0891b2;background:rgba(8,145,178,.08);padding:4px 16px;border-radius:6px;margin:16px 0}}
.callout.success{{border-color:#16a34a;background:rgba(22,163,74,.08)}}.callout.warning{{border-color:#d97706;background:rgba(217,119,6,.1)}}.callout.danger{{border-color:#dc2626;background:rgba(220,38,38,.08)}}
.co-title,.step-title,.tab-title{{font-weight:600}}.step{{border-left:2px solid var(--line);padding-left:16px;margin:12px 0}}
@media (max-width:800px){{nav{{position:static;width:auto;border-right:0}}main{{margin:0;padding:16px}}}}
</style></head><body><nav><p style="font-weight:700;font-size:15px;margin:0">{html.escape(a.title)}</p>{"".join(nav_html)}</nav>
<main>{"".join(sections)}</main></body></html>'''
    with open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(doc)
    print(f'wrote {os.path.join(a.out, "index.html")}: {len(pages)} page(s), {len(copied)} image(s)')


if __name__ == '__main__':
    main()
