#!/usr/bin/env python3
"""构建生日网站资产：
1. 11 个转头帧抠图 -> 统一 300x450 -> 合成 7x3 大图集 turn-atlas.png
2. 5 套巡演造型抠图 -> 透明 PNG（高 640）
3. 2 张专辑封面 -> 512px JPG
"""
from PIL import Image, ImageOps
from collections import deque
import os

BASE = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18"
SRC = os.path.join(BASE, "oil-motion-hero/source")
OUT = os.path.join(BASE, "birthday-site/assets")
os.makedirs(OUT, exist_ok=True)

CELL_W, CELL_H = 300, 450

def flood_remove_white(img, thresh=238):
    """从四边泛洪填充移除白底，返回 RGBA。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    alpha = [[255] * w for _ in range(h)]
    q = deque()
    def seed(x, y):
        if alpha[y][x] == 0:
            return
        r, g, b = px[x, y]
        if r >= thresh and g >= thresh and b >= thresh:
            alpha[y][x] = 0
            q.append((x, y))
    for x in range(w):
        seed(x, 0); seed(x, h - 1)
    for y in range(h):
        seed(0, y); seed(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and alpha[ny][nx] == 255:
                r, g, b = px[nx, ny]
                if r >= thresh and g >= thresh and b >= thresh:
                    alpha[ny][nx] = 0
                    q.append((nx, ny))
    out = img.convert("RGBA")
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    for y in range(h):
        row = alpha[y]
        for x in range(w):
            if row[x] == 0:
                mp[x, y] = 0
    out.putalpha(mask)
    return out

def trim(im, pad=4):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(im.width, r + pad); b = min(im.height, b + pad)
    return im.crop((l, t, r, b))

def to_cell(path, white_bg=True):
    im = Image.open(path)
    if white_bg:
        im = flood_remove_white(im)
    else:
        im = im.convert("RGBA")
    im = trim(im)
    s = min(CELL_W / im.width, CELL_H / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                   Image.LANCZOS)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    cell.paste(im, ((CELL_W - im.width) // 2, CELL_H - im.height), im)
    return cell

T = os.path.join(SRC, "turn")
T2 = os.path.join(SRC, "turn2")
frames = {
    "L-profile":  f"{T}/Edit_the_reference_character_w_2026-10-09T01-13-14.png",
    "L-3q":       f"{T}/Edit_the_reference_character_w_2026-10-09T01-13-15.png",
    "L-slight":   f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-07-47.png",
    "FRONT":      f"{SRC}/character-reference.png",
    "R-slight":   f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-08-04.png",
    "R-3q":       f"{T}/Edit_the_reference_character_w_2026-10-09T01-14-51.png",
    "R-profile":  f"{T}/Edit_the_reference_character_w_2026-10-09T02-12-26.png",
    "L-3q-up":    f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-08-32.png",
    "L-3q-down":  f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-08-48.png",
    "R-3q-up":    f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-09-09.png",
    "R-3q-down":  f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-09-24.png",
    "FRONT-up":   f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-16-34.png",
    "FRONT-down": f"{T2}/Edit_this_chibi_pixel_art_char_2026-10-09T12-16-58.png",
}
cells = {k: to_cell(p) for k, p in frames.items()}

# 7 列 x 3 行（上/平/下）
grid = [
    ["L-3q-up",  "L-3q-up",  "L-3q-up",  "FRONT-up",   "R-3q-up", "R-3q-up", "R-3q-up"],
    ["L-profile","L-3q",     "L-slight", "FRONT",  "R-slight","R-3q",    "R-profile"],
    ["L-3q-down","L-3q-down","L-3q-down","FRONT-down", "R-3q-down","R-3q-down","R-3q-down"],
]
atlas = Image.new("RGBA", (CELL_W * 7, CELL_H * 3), (0, 0, 0, 0))
for r, row in enumerate(grid):
    for c, name in enumerate(row):
        atlas.paste(cells[name], (c * CELL_W, r * CELL_H))
atlas = atlas.quantize(colors=256, method=Image.FASTOCTREE).convert("RGBA")
atlas.save(os.path.join(OUT, "turn-atlas.png"), optimize=True)

# 巡演造型
looks = os.path.join(SRC, "looks")
names = ["ly-tour", "ptd", "butter", "face", "muse"]
files = sorted(os.listdir(looks))
for name, fn in zip(names, files):
    im = flood_remove_white(Image.open(os.path.join(looks, fn)))
    im = trim(im)
    s = 640 / im.height
    im = im.resize((round(im.width * s), 640), Image.LANCZOS)
    im = im.quantize(colors=192, method=Image.FASTOCTREE).convert("RGBA")
    im.save(os.path.join(OUT, f"look-{name}.png"), optimize=True)

# 专辑封面
albums = os.path.join(SRC, "albums")
afiles = sorted(os.listdir(albums))
for name, fn in zip(["face", "muse"], afiles):
    im = Image.open(os.path.join(albums, fn)).convert("RGB")
    im = ImageOps.fit(im, (512, 512), Image.LANCZOS)
    im.save(os.path.join(OUT, f"album-{name}.jpg"), quality=86)

for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print(f"{f:36s} {os.path.getsize(p)//1024} KB")
print("DONE")
