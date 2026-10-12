#!/usr/bin/env python3
"""v4：修正城市解析（补 STANFORD/LONDON/PARIS/MADRID/BRUSSELS 等），
用 SVG 国界 bbox 拟合等距投影变换，重算地图坐标 + 巡演路线顺序 -> data.js
"""
import os, re, json, hashlib
from collections import Counter

SRC = "/Users/whitekunckles/Desktop/朴智旻造型"
BASE = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
data_path = os.path.join(BASE, "data.js")

# ---------- 1. 重新解析文件名 ----------
files = []
for f in os.listdir(SRC):
    if f.lower().endswith(".png"): files.append(os.path.join(SRC, f))
for sub in ["maple精灵图/v4", "maple精灵图/v5"]:
    d = os.path.join(SRC, sub)
    for f in os.listdir(d):
        if f.lower().endswith(".png"): files.append(os.path.join(d, f))
files.sort(key=lambda p: os.path.basename(p))

CITY_FIX = {
    "GOYANG": "GOYANG", "JAPAN": "TOKYO", "ELPASO": "EL PASO", "MEXICOCITY": "MEXICO CITY",
    "STANFORD": "STANFORD", "LASVEGAS": "LAS VEGAS", "LOSANGELES": "LOS ANGELES",
    "EASTRUTHERFORD": "EAST RUTHERFORD", "FOXBOROUGH": "FOXBOROUGH", "TORONTO": "TORONTO",
    "ARLINGTON": "ARLINGTON", "CHICAGO": "CHICAGO", "MUNICH": "MUNICH", "BOGOTA": "BOGOTA",
    "LIMA": "LIMA", "BALTIMORE": "BALTIMORE", "PARIS": "PARIS", "LONDON": "LONDON",
    "BRUSSELS": "BRUSSELS", "MADRID": "MADRID",
}

def parse(fn):
    n = fn.upper().replace("-", "").replace("_", "").replace(" ", "").replace(".PNG", "")
    m = re.match(r"(\d{2})(\d{2})(\d{2})", n)
    date = f"{m.group(2)}.{m.group(3)}" if m else "?"
    mm = re.search(r"ARIRANG'?IN(.+)$", n)
    if mm:
        city = CITY_FIX.get(mm.group(1), mm.group(1).title())
    elif "IHEART" in n:
        city = "iHEART FEST"
    elif "FIFA" in n or "WORLDCUP" in n:
        city = "WORLD CUP 2026"
    else:
        city = "SPECIAL"
    return date, city

seen = set(); order = []
for p in files:
    h = hashlib.md5(open(p, "rb").read()).hexdigest()
    if h in seen: continue
    seen.add(h)
    date, city = parse(os.path.basename(p))
    order.append({"date": date, "city": city})

old = json.loads(open(data_path, encoding="utf-8").read().split("=", 1)[1].strip().rstrip(";"))
looks = old["looks"]
assert len(looks) == len(order), (len(looks), len(order))
for lk, o in zip(looks, order):
    lk["date"], lk["city"] = o["date"], o["city"]

# ---------- 2. 投影拟合（SVG 用户单位 1010x666） ----------
BBOX = {  # name: (bbox_cx, bbox_cy), 已知经纬度用国家几何中心
    "Belgium": ((487.37, 298.99), (4.6, 50.6)),
    "Netherlands": ((489.70, 291.37), (5.5, 52.2)),
    "Greece": ((542.08, 346.63), (22.0, 39.1)),
    "Egypt": ((561.30, 384.89), (30.0, 26.8)),
    "Sri Lanka": ((701.64, 440.87), (80.8, 7.8)),
    "South Korea": ((835.45, 355.27), (127.8, 36.3)),
    "Cuba": ((251.74, 401.41), (-79.5, 21.6)),
    "Ecuador": ((240.69, 467.86), (-78.2, -1.4)),
    "Italy": ((510.14, 333.16), (12.6, 42.8)),
    "Germany": ((504.19, 295.33), (10.4, 51.2)),
    "Spain": ((455.48, 354.72), (-3.7, 40.4)),
    "Thailand": ((759.78, 425.94), (101.0, 15.0)),
    "Vietnam": ((771.78, 417.42), (106.3, 16.0)),
    "India": ((707.15, 400.46), (79.0, 22.0)),
    "Australia": ((856.39, 568.75), (134.0, -25.0)),
    "South Africa": ((551.14, 569.03), (24.5, -29.5)),
    "Turkey": ((573.81, 344.45), (35.2, 39.0)),
    "Iran": ((625.51, 366.17), (53.7, 32.4)),
    "Mexico": ((187.09, 394.09), (-102.5, 23.6)),
    "Brazil": ((322.23, 505.63), (-51.0, -10.0)),
}

