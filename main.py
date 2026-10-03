#!/usr/bin/env python3
"""Robust segment-based captcha OCR for localhost.cz.

Captcha = 4 slanted white digits on a green background (100x30 px).
Answer   = sum of the first two digits, so we must read the first two cells correctly.
Pipeline : white-pixel mask -> column projection -> split into 4 groups
           (valley splitting of merged groups) -> per-cell tesseract (h=40, psm 10/8/7).
"""
import sys, subprocess, os
import numpy as np
from PIL import Image, ImageOps

MASK_THR = 130

def load_mask(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    return (a[:, :, 0] > MASK_THR) & (a[:, :, 1] > MASK_THR) & (a[:, :, 2] > MASK_THR)

def col_groups(colsum, gap=0, minw=3):
    g, s, l = [], None, None
    for x, v in enumerate(colsum):
        if v > 0:
            if s is None: s = x
            l = x
        else:
            if s is not None and x - l > gap:
                g.append((s, l)); s = l = None
    if s is not None: g.append((s, l))
    # drop tiny noise groups
    g = [x for x in g if x[1] - x[0] + 1 >= minw]
    return g

def split_wide(colsum, groups, n=4):
    """Force exactly n groups: merge closest if too many, valley-split widest if too few."""
    while len(groups) > n:
        i = min(range(len(groups) - 1), key=lambda k: groups[k+1][0] - groups[k][1])
        groups = groups[:i] + [(groups[i][0], groups[i+1][1])] + groups[i+2:]
    while len(groups) < n:
        i = max(range(len(groups)), key=lambda k: groups[k][1] - groups[k][0])
        a, b = groups[i]
        if b - a < 2:
            break
        seg = colsum[a:b+1]
        # valley = min column strictly inside the group
        off = int(np.argmin(seg[1:-1])) + 1 if len(seg) > 2 else len(seg)//2
        mid = a + off
        groups = groups[:i] + [(a, mid-1), (mid, b)] + groups[i+1:]
    return groups

from collections import Counter

def _one(sub, h, psm, invert):
    w = max(8, int(round(h * sub.shape[1] / sub.shape[0])))
    img = Image.fromarray((sub.astype(np.uint8) * 255)).resize((w, h), Image.LANCZOS)
    if invert:
        img = ImageOps.invert(img)
    img = ImageOps.expand(img, border=15, fill=255 if invert else 0)
    img.save("/tmp/_capcell.png")
    out = subprocess.run(
        ["tesseract", "/tmp/_capcell.png", "stdout", "--psm", psm,
         "-c", "tessedit_char_whitelist=0123456789"],
        capture_output=True, text=True).stdout
    d = "".join(c for c in out if c.isdigit())
    return d[0] if d else None

def ocr_cell(sub):
    """Vote across preprocessing configs; return the majority digit."""
    votes = Counter()
    for h in (30, 35, 40, 45, 50, 70):
        for psm in ("7", "8", "10", "13"):
            for invert in (True, False):
                d = _one(sub, h, psm, invert)
                if d:
                    votes[d] += 1
    if not votes:
        return "?"
    return votes.most_common(1)[0][0]

def solve(path, debug=False):
    mask = load_mask(path)
    colsum = mask.sum(axis=0)
    groups = split_wide(colsum, col_groups(colsum), 4)
    digits = [ocr_cell(mask[:, a:b+1]) for (a, b) in groups[:4]]
    s = "".join(digits)
    first2 = [int(c) for c in s[:2] if c.isdigit()]
    total = sum(first2) if len(first2) == 2 else None
    if debug:
        print(f"  groups={groups} -> {s} sum={total}")
    return s, total

if __name__ == "__main__":
    paths = sys.argv[1:] or (["capx.png"] + [f"capS{i}.jpg" for i in range(1, 7)])
    truth = {"capx.png": "8422", "capS1.jpg": "2739", "capS2.jpg": "3972",
             "capS3.jpg": "3472", "capS4.jpg": "2444", "capS5.jpg": "2928", "capS6.jpg": "9377"}
    ok = 0; tot = 0
    for p in paths:
        if not os.path.exists(p): continue
        s, t = solve(p, debug=True)
        if p in truth:
            tf = int(truth[p][0]) + int(truth[p][1])
            good = (t == tf)
            ok += good; tot += 1
            print(f"{p}: ocr={s} sum={t} truth_sum={tf} {'OK' if good else 'WRONG'}")
    if tot: print(f"\nAccuracy(first-two-sum): {ok}/{tot}")