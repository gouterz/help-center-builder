#!/usr/bin/env python3
"""Scan help-center pages for things that shouldn't be public, and images for hidden metadata.

Usage:
  python privacy_scan.py DOCS_DIR_OR_FILES... [--deny terms.txt] [--allow terms.txt]
                         [--allow-domain example.com ...] [--images] [--strip] [--json]

--deny   one term per line (case-insensitive); prefix a line with re: for a regex.
         Put internal service/database/host/vendor/staff/customer names here.
         Keep this file OUTSIDE the docs repo.
--allow  terms that are fine to publish (e.g. your public domains); suppresses hits containing them.
--images report PNG text/time chunks, JPEG EXIF/XMP/comments, SVG editor metadata.
--strip  remove that metadata from PNG and JPEG files in place.

Every hit needs a human (or Claude) look: the scan finds candidates, it doesn't decide.
Exit code is 1 when anything was found. Standard library only.
"""
import argparse
import json
import os
import re
import sys

TEXT_EXT = {'.md', '.mdx', '.markdown', '.txt', '.html', '.htm', '.json', '.yaml', '.yml'}
IMG_EXT = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}

PATTERNS = [
    ('secret', re.compile(r'\b(?:sk|pk|rk)_(?:live|test)_[0-9A-Za-z]{8,}|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[0-9A-Za-z]{20,}|\bgithub_pat_\w{20,}|\bglpat-[\w-]{16,}|\bxox[abprs]-[\w-]{10,}|\bAIza[\w-]{35}\b|\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('secret', re.compile(r'(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*["\']?[^\s"\'<>]{6,}')),
    ('id', re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')),
    ('id', re.compile(r'\b[0-9a-f]{24,}\b')),
    ('host', re.compile(r'(?i)\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?|\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b')),
    ('host', re.compile(r'(?i)\b[\w-]*(?:staging|stage|stg|preprod|uat|qa|sandbox|internal|intranet|admin|dev)[\w-]*\.[\w.-]+\.[a-z]{2,}\b|\b[\w.-]+\.(?:internal|local|lan|corp)\b')),
    ('infra', re.compile(r'(?i)\bs3://|\barn:aws:|[\w.-]+\.amazonaws\.com|[\w.-]+\.cloudfront\.net|[\w.-]+\.execute-api\.|[\w.-]+\.firebaseio\.com|[\w.-]+\.herokuapp\.com|[\w.-]+\.(?:vercel|netlify)\.app|[\w.-]+\.supabase\.co|[\w.-]+\.azurewebsites\.net|[\w.-]+\.run\.app|(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis|amqp)://')),
    ('path', re.compile(r'(?i)[A-Z]:\\Users\\[^\\\s]+|/(?:Users|home)/[\w.-]+/|\b(?:src|lib|app|server|backend|node_modules)/[\w./-]+|\b[\w-]+/[\w./-]*\.(?:js|jsx|ts|tsx|py|rb|go|java|php|cs|env)\b')),
    ('code', re.compile(r'\bprocess\.env\b|\brequire\(|\bconsole\.log\b|\bimport\s+[\w{}, ]+\s+from\b|\bSELECT\s+.+\s+FROM\b|\b(?:req|res|db)\.\w+')),
    ('todo', re.compile(r'\b(?:TODO|FIXME|XXX|TBD)\b|lorem ipsum', re.I)),
]
EMAIL = re.compile(r'\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)\b')
BACKTICK = re.compile(r'`([^`\n]+)`')
IDENT = re.compile(r'^[a-z]+(?:_[a-z0-9]+)+$|^[a-z]+[A-Z]\w*$|^\w+(?:\.\w+){2,}$')


def load_terms(path):
    if not path:
        return []
    out = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            out.append(re.compile(line[3:], re.I) if line.startswith('re:') else re.compile(r'(?<!\w)' + re.escape(line) + r'(?!\w)', re.I))
    return out


def iter_files(paths, exts):
    for p in paths:
        if os.path.isfile(p):
            if os.path.splitext(p)[1].lower() in exts:
                yield p
            continue
        for dp, dns, fns in os.walk(p):
            dns[:] = [d for d in dns if d not in {'.git', 'node_modules', '.next', 'build', 'dist'}]
            for fn in fns:
                if os.path.splitext(fn)[1].lower() in exts:
                    yield os.path.join(dp, fn)


def scan_text(path, deny, allow, allow_domains):
    hits = []
    in_fence = False
    with open(path, encoding='utf-8', errors='replace') as fh:
        for n, line in enumerate(fh, 1):
            if line.lstrip().startswith(('```', '~~~')):
                if not in_fence:
                    hits.append((n, 'code-block', 'fenced code block: check every name in it is customer-facing'))
                in_fence = not in_fence
            found = []
            for cat, rx in PATTERNS:
                if in_fence and cat in ('code', 'todo'):
                    continue
                found += [(cat, m.group(0)) for m in rx.finditer(line)]
            for m in EMAIL.finditer(line):
                dom = m.group(1).lower()
                if not any(dom == d or dom.endswith('.' + d) for d in allow_domains):
                    found.append(('email', m.group(0)))
            if not in_fence:
                found += [('identifier', m.group(1)) for m in BACKTICK.finditer(line) if IDENT.match(m.group(1).strip())]
            found += [('deny', m.group(0)) for rx in deny for m in rx.finditer(line)]
            for cat, text in found:
                if any(a.search(text) for a in allow):
                    continue
                hits.append((n, cat, text.strip()[:120]))
    return hits


# ---- image metadata -------------------------------------------------------
PNG_SIG = b'\x89PNG\r\n\x1a\n'
PNG_DROP = {b'tEXt', b'iTXt', b'zTXt', b'eXIf', b'tIME'}


def png_meta(data, strip):
    found, out, i = [], [PNG_SIG], 8
    while i < len(data):
        ln = int.from_bytes(data[i:i + 4], 'big')
        typ = data[i + 4:i + 8]
        chunk = data[i:i + 12 + ln]
        if typ in PNG_DROP:
            body = data[i + 8:i + 8 + ln]
            found.append(f'{typ.decode()} chunk: {body[:60]!r}')
        else:
            out.append(chunk)
        i += 12 + ln
        if typ == b'IEND':
            break
    return found, (b''.join(out) if strip and found else None)


def jpeg_meta(data, strip):
    found, out, i = [], [b'\xff\xd8'], 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            return found + ['unparseable JPEG structure'], None
        while data[i + 1] == 0xFF:
            i += 1
        m = data[i + 1]
        if m == 0xDA:  # start of scan: copy the rest untouched
            out.append(data[i:])
            break
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            out.append(data[i:i + 2])
            i += 2
            continue
        ln = int.from_bytes(data[i + 2:i + 4], 'big')
        seg = data[i:i + 2 + ln]
        if m in (0xE1, 0xED, 0xFE):  # APP1 (EXIF/XMP), APP13 (IPTC), COM
            found.append({0xE1: 'EXIF/XMP (APP1)', 0xED: 'IPTC (APP13)', 0xFE: 'comment'}[m] + f': {seg[4:40]!r}')
        else:
            out.append(seg)
        i += 2 + ln
    return found, (b''.join(out) if strip and found else None)


def svg_meta(text):
    rx = re.compile(r'<metadata|sodipodi:docname="[^"]*"|inkscape:export-filename="[^"]*"|<dc:creator|[A-Z]:\\\\?Users|/Users/[\w.-]+|/home/[\w.-]+', re.I)
    return [m.group(0)[:80] for m in rx.finditer(text)]


def scan_image(path, strip):
    with open(path, 'rb') as fh:
        data = fh.read()
    ext = os.path.splitext(path)[1].lower()
    new = None
    if data.startswith(PNG_SIG):
        found, new = png_meta(data, strip)
    elif data[:2] == b'\xff\xd8':
        found, new = jpeg_meta(data, strip)
    elif ext == '.svg':
        found = svg_meta(data.decode('utf-8', 'replace'))
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        found = [f'{c} chunk (re-export without metadata)' for c in ('EXIF', 'XMP ') if c.encode() in data]
    else:
        found = []
    if new is not None:
        with open(path, 'wb') as fh:
            fh.write(new)
        found = [f + '  [stripped]' for f in found]
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--deny')
    ap.add_argument('--allow')
    ap.add_argument('--allow-domain', action='append', default=[])
    ap.add_argument('--images', action='store_true')
    ap.add_argument('--strip', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    deny, allow = load_terms(a.deny), load_terms(a.allow)
    allow_domains = [d.lower() for d in a.allow_domain] + ['example.com', 'example.org', 'example.net']
    report = {}
    for p in iter_files(a.paths, TEXT_EXT):
        hits = scan_text(p, deny, allow, allow_domains)
        if hits:
            report[p] = [{'line': n, 'type': c, 'match': t} for n, c, t in hits]
    if a.images or a.strip:
        for p in iter_files(a.paths, IMG_EXT):
            found = scan_image(p, a.strip)
            if found:
                report[p] = [{'line': 0, 'type': 'image-metadata', 'match': f} for f in found]

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        for p, hits in report.items():
            print(p)
            for h in hits:
                loc = f"  line {h['line']:>4}" if h['line'] else '          '
                print(f"{loc}  [{h['type']}] {h['match']}")
        total = sum(len(h) for h in report.values())
        print(f'\n{total} item(s) to review in {len(report)} file(s).' if total else 'Nothing found.')
    sys.exit(1 if report else 0)


if __name__ == '__main__':
    main()
