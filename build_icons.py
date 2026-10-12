#!/usr/bin/env python3
"""生成板块插画图标：抠白底 -> 透明 PNG 220px"""
from PIL import Image
from collections import deque
import os

SRC = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/source-icons"
OUT = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets/icons"
os.makedirs(OUT, exist_ok=True)

def remove_white(im, thresh=238):
    rgb = im.convert("RGB"); w, h = rgb.size; px = rgb.load()
    keep = [[True]*w for _ in range(h)]
    q = deque()
    def seed(x, y):
        if not keep[y][x]: return
        r, g, b = px[x, y]
        if r >= thresh and g >= thresh and b >= thresh:
            keep[y][x] = False; q.append((x, y))
    for x in range(w): seed(x, 0); seed(x, h-1)
    for y in range(h): seed(0, y); seed(w-1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h and keep[ny][nx]:
                r, g, b = px[nx, ny]
                if r >= thresh and g >= thresh and b >= thresh:
                    keep[ny][nx] = False; q.append((nx, ny))
    out = im.convert("RGBA")
    mask = Image.new("L", (w, h), 255); mp = mask.load()
    for y in range(h):
        row = keep[y]
        for x in range(w):
            if not row[x]: mp[x, y] = 0
    out.putalpha(mask)
    return out

names = ["tour", "photos", "albums", "feed", "messages"]
files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".png"))
assert len(files) == 5, files
for name, fn in zip(names, files):
    im = remove_white(Image.open(os.path.join(SRC, fn)))
    bbox = im.getchannel("A").getbbox()
    im = im.crop(bbox)
    s = 220 / max(im.size)
    im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    im.save(os.path.join(OUT, f"ic-{name}.png"), optimize=True)
    print(f"ic-{name}.png  {im.size}  {os.path.getsize(os.path.join(OUT, f'ic-{name}.png'))//1024}KB")
print("DONE")
