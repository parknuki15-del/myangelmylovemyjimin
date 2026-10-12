#!/usr/bin/env python3
"""v5：用 SVG 真实像素重心（204 国）重新拟合投影，修正城市坐标。
之前 v4 用的是「bbox 中心」，对韩国/日本这种半岛+群岛国家误差很大，
导致高阳、日本坐标偏。这里改用面积重心 + 迭代剔离群。"""
import json, os

BASE = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
data_path = os.path.join(BASE, "data.js")

# ---- SVG 面积重心（由浏览器 canvas 逐国光栅化求得） ----
SVG = {
    "South Korea": (833.04, 353.48), "Japan": (861.68, 348.25), "China": (766.89, 349.02),
    "Taiwan": (813.91, 394.28), "North Korea": (831.53, 339.55), "Russia": (757.89, 221.30),
    "United States": (137.58, 294.59), "Canada": (202.17, 200.57), "Mexico": (185.88, 392.70),
    "United Kingdom": (465.82, 280.12), "France": (481.48, 314.71), "Germany": (503.53, 295.36),
    "Spain": (464.12, 339.47), "Belgium": (487.35, 298.02), "Netherlands": (489.90, 290.66),
    "Italy": (508.28, 329.93), "Portugal": (449.10, 341.99), "Ireland": (451.46, 286.05),
    "Switzerland": (497.46, 314.32), "Austria": (513.79, 310.90), "Poland": (528.76, 291.07),
    "Sweden": (522.12, 231.60), "Norway": (517.22, 217.21), "Finland": (548.18, 221.56),
    "Greece": (539.44, 344.08), "Turkey": (572.81, 343.64), "Egypt": (558.33, 385.18),
    "India": (698.14, 395.80), "Thailand": (757.72, 420.42), "Vietnam": (772.63, 415.19),
    "Philippines": (819.03, 429.47), "Indonesia": (804.69, 469.07), "Malaysia": (782.22, 451.78),
    "Australia": (852.17, 538.35), "Brazil": (325.46, 493.87), "Argentina": (290.72, 572.87),
    "Colombia": (269.36, 451.39), "Peru": (265.75, 488.22), "Chile": (273.45, 589.17),
    "Ecuador": (252.77, 466.51), "South Africa": (544.74, 547.37), "Nigeria": (497.13, 435.45),
    "Kenya": (580.45, 460.67), "Saudi Arabia": (599.17, 392.58), "Iraq": (597.08, 364.31),
    "Iran": (626.46, 365.57), "Israel": (572.70, 370.03), "Kazakhstan": (663.16, 307.42),
    "Mongolia": (763.59, 313.49), "Ukraine": (562.39, 304.86), "Romania": (544.51, 317.95),
    "Hungary": (528.97, 312.59), "Czech Republic": (517.50, 301.89), "Denmark": (502.74, 272.64),
    "New Zealand": (958.98, 591.40), "Panama": (249.62, 438.54), "Cuba": (252.14, 400.43),
    "Venezuela": (288.57, 442.44), "Bolivia": (292.78, 509.87), "Paraguay": (310.69, 529.28),
    "Uruguay": (317.11, 559.48), "Guatemala": (220.73, 417.83), "Costa Rica": (238.35, 434.59),
}

# ---- 真实面积重心经纬度（可信、且无海外领地干扰的国家） ----
GEO = {
    "South Korea": (127.8, 36.4), "China": (103.9, 36.0), "Taiwan": (120.96, 23.7),
    "France": (2.5, 46.6), "Germany": (10.4, 51.2), "Spain": (-3.7, 40.4),
    "Belgium": (4.6, 50.6), "Netherlands": (5.5, 52.2), "Italy": (12.6, 42.8),
    "Portugal": (-8.2, 39.6), "Ireland": (-8.0, 53.2), "Switzerland": (8.2, 46.8),
    "Austria": (14.1, 47.6), "Poland": (19.4, 52.1), "Sweden": (15.0, 62.0),
    "Greece": (22.0, 39.1), "Turkey": (35.2, 39.0), "Egypt": (29.0, 26.8),
    "India": (79.0, 22.5), "Thailand": (101.0, 15.0), "Vietnam": (106.1, 16.2),
    "Philippines": (122.0, 12.0), "Malaysia": (102.0, 4.0), "Australia": (134.0, -25.0),
    "Brazil": (-51.0, -10.0), "Argentina": (-64.0, -35.0), "Colombia": (-73.0, 4.0),
    "Peru": (-75.0, -9.5), "Chile": (-71.0, -35.0), "Ecuador": (-78.4, -1.4),
    "South Africa": (24.5, -29.5), "Nigeria": (8.0, 9.5), "Kenya": (37.8, 0.2),
    "Saudi Arabia": (45.0, 24.0), "Iraq": (43.7, 33.2), "Iran": (53.7, 32.4),
    "Kazakhstan": (67.0, 48.0), "Mongolia": (103.0, 46.5), "Ukraine": (31.0, 49.0),
    "Romania": (25.0, 45.9), "Hungary": (19.4, 47.2), "Czech Republic": (15.3, 49.8),
    "Denmark": (9.5, 56.0), "New Zealand": (172.5, -41.5), "Panama": (-80.0, 8.5),
    "Cuba": (-79.5, 21.6), "Venezuela": (-66.0, 7.0), "Bolivia": (-64.0, -17.0),
    "Paraguay": (-58.0, -23.5), "Uruguay": (-56.0, -33.0), "Guatemala": (-90.5, 15.5),
    "Costa Rica": (-84.0, 10.0),
}


