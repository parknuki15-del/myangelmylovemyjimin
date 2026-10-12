#!/usr/bin/env python3
"""v5：为巡演地图生成「真实大圆弧」路线。
参考图的路线是沿地图边缘跨洋的弧线（像板块缝合），所以：
  - 地理距离 > 3000km 的段（跨洋）用大圆球面插值，采样后投影 -> 自然向北拱起的弧
  - 城市之间的陆路段用直线
跨 180° 经线时按地图边缘切开，避免横穿整张图的假线。
结果写入 data.js 的 legs:[{d, color, kind}]
"""
import json, math, os

BASE = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
data_path = os.path.join(BASE, "data.js")

# build_assets6.py 拟合出的投影（x 纯经度 / y 墨卡托）
A, C = 2.81040, 474.371
M, D = -159.94609, 462.135
def merc(lat):
    la = max(-85.0, min(85.0, lat)) * math.pi / 180.0
    return math.log(math.tan(math.pi / 4 + la / 2))
def proj(lon, lat):
    return (A * lon + C, M * merc(lat) + D)

def vec(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))

def to_lonlat(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    x, y, z = (c / n for c in v)
    return (math.degrees(math.atan2(y, x)), math.degrees(math.asin(max(-1, min(1, z)))))

def haversine(p1, p2):
    lon1, lat1 = map(math.radians, p1); lon2, lat2 = map(math.radians, p2)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))

def gc(p1, p2, n=32):
    """大圆球面插值，返回经纬度采样点"""
    v1, v2 = vec(*p1), vec(*p2)
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(v1, v2))))
    om = math.acos(dot)
    if om < 1e-6:
        return [p1, p2]
    s = math.sin(om)
    out = []
    for i in range(n + 1):
        t = i / n
        a, b = math.sin((1 - t) * om) / s, math.sin(t * om) / s
        out.append(to_lonlat(tuple(a * x + b * y for x, y in zip(v1, v2))))
    return out

def split(pts):
    """投影 + 按地图边缘切开（跨经线）"""
    out, cur = [], []
    prev = None
    for lon, lat in pts:
        x, y = proj(lon, lat)
        if prev is not None and abs(x - prev[0]) > 505:
            if len(cur) > 1:
                out.append(cur)
            cur = []
        cur.append((x, y))
        prev = (x, y)
    if len(cur) > 1:
        out.append(cur)
    return out

def d_of(seg):
    s = "M%.1f,%.1f" % seg[0]
    for p in seg[1:]:
        s += " L%.1f,%.1f" % p
    return s

PALETTE = ["#e8534a", "#ef7f5f", "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f",
           "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f", "#f0a24b", "#e8534a",
           "#d94f6a", "#ef7f5f", "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f",
           "#f0a24b", "#e8534a", "#d94f6a"]

# 按时间的城市顺序（和 data.js 的 cities 顺序一致）
CITY_GEO = {
    "GOYANG": (126.83, 37.66), "TOKYO": (139.69, 35.68), "EL PASO": (-106.49, 31.76),
    "MEXICO CITY": (-99.13, 19.43), "STANFORD": (-122.17, 37.43), "LAS VEGAS": (-115.14, 36.17),
    "MADRID": (-3.70, 40.42), "BRUSSELS": (4.35, 50.85), "LONDON": (-0.13, 51.51),
    "MUNICH": (11.58, 48.14), "PARIS": (2.35, 48.86), "WORLD CUP 2026": (-84.39, 33.75),
    "EAST RUTHERFORD": (-74.10, 40.83), "FOXBOROUGH": (-71.27, 42.09),
    "BALTIMORE": (-76.61, 39.29), "ARLINGTON": (-97.11, 32.74), "TORONTO": (-79.38, 43.65),
    "CHICAGO": (-87.63, 41.88), "LOS ANGELES": (-118.24, 34.05),
    "iHEART FEST": (-118.24, 34.05), "BOGOTA": (-74.07, 4.71), "LIMA": (-77.04, -12.05),
    # 2026 世界杯决赛 7/19 @ MetLife Stadium
    "WORLD CUP 2026": (-74.10, 40.83),
}

old = json.loads(open(data_path, encoding="utf-8").read().split("=", 1)[1].strip().rstrip(";"))
order = [c["city"] for c in old["cities"]]

legs = []
for i in range(len(order) - 1):
    c1, c2 = order[i], order[i + 1]
    p1, p2 = CITY_GEO[c1], CITY_GEO[c2]
    dist = haversine(p1, p2)
    if dist > 3000:
        segs = split(gc(p1, p2, 40))
        kind = "arc"
    else:
        segs = split([p1, p2])
        kind = "land"
    for s in segs:
        legs.append({"d": d_of(s), "color": PALETTE[i % len(PALETTE)], "kind": kind})
    print(f"{c1:16s} -> {c2:16s} {dist/1000:7.0f} km  {kind}  segs={len(segs)}")

old["legs"] = legs
with open(data_path, "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(old, ensure_ascii=False) + ";\n")
print("\nlegs:", len(legs), " 写回 data.js")
