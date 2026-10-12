#!/usr/bin/env python3
"""生日网站 v2 素材处理：
1. ARIRANG 巡演精灵图（root png + v4 + v5）：抠白底、去重、统一高 560 -> assets/looks/NNN.png
2. 照片素材压缩复制：wall / face / muse / wvs / stickers
3. 输出 assets/data.js 供页面动态构建
"""
from PIL import Image
from collections import deque
import os, re, json, hashlib

SRC = "/Users/whitekunckles/Desktop/朴智旻造型"
OUT = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
LOOKS_OUT = os.path.join(OUT, "looks")
os.makedirs(LOOKS_OUT, exist_ok=True)

def flood_remove_white(img, thresh=238):
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    alpha = [[255] * w for _ in range(h)]
    q = deque()
    def seed(x, y):
        if alpha[y][x] == 0: return
        r, g, b = px[x, y]
        if r >= thresh and g >= thresh and b >= thresh:
            alpha[y][x] = 0; q.append((x, y))
    for x in range(w): seed(x, 0); seed(x, h - 1)
    for y in range(h): seed(0, y); seed(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and alpha[ny][nx] == 255:
                r, g, b = px[nx, ny]
                if r >= thresh and g >= thresh and b >= thresh:
                    alpha[ny][nx] = 0; q.append((nx, ny))
    out = img.convert("RGBA")
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    for y in range(h):
        row = alpha[y]
        for x in range(w):
            if row[x] == 0: mp[x, y] = 0
    out.putalpha(mask)
    return out

def trim(im, pad=4):
    bbox = im.getchannel("A").getbbox()
    if not bbox: return im
    l, t, r, b = bbox
    return im.crop((max(0, l-pad), max(0, t-pad), min(im.width, r+pad), min(im.height, b+pad)))

CITIES = ["GOYANG", "JAPAN", "EL PASO", "MEXICO CITY", "LAS VEGAS", "LOS ANGELES",
          "FOXBOROUGH", "TORONTO", "ARLINGTON", "EAST RUTHERFORD", "CHICAGO",
          "MUNICH", "BOGOTA", "LIMA", "BALTIMORE", "IHEARTRADIO MUSIC FESTIVAL"]

def parse_label(fn):
    name = fn.upper().replace("-", "").replace("_", "").replace(" ", "")
    m = re.match(r"(\d{2})(\d{2})(\d{2})", name)
    date = f"{m.group(2)}.{m.group(3)}" if m else "?"
    city = "ARIRANG"
    for c in CITIES:
        if c.replace(" ", "") in name:
            city = "iHEART FEST" if "IHEART" in c else c
            break
    return date, city

# 收集全部精灵图
sprite_files = []
root_png = [f for f in os.listdir(SRC) if f.lower().endswith(".png")]
for f in root_png: sprite_files.append(os.path.join(SRC, f))
for sub in ["maple精灵图/v4", "maple精灵图/v5"]:
    d = os.path.join(SRC, sub)
    for f in os.listdir(d):
        if f.lower().endswith(".png"):
            sprite_files.append(os.path.join(d, f))
sprite_files.sort(key=lambda p: os.path.basename(p))

looks, seen = [], set()
idx = 0
for path in sprite_files:
    with open(path, "rb") as fh:
        md5 = hashlib.md5(fh.read()).hexdigest()
    if md5 in seen: continue
    seen.add(md5)
    im = flood_remove_white(Image.open(path))
    im = trim(im)
    s = 560 / im.height
    im = im.resize((round(im.width * s), 560), Image.LANCZOS)
    im = im.quantize(colors=192, method=Image.FASTOCTREE).convert("RGBA")
    idx += 1
    out_name = f"look{idx:03d}.png"
    im.save(os.path.join(LOOKS_OUT, out_name), optimize=True)
    date, city = parse_label(os.path.basename(path))
    looks.append({"img": f"assets/looks/{out_name}", "date": date, "city": city})

print(f"sprites: {len(sprite_files)} 原始 -> {len(looks)} 去重后")

def copy_jpgs(sub, out_sub, maxw, q=80):
    d = os.path.join(SRC, sub)
    dst = os.path.join(OUT, out_sub)
    os.makedirs(dst, exist_ok=True)
    fs = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".jpeg")))
    n = 0
    for f in fs:
        n += 1
        im = Image.open(os.path.join(d, f)).convert("RGB")
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        im.save(os.path.join(dst, f"{n:03d}.jpg"), quality=q)
    return n

counts = {
    "wall":  copy_jpgs("照片墙", "wall", 760),
    "face":  copy_jpgs("专辑FACE", "face", 900),
    "muse":  copy_jpgs("专辑MUSE", "muse", 900),
    "wvs":   copy_jpgs("wvs动态", "wvs", 640),
    "stickers": copy_jpgs("素材", "stickers", 800),
    "polaroid": copy_jpgs("拍立得", "polaroid", 800),
}
print("counts:", counts)

data = {"looks": looks, "counts": counts}
with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
print("data.js written")