def solve(rows, vals):
    A = [[0.0] * 3 for _ in range(3)]
    B = [0.0] * 3
    for r, v in zip(rows, vals):
        for i in range(3):
            B[i] += r[i] * v
            for j in range(3):
                A[i][j] += r[i] * r[j]
    M = [A[i][:] + [B[i]] for i in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda k: abs(M[k][i]))
        M[i], M[p] = M[p], M[i]
        for k in range(i + 1, 3):
            f = M[k][i] / M[i][i]
            for j in range(i, 4):
                M[k][j] -= f * M[i][j]
    x = [0.0] * 3
    for i in (2, 1, 0):
        s = M[i][3] - sum(M[i][j] * x[j] for j in range(i + 1, 3))
        x[i] = s / M[i][i]
    return x


def fit(names):
    rows = [[GEO[n][0], GEO[n][1], 1.0] for n in names]
    cx = solve(rows, [SVG[n][0] for n in names])
    cy = solve(rows, [SVG[n][1] for n in names])
    return cx, cy


names = [n for n in GEO if n in SVG]
print("初始参考点:", len(names))
cx, cy = fit(names)

def predict(lon, lat, cx=cx, cy=cy):
    return (cx[0] * lon + cx[1] * lat + cx[2], cy[0] * lon + cy[1] * lat + cy[2])

# 迭代剔离群（>2.2 * 中位残差 或 >14px）
for it in range(6):
    res = []
    for n in names:
        X, Y = predict(GEO[n][0], GEO[n][1])
        res.append((((SVG[n][0] - X) ** 2 + (SVG[n][1] - Y) ** 2) ** 0.5, n))
    res.sort(reverse=True)
    worst, wn = res[0]
    med = sorted(r[0] for r in res)[len(res) // 2]
    if worst > 14 or worst > 2.4 * med:
        print(f"  drop {wn} 残差 {worst:.1f}px")
        names.remove(wn)
        cx, cy = fit(names)
    else:
        break

res = []
for n in names:
    X, Y = predict(GEO[n][0], GEO[n][1])
    res.append((((SVG[n][0] - X) ** 2 + (SVG[n][1] - Y) ** 2) ** 0.5, n))
res.sort(reverse=True)
print("保留参考点:", len(names))
print("残差 top5:", [(n, round(d, 1)) for d, n in res[:5]])
print("中位残差: %.2f px" % sorted(d for d, _ in res)[len(res) // 2])
print("变换: x = %.4f*lon + %.4f*lat + %.2f" % tuple(cx))
print("      y = %.4f*lon + %.4f*lat + %.2f" % tuple(cy))

# 校验：日本（不参与拟合）
print("\n校验（不参与拟合的国家，看预测 vs 实际）：")
for n in ["Japan", "United Kingdom", "United States", "Russia", "Norway", "Finland"]:
    if n in SVG:
        print(f"  {n:16s} 实际={SVG[n]} 预测=({predict(*GEO[n])[0]:.0f}, {predict(*GEO[n])[1]:.0f})"
              if n in GEO else f"  {n:16s} 实际={SVG[n]} (无经纬参考)")

CITY_GEO = {
    "GOYANG": (126.83, 37.66), "TOKYO": (139.69, 35.68), "EL PASO": (-106.49, 31.76),
    "MEXICO CITY": (-99.13, 19.43), "STANFORD": (-122.17, 37.43), "LAS VEGAS": (-115.14, 36.17),
    "LOS ANGELES": (-118.24, 34.05), "EAST RUTHERFORD": (-74.10, 40.83),
    "FOXBOROUGH": (-71.27, 42.09), "TORONTO": (-79.38, 43.65), "ARLINGTON": (-97.11, 32.74),
    "CHICAGO": (-87.63, 41.88), "MUNICH": (11.58, 48.14), "BOGOTA": (-74.07, 4.71),
    "LIMA": (-77.04, -12.05), "BALTIMORE": (-76.61, 39.29), "PARIS": (2.35, 48.86),
    "LONDON": (-0.13, 51.51), "BRUSSELS": (4.35, 50.85), "MADRID": (-3.70, 40.42),
    "iHEART FEST": (-118.24, 34.05),
    # 2026 世界杯决赛 = 7/19，场地 MetLife Stadium（和 8/1-2 的 East Rutherford 同址）
    "WORLD CUP 2026": (-74.10, 40.83),
}

old = json.loads(open(data_path, encoding="utf-8").read().split("=", 1)[1].strip().rstrip(";"))
looks = old["looks"]
print()
for c in old["cities"]:
    lon, lat = CITY_GEO.get(c["city"], (0, 0))
    X, Y = predict(lon, lat)
    c["x"], c["y"] = round(X / 1010, 5), round(Y / 666, 5)
    print(f"{c['city']:18s} x={c['x']*100:6.2f}%  y={c['y']*100:6.2f}%")
old["route"] = [{"x": c["x"], "y": c["y"], "city": c["city"]} for c in old["cities"]]

with open(data_path, "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(old, ensure_ascii=False) + ";\n")
print("\n写回 data.js")
