#!/usr/bin/env python3
"""Check help-center pages for broken links, missing images, missing alt text,
orphaned images and table-of-contents problems.

Usage:
  python check_docs.py DOCS_ROOT [--toc SUMMARY.md|docs.json|mint.json]
                       [--pages a.md b.md ...] [--since GIT_REF]
                       [--static DIR] [--external]

--pages   only check these pages (default: every .md/.mdx under DOCS_ROOT)
--since   only check pages and images added/changed since GIT_REF (plus staged/untracked)
--static  folder that root-relative paths like /images/x.png resolve against
          (Docusaurus: static/; Mintlify: the docs root). Default: DOCS_ROOT
--toc     GitBook SUMMARY.md, or Mintlify docs.json / mint.json
--external  also request every http(s) link (slow; some sites block bots with 403)

Exit code is 1 when errors were found. Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PAGE_EXT = ('.md', '.mdx')
IMG_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')
MD_LINK = re.compile(r'(!?)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
HTML_SRC = re.compile(r'<(img|video|source|a)\b([^>]*)>', re.I)
ATTR = re.compile(r'(src|href|alt)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|{["\']([^"\']*)["\']})', re.I)
SKIP = ('http://', 'https://', 'mailto:', 'tel:', '#', 'data:', 'javascript:')


def git_changed(root, ref):
    def run(*args):
        r = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True)
        return r.stdout.splitlines() if r.returncode == 0 else []
    top = (run('rev-parse', '--show-toplevel') or [root])[0]
    names = run('diff', '--name-only', '--diff-filter=AMR', ref) + run('diff', '--name-only', '--cached', '--diff-filter=AMR') + run('ls-files', '--others', '--exclude-standard')
    rel_prefix = os.path.relpath(os.path.abspath(root), top).replace('\\', '/')
    out = set()
    for n in names:
        p = os.path.normpath(os.path.join(top, n)) if not os.path.isabs(n) else n
        if os.path.exists(p):
            out.add(os.path.abspath(p))
    return out


def all_files(root, exts):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {'.git', 'node_modules', '.next', 'build', 'dist', '.docusaurus'}]
        for fn in fns:
            if fn.lower().endswith(exts):
                yield os.path.abspath(os.path.join(dp, fn))


def refs_in(page):
    """Yield (line, kind, target, alt) for every link/image reference in a page."""
    in_fence = False
    with open(page, encoding='utf-8', errors='replace') as fh:
        for n, line in enumerate(fh, 1):
            if line.lstrip().startswith(('```', '~~~')):
                in_fence = not in_fence
            if in_fence:
                continue
            for bang, text, target in MD_LINK.findall(line):
                yield n, 'image' if bang else 'link', target, text if bang else None
            for tag, attrs in HTML_SRC.findall(line):
                a = {m[0].lower(): m[1] or m[2] or m[3] for m in ATTR.findall(attrs)}
                if tag.lower() == 'a' and 'href' in a:
                    yield n, 'link', a['href'], None
                elif 'src' in a:
                    yield n, 'image' if tag.lower() == 'img' else 'media', a['src'], a.get('alt', '') if tag.lower() == 'img' else None


def resolve(root, static, page, target):
    t = target.split('#')[0].split('?')[0]
    if not t:
        return page
    t = urllib.request.url2pathname(t) if '%' in t else t
    bases = [static, root] if t.startswith('/') else [os.path.dirname(page)]
    for base in bases:
        p = os.path.normpath(os.path.join(base, t.lstrip('/')))
        for cand in (p, p + '.md', p + '.mdx', os.path.join(p, 'README.md'), os.path.join(p, 'index.md'), os.path.join(p, 'index.mdx')):
            if os.path.isfile(cand):
                return os.path.abspath(cand)
    return None


def h1_of(page):
    with open(page, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.startswith('# '):
                return line[2:].strip()
            m = re.match(r'^title:\s*["\']?(.+?)["\']?\s*$', line)
            if m:
                return m.group(1)
    return None


def toc_entries(root, toc):
    """Return [(title_or_None, abs_path_or_None, raw)]."""
    path = os.path.join(root, toc) if not os.path.isabs(toc) else toc
    out = []
    if toc.lower().endswith('.md'):
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                m = re.match(r'^\s*[*-]\s+\[([^\]]+)\]\(([^)]+)\)', line)
                if m:
                    p = os.path.normpath(os.path.join(os.path.dirname(path), m.group(2).split('#')[0]))
                    out.append((m.group(1), os.path.abspath(p) if os.path.isfile(p) else None, m.group(2)))
    else:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == 'pages' and isinstance(v, list):
                        for item in v:
                            if isinstance(item, str):
                                hit = next((os.path.abspath(os.path.join(root, item + e)) for e in PAGE_EXT if os.path.isfile(os.path.join(root, item + e))), None)
                                out.append((None, hit, item))
                            else:
                                walk(item)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(data.get('navigation', data))
    return out


def check_url(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (docs link check)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        return url, e.code
    except Exception as e:  # noqa: BLE001
        return url, str(e)[:80]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root')
    ap.add_argument('--toc')
    ap.add_argument('--pages', nargs='*')
    ap.add_argument('--since')
    ap.add_argument('--static')
    ap.add_argument('--external', action='store_true')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    static = os.path.abspath(a.static or root)

    every_page = list(all_files(root, PAGE_EXT))
    changed = git_changed(root, a.since) if a.since else None
    if a.pages:
        pages = [os.path.abspath(p) for p in a.pages]
    elif changed is not None:
        pages = [p for p in every_page if p in changed]
    else:
        pages = every_page
    toc_name = os.path.basename(a.toc).lower() if a.toc else ''
    pages = [p for p in pages if os.path.basename(p).lower() != toc_name]

    errors, warnings, external = [], [], set()
    referenced = set()
    for page in every_page:
        for n, kind, target, alt in refs_in(page):
            if target.startswith(('http://', 'https://')):
                if page in pages:
                    external.add(target)
                continue
            if target.startswith(SKIP):
                continue
            hit = resolve(root, static, page, target)
            if hit:
                referenced.add(hit)
            if page not in pages:
                continue
            rel = os.path.relpath(page, root)
            if not hit:
                errors.append(f'{rel}:{n}: {kind} target not found: {target}')
            if kind == 'image' and not (alt or '').strip():
                warnings.append(f'{rel}:{n}: image has no alt text: {target}')

    # orphaned images (only new/changed ones when --since is used)
    imgs = [p for p in all_files(root, IMG_EXT) if changed is None or p in changed]
    for img in imgs:
        if img not in referenced:
            (warnings if changed is None else errors).append(f'orphaned image (not used by any page): {os.path.relpath(img, root)}')

    if a.toc:
        entries = toc_entries(root, a.toc)
        seen = {}
        for title, p, raw in entries:
            if p is None:
                errors.append(f'TOC entry points to a missing page: {raw}')
                continue
            seen[p] = seen.get(p, 0) + 1
            h1 = h1_of(p)
            if title and h1 and title.strip() != h1.strip():
                warnings.append(f'TOC title differs from page title: "{title}" vs "{h1}" ({raw})')
        for p in pages:
            if seen.get(p, 0) == 0:
                errors.append(f'page missing from TOC: {os.path.relpath(p, root)}')
            elif seen[p] > 1:
                errors.append(f'page listed {seen[p]} times in TOC: {os.path.relpath(p, root)}')

    if a.external and external:
        with ThreadPoolExecutor(8) as ex:
            for url, status in ex.map(check_url, sorted(external)):
                if not (isinstance(status, int) and status < 400):
                    (warnings if status in (401, 403, 429) else errors).append(f'external link {status}: {url}')

    print(f'Checked {len(pages)} page(s), {len(imgs)} image(s)' + (f', {len(external)} external link(s)' if a.external else ''))
    for e in errors:
        print('ERROR  ', e)
    for w in warnings:
        print('WARN   ', w)
    if not errors and not warnings:
        print('All good.')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
