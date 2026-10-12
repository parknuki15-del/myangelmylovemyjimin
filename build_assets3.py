#!/usr/bin/env python3
"""v3 素材处理：
1. 4 张贴纸拼图 -> 拆成独立贴纸零件（透明 PNG）
2. 5 张拍立得相框 -> 抠掉中间窗口（透明），作为照片框架
3. 专辑封面修正：FACE=WechatIMG2384, MUSE=2221(logo), 磁带=2222；照片条剔除这三张
4. 世界地图 + 城市坐标 -> data.js
"""
from PIL import Image
from collections import deque
import os, sys, json, shutil

SRC = "/Users/whitekunckles/Desktop/朴智旻造型"
OUT = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
sys.setrecursionlimit(10000)

# ---------------- 贴纸切割 ----------------
def bg_mask_remove(im, thresh=232):
    """从四边泛洪去白底，返回 mask(255=保留)"""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    keep = [[True] * w for _ in range(h)]
    q = deque()
    def seed(x, y):
        if not keep[y][x]: return
        r, g, b = px[x, y]
        if r >= thresh and g >= thresh and b >= thresh:
            keep[y][x] = False; q.append((x, y))
    for x in range(w): seed(x, 0); seed(x, h - 1)
    for y in range(h): seed(0, y); seed(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and keep[ny][nx]:
                r, g, b = px[nx, ny]
                if r >= thresh and g >= thresh and b >= thresh:
                    keep[ny][nx] = False; q.append((nx, ny))
    return keep

def components(keep, min_area=2500, step=1):
    """连通域标记，返回 [(bbox, mask小图)]"""
    h = len(keep); w = len(keep[0])
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y0 in range(0, h, step):
        for x0 in range(0, w, step):
            if not keep[y0][x0] or seen[y0][x0]:
                continue
            q = deque([(x0, y0)]); seen[y0][x0] = True
            minx = maxx = x0; miny = maxy = y0; area = 0
            pix = []
            while q:
                x, y = q.popleft(); area += 1; pix.append((x, y))
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and keep[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True; q.append((nx, ny))
            if area >= min_area:
                comps.append(((minx, miny, maxx, maxy), area, pix))
    return comps

sticker_dir = os.path.join(OUT, "st")
if os.path.isdir(sticker_dir): shutil.rmtree(sticker_dir)
os.makedirs(sticker_dir, exist_ok=True)

sheet_files = sorted(f for f in os.listdir(os.path.join(SRC, "素材")) if f.lower().endswith(".jpg"))
all_stickers = []
for si, fn in enumerate(sheet_files, 1):
    im = Image.open(os.path.join(SRC, "素材", fn)).convert("RGBA")
    keep = bg_mask_remove(im)
    comps = components(keep, min_area=2200)
    comps.sort(key=lambda c: -c[1])
    rgba = im.load()
    for ci, (bbox, area, pix) in enumerate(comps[:40], 1):
        l, t, r, b = bbox
        pad = 6
        l = max(0, l - pad); t = max(0, t - pad)
        r = min(im.width - 1, r + pad); b = min(im.height - 1, b + pad)
        cw, ch = r - l + 1, b - t + 1
        crop = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cp = crop.load()
        for (x, y) in pix:
            if l <= x <= r and t <= y <= b:
                cp[x - l, y - t] = rgba[x, y]
        name = f"st{si:02d}_{ci:03d}.png"
        crop.save(os.path.join(sticker_dir, name), optimize=True)
        all_stickers.append({"img": f"assets/st/{name}", "w": cw, "h": ch, "area": area})
    print(f"sheet {fn}: {len(comps)} components kept")

# ---------------- 拍立得相框 ----------------
frame_dir = os.path.join(OUT, "frames")
if os.path.isdir(frame_dir): shutil.rmtree(frame_dir)
os.makedirs(frame_dir, exist_ok=True)
pola_dir = os.path.join(SRC, "拍立得")
frames = []
for i, fn in enumerate(sorted(f for f in os.listdir(pola_dir) if f.lower().endswith(".jpg")), 1):
    im = Image.open(os.path.join(pola_dir, fn)).convert("RGBA")
    w, h = im.size
    px = im.load()
    # 从中心泛洪：把窗口（纯白）变透明
    mask = [[False] * w for _ in range(h)]
    q = deque()
    cx, cy = w // 2, h // 2
    def white(x, y):
        r, g, b, a = px[x, y]
        return r >= 243 and g >= 243 and b >= 243
    if white(cx, cy):
        q.append((cx, cy)); mask[cy][cx] = True
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not mask[ny][nx] and white(nx, ny):
                mask[ny][nx] = True; q.append((nx, ny))
    hole = sum(1 for row in mask for v in row if v)
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 0)
    # 缩放至统一宽度 420
    sc = 420 / w
    im = im.resize((420, round(h * sc)), Image.LANCZOS)
    out = f"frame{i:02d}.png"
    im.save(os.path.join(frame_dir, out), optimize=True)
    frames.append({"img": f"assets/frames/{out}", "hole": hole})
    print(f"frame {fn}: hole {hole}px -> {out}")

# ---------------- 专辑封面 + 照片条（剔除封面图） ----------------
def resize_save(src_path, dst_path, maxw, q=88):
    im = Image.open(src_path).convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    im.save(dst_path, quality=q)

resize_save(os.path.join(SRC, "专辑FACE/WechatIMG2384.jpg"), os.path.join(OUT, "cover-face.jpg"), 760)
resize_save(os.path.join(SRC, "专辑MUSE/22211791617459_.pic_hd.jpg"), os.path.join(OUT, "cover-muse.jpg"), 760)
resize_save(os.path.join(SRC, "专辑MUSE/22221791617459_.pic_hd.jpg"), os.path.join(OUT, "cover-muse-tape.jpg"), 900)

COVERS = {"WechatIMG2384.jpg", "22211791617459_.pic_hd.jpg", "22221791617459_.pic_hd.jpg"}

def rebuild_photos(sub, out_sub, maxw, q=84):
    d = os.path.join(SRC, sub)
    dst = os.path.join(OUT, out_sub)
    if os.path.isdir(dst): shutil.rmtree(dst)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith((".jpg", ".jpeg")) or f in COVERS:
            continue
        n += 1
        resize_save(os.path.join(d, f), os.path.join(dst, f"{n:03d}.jpg"), maxw, q)
    return n

counts = {
    "wall": len([f for f in os.listdir(os.path.join(OUT, "wall")) if f.endswith('.jpg')]),
    "face": rebuild_photos("专辑FACE", "face", 900),
    "muse": rebuild_photos("专辑MUSE", "muse", 900),
    "wvs": len([f for f in os.listdir(os.path.join(OUT, "wvs")) if f.endswith('.jpg')]),
    "stickers": len(all_stickers),
    "frames": len(frames),
}
print("counts:", counts)

# ---------------- 城市坐标 ----------------
GEO = {
    "GOYANG": (37.66, 126.83), "JAPAN": (35.68, 139.69), "EL PASO": (31.76, -106.49),
    "MEXICO CITY": (19.43, -99.13), "LAS VEGAS": (36.17, -115.14), "LOS ANGELES": (34.05, -118.24),
    "FOXBOROUGH": (42.09, -71.27), "TORONTO": (43.65, -79.38), "ARLINGTON": (32.74, -97.11),
    "EAST RUTHERFORD": (40.83, -74.10), "CHICAGO": (41.88, -87.63), "MUNICH": (48.14, 11.58),
    "BOGOTA": (4.71, -74.07), "LIMA": (-12.05, -77.04), "BALTIMORE": (39.29, -76.61),
    "iHEART FEST": (34.05, -118.24),
}
data_path = os.path.join(OUT, "data.js")
looks = json.loads(open(data_path, encoding="utf-8").read().split("=", 1)[1].strip().rstrip(";"))["looks"]

city_index = {}
for idx, lk in enumerate(looks):
    c = lk["city"]
    city_index.setdefault(c, {"city": c, "looks": [], "dates": set()})
    city_index[c]["looks"].append(idx)
    city_index[c]["dates"].add(lk["date"])
cities = []
for c, info in city_index.items():
    lat, lon = GEO.get(c, (0, 0))
    cities.append({
        "city": c,
        "count": len(info["looks"]),
        "first": min(info["looks"]),
        "dates": sorted(info["dates"]),
        "x": round((lon + 180) / 360, 4),
        "y": round((90 - lat) / 180, 4),
    })
cities.sort(key=lambda c: c["first"])

data = {"looks": looks, "counts": counts, "stickers": all_stickers, "frames": frames, "cities": cities}
with open(data_path, "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
print("cities:", len(cities), "stickers:", len(all_stickers))
print("DONE")
