#!/usr/bin/env python3
"""Blur or fill regions of a screenshot you've already captured.

Prefer fixing things before capture (demo data, anno.swapText / anno.mask / anno.blur).
Use this for images that already exist.

Usage:
  python redact.py IMAGE --originals DIR [--blur x0,y0,x1,y1 ...] [--circle cx,cy,r ...]
                   [--fill x0,y0,x1,y1 ...] [--color "#CBD5E1"] [--radius 10]
                   [--scale S] [--origin ox,oy] [--out PATH]

Coordinates are image pixels. If you measured them in the browser with anno.rect()
(CSS px), pass --scale (image width / viewport width at capture time) and, for a region
capture, --origin (the CSS px top-left of the captured region).

The first run copies the untouched image into --originals; every later run starts from
that copy, so you can adjust the boxes and re-run without blurring twice. Keep --originals
OUTSIDE the docs repo and never commit it.

Use --fill (solid) for secrets such as keys, tokens and IDs: blurred text can sometimes be
recovered. Blur is fine for incidental content like faces or someone's text.
Needs Pillow: pip install pillow
"""
import argparse
import os
import shutil

from PIL import Image, ImageDraw, ImageFilter


def nums(s):
    return [float(v) for v in s.split(',')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('--originals', required=True)
    ap.add_argument('--blur', action='append', default=[])
    ap.add_argument('--circle', action='append', default=[])
    ap.add_argument('--fill', action='append', default=[])
    ap.add_argument('--color', default='#CBD5E1')
    ap.add_argument('--radius', type=float, default=10)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--origin', default='0,0')
    ap.add_argument('--out')
    a = ap.parse_args()

    os.makedirs(a.originals, exist_ok=True)
    backup = os.path.join(a.originals, os.path.basename(a.image))
    if not os.path.exists(backup):
        shutil.copy2(a.image, backup)
    img = Image.open(backup).convert('RGB')
    ox, oy = nums(a.origin)

    def px(vals):
        # x/y pairs go through origin + scale; a trailing radius only scales
        out = []
        for i, v in enumerate(vals):
            if len(vals) == 3 and i == 2:
                out.append(round(v * a.scale))
            else:
                out.append(round((v - (ox if i % 2 == 0 else oy)) * a.scale))
        return out

    def blurred(box):
        region = img.crop(box)
        for _ in range(3):
            region = region.filter(ImageFilter.GaussianBlur(a.radius))
        return region

    for b in a.blur:
        box = tuple(px(nums(b)))
        img.paste(blurred(box), box[:2])
    for c in a.circle:
        cx, cy, r = px(nums(c))
        box = (cx - r, cy - r, cx + r, cy + r)
        mask = Image.new('L', (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        img.paste(blurred(box), box[:2], mask)
    draw = ImageDraw.Draw(img)
    for f in a.fill:
        draw.rectangle(tuple(px(nums(f))), fill=a.color)

    out = a.out or a.image
    img.save(out, optimize=True)  # Pillow writes no text/EXIF chunks unless asked
    print(f'saved {out} (original kept at {backup})')


if __name__ == '__main__':
    main()