def fit(points):
    """最小二乘拟合 x=a*lon+b*lat+c, y=d*lon+e*lat+f"""
    import itertools
    n = len(points)
    # 正规方程（3 参数）
    def solve(rows, vals):
        A = [[0.0]*3 for _ in range(3)]; B = [0.0]*3
        for r, v in zip(rows, vals):
            for i in range(3):
                B[i] += r[i]*v
                for j in range(3):
                    A[i][j] += r[i]*r[j]
        # 高斯消元
        M = [A[i][:] + [B[i]] for i in range(3)]
        for i in range(3):
            p = max(range(i, 3), key=lambda k: abs(M[k][i])); M[i], M[p] = M[p], M[i]
            for k in range(i+1, 3):
                f = M[k][i]/M[i][i]
                for j in range(i, 4): M[k][j] -= f*M[i][j]
        x = [0.0]*3
        for i in (2, 1, 0):
            s = M[i][3] - sum(M[i][j]*x[j] for j in range(i+1, 3))
            x[i] = s/M[i][i]
        return x
    rows = [[lon, lat, 1.0] for (_, (lon, lat)) in points]
    cx = solve(rows, [px for ((px, py), _) in points])
    cy = solve(rows, [py for ((px, py), _) in points])
    return cx, cy

pts = list(BBOX.values())
cx, cy = fit(pts)
def predict(lon, lat):
    return (cx[0]*lon + cx[1]*lat + cx[2], cy[0]*lon + cy[1]*lat + cy[2])

# 残差检查 + 剔除离群
def resid(points):
    out = []
    for (px, py), (lon, lat) in points:
        X, Y = predict(lon, lat)
        out.append((((px-X)**2 + (py-Y)**2) ** 0.5, px, py, X, Y, lon, lat))
    return out
res = sorted(resid(pts), reverse=True)
print("最大残差(px):", [(round(r[0],1)) for r in res[:5]])
KEEP = [p for p in pts if p[0:2] and True]
if res and res[0][0] > 12:  # 剔除最差的
    bad = res[0]
    KEEP = [p for p in pts if not (p[0] == (bad[1], bad[2]))]
    cx, cy = fit(KEEP)
    print("剔除离群后重拟合")
print("变换: x = %.4f*lon + %.4f*lat + %.2f" % tuple(cx))
print("      y = %.4f*lon + %.4f*lat + %.2f" % tuple(cy))

CITY_GEO = {
    "GOYANG": (126.83, 37.66), "TOKYO": (139.69, 35.68), "EL PASO": (-106.49, 31.76),
    "MEXICO CITY": (-99.13, 19.43), "STANFORD": (-122.17, 37.43), "LAS VEGAS": (-115.14, 36.17),
    "LOS ANGELES": (-118.24, 34.05), "EAST RUTHERFORD": (-74.10, 40.83),
    "FOXBOROUGH": (-71.27, 42.09), "TORONTO": (-79.38, 43.65), "ARLINGTON": (-97.11, 32.74),
    "CHICAGO": (-87.63, 41.88), "MUNICH": (11.58, 48.14), "BOGOTA": (-74.07, 4.71),
    "LIMA": (-77.04, -12.05), "BALTIMORE": (-76.61, 39.29), "PARIS": (2.35, 48.86),
    "LONDON": (-0.13, 51.51), "BRUSSELS": (4.35, 50.85), "MADRID": (-3.70, 40.42),
    "iHEART FEST": (-118.24, 34.05), "WORLD CUP 2026": (-84.39, 33.75),
}

city_index = {}
for idx, lk in enumerate(looks):
    c = lk["city"]
    city_index.setdefault(c, {"city": c, "looks": [], "latlon": CITY_GEO.get(c, (0, 0))})
    city_index[c]["looks"].append(idx)

cities = []
for c, info in city_index.items():
    lon, lat = info["latlon"]
    X, Y = predict(lon, lat)
    cities.append({
        "city": c, "count": len(info["looks"]), "first": min(info["looks"]),
        "x": round(X / 1010, 5), "y": round(Y / 666, 5),
    })
cities.sort(key=lambda c: c["first"])
for c in cities:
    print(f"{c['city']:18s} n={c['count']:2d}  x={c['x']*100:6.2f}%  y={c['y']*100:6.2f}%")

# 路线（按首次出现顺序）+ 抽稀（同城只留一个点）
route = [{"x": c["x"], "y": c["y"], "city": c["city"]} for c in cities]

old["cities"] = cities
old["route"] = route
old["looks"] = looks
with open(data_path, "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(old, ensure_ascii=False) + ";\n")
print("城市数:", len(cities), " 写回 data.js")
