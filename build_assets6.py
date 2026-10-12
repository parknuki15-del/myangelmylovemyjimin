#!/usr/bin/env python3
"""v6：world.svg 的投影不是等距投影 —— 实测 y 方向是「墨卡托」
（y_lin rms 7.06 / y_quad 5.76 / y_miller 4.26 / y_merc 3.29）。
这里改成 x = a*lon + c（纯经度，实测 b≈0）、y = m*mercator(lat) + d，
并迭代剔离群，然后重算 22 个城市的坐标。
"""
import json, math, os

BASE = "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site/assets"
data_path = os.path.join(BASE, "data.js")

# ---- SVG 面积重心（浏览器逐国光栅化得到） ----
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

# ---- 真实面积重心经纬度 ----
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


def merc(lat):
    la = max(-85.0, min(85.0, lat)) * math.pi / 180.0
    return math.log(math.tan(math.pi / 4 + la / 2))


def solve(rows, vals, k):
    A = [[0.0] * k for _ in range(k)]
    B = [0.0] * k
    for r, v in zip(rows, vals):
        for i in range(k):
            B[i] += r[i] * v
            for j in range(k):
                A[i][j] += r[i] * r[j]
    M = [A[i][:] + [B[i]] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda q: abs(M[q][i]))
        M[i], M[p] = M[p], M[i]
        for q in range(i + 1, k):
            f = M[q][i] / M[i][i]
            for j in range(i, k + 1):
                M[q][j] -= f * M[i][j]
    x = [0.0] * k
    for i in range(k - 1, -1, -1):
        x[i] = (M[i][k] - sum(M[i][j] * x[j] for j in range(i + 1, k))) / M[i][i]
    return x


def fit(ns):
    cx = solve([[GEO[n][0], 1.0] for n in ns], [SVG[n][0] for n in ns], 2)
    cy = solve([[merc(GEO[n][1]), 1.0] for n in ns], [SVG[n][1] for n in ns], 2)
    return cx, cy


names = [n for n in GEO if n in SVG]
cx, cy = fit(names)

for _ in range(10):
    res = []
    for n in names:
        X = cx[0] * GEO[n][0] + cx[1]
        Y = cy[0] * merc(GEO[n][1]) + cy[1]
        res.append((math.hypot(SVG[n][0] - X, SVG[n][1] - Y), n))
    res.sort(reverse=True)
    med = sorted(r[0] for r in res)[len(res) // 2]
    if res[0][0] > 11 or res[0][0] > 2.6 * med:
        print("  drop %-16s 残差 %.1fpx" % (res[0][1], res[0][0]))
        names.remove(res[0][1])
        cx, cy = fit(names)
    else:
        break

def P(lon, lat):
    return (cx[0] * lon + cx[1], cy[0] * merc(lat) + cy[1])

res = []
for n in names:
    X, Y = P(*GEO[n])
    res.append((math.hypot(SVG[n][0] - X, SVG[n][1] - Y), n))
res.sort(reverse=True)
print("保留参考点:", len(names), " rms=%.2f px" %
      (sum(d * d for d, _ in res) / len(res)) ** 0.5)
print("残差 top6:", [(n, round(d, 1)) for d, n in res[:6]])
print("x = %.5f*lon + %.3f" % (cx[0], cx[1]))
print("y = %.5f*merc(lat) + %.3f" % (cy[0], cy[1]))

print("\n校验（预测 vs SVG 真实重心）：")
for n in ["South Korea", "China", "Japan", "Taiwan", "United Kingdom", "United States"]:
    if n in SVG:
        X, Y = P(*GEO[n]) if n in GEO else (0, 0)
        print("  %-16s SVG=%s   预测=(%.0f, %.0f)" % (n, SVG[n], X, Y))

CITY_GEO = {
    "GOYANG": (126.83, 37.66), "TOKYO": (139.69, 35.68), "EL PASO": (-106.49, 31.76),
    "MEXICO CITY": (-99.13, 19.43), "STANFORD": (-122.17, 37.43), "LAS VEGAS": (-115.14, 36.17),
    "LOS ANGELES": (-118.24, 34.05), "EAST RUTHERFORD": (-74.10, 40.83),
    "FOXBOROUGH": (-71.27, 42.09), "TORONTO": (-79.38, 43.65), "ARLINGTON": (-97.11, 32.74),
    "CHICAGO": (-87.63, 41.88), "MUNICH": (11.58, 48.14), "BOGOTA": (-74.07, 4.71),
    "LIMA": (-77.04, -12.05), "BALTIMORE": (-76.61, 39.29), "PARIS": (2.35, 48.86),
    "LONDON": (-0.13, 51.51), "BRUSSELS": (4.35, 50.85), "MADRID": (-3.70, 40.42),
    "iHEART FEST": (-118.24, 34.05),
    # 2026 世界杯决赛（7/19）在 MetLife Stadium，与 8/1-2 East Rutherford 同址
    "WORLD CUP 2026": (-74.10, 40.83),
}

old = json.loads(open(data_path, encoding="utf-8").read().split("=", 1)[1].strip().rstrip(";"))
print()
for c in old["cities"]:
    X, Y = P(*CITY_GEO[c["city"]])
    c["x"], c["y"] = round(X / 1010, 5), round(Y / 666, 5)
    print("%-18s x=%6.2f%%  y=%6.2f%%" % (c["city"], c["x"] * 100, c["y"] * 100))

old["route"] = [{"x": c["x"], "y": c["y"], "city": c["city"]} for c in old["cities"]]
with open(data_path, "w", encoding="utf-8") as f:
    f.write("window.SITE_DATA = " + json.dumps(old, ensure_ascii=False) + ";\n")
print("\n写回 data.js")
