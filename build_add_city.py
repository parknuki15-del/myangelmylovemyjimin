#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""往巡演地图「末尾追加」一座城市（当前用于 SANTIAGO）。

为什么不重跑 build_assets4/5/6.py：
  那几个脚本会重新枚举精灵图、重新拟合投影，把 22 座城市的 x/y 全部重算一遍。
  拟合是确定性的，理论上值不变，但只要拟合用的参考点集合有任何变动，所有城市的
  坐标都会整体漂移 —— 现有地图的点位是调好的，不值得为了加一站去冒这个险。
  这里只做「在末尾加一个点 + 加一段路线」，现有 22 座城市一个数字都不动。

投影沿用 build_route.py 里写死的常量（即 build_assets6.py 拟合结果）：
    x = A*lon + C          （纯经度）
    y = M*mercator(lat) + D（墨卡托）
已用 LIMA 反算校验过，误差 < 0.2px。

用法：
    python3 build_add_city.py            # 追加
    python3 build_add_city.py --dry      # 只打印，不写文件
"""
import argparse
import json
import math
import sys

DATA = 'assets/data.js'

A, C = 2.81040, 474.371          # x = A*lon + C
M, D = -159.94609, 462.135       # y = M*merc(lat) + D
SVG_W, SVG_H = 1010, 666

PALETTE = ["#e8534a", "#ef7f5f", "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f",
           "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f", "#f0a24b", "#e8534a",
           "#d94f6a", "#ef7f5f", "#f0a24b", "#e8534a", "#d94f6a", "#ef7f5f",
           "#f0a24b", "#e8534a", "#d94f6a"]

# 新增城市：(城市名, 经度, 纬度, 这套造型在 looks 里的首个编号 1-based, 套数)
NEW_CITY = ('SANTIAGO', -70.65, -33.45, 99, 2)

# 顺带把已有城市的套数补上（新造型落回同一个城市，count 要跟着长）
COUNT_FIX = {'LIMA': 6}


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
    lon1, lat1 = map(math.radians, p1)
    lon2, lat2 = map(math.radians, p2)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def gc(p1, p2, n=40):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只打印，不写文件')
    args = ap.parse_args()

    txt = open(DATA, encoding='utf-8').read()
    data = json.loads(txt.split('=', 1)[1].strip().rstrip(';'))

    cities = data['cities']
    looks = data['looks']
    print('cities %d 座 / looks %d 套 / legs %d 段' % (len(cities), len(looks), len(data['legs'])))
    print('count 合计 %d（应等于 looks 套数）' % sum(c['count'] for c in cities))

    name, lon, lat, first, count = NEW_CITY
    if any(c['city'] == name for c in cities):
        sys.exit('%s 已经在 cities 里了，别重复加' % name)

    # --- 1. 已有城市的套数补正 ---
    for c in cities:
        if c['city'] in COUNT_FIX:
            print('  %-10s count %s -> %s' % (c['city'], c['count'], COUNT_FIX[c['city']]))
            c['count'] = COUNT_FIX[c['city']]

    # --- 2. 追加新城市 ---
    X, Y = proj(lon, lat)
    entry = {'city': name, 'count': count, 'first': first,
             'x': round(X / SVG_W, 5), 'y': round(Y / SVG_H, 5)}
    cities.append(entry)
    print('  + %-10s count=%d first=%d  x=%.5f y=%.5f  (SVG %.1f,%.1f)' % (
        name, count, first, entry['x'], entry['y'], X, Y))

    # 校验：count 合计应等于 looks 套数
    tot = sum(c['count'] for c in cities)
    print('count 合计 %d vs looks %d  %s' % (tot, len(looks), '✅' if tot == len(looks) else '❌'))
    if tot != len(looks):
        sys.exit('套数对不上，先核对 COUNT_FIX')

    # --- 3. route 同步 ---
    data['route'] = [{'x': c['x'], 'y': c['y'], 'city': c['city']} for c in cities]

    # --- 4. legs：只补最后一段（前一站 -> 新城市）---
    order = [c['city'] for c in cities]
    prev_city = order[-2]
    # 前一站的经纬度：从现有 route 反推不了，直接用脚本里已知的常量
    CITY_GEO = {
        "GOYANG": (126.83, 37.66), "TOKYO": (139.69, 35.68), "EL PASO": (-106.49, 31.76),
        "MEXICO CITY": (-99.13, 19.43), "STANFORD": (-122.17, 37.43), "LAS VEGAS": (-115.14, 36.17),
        "LOS ANGELES": (-118.24, 34.05), "EAST RUTHERFORD": (-74.10, 40.83),
        "FOXBOROUGH": (-71.27, 42.09), "TORONTO": (-79.38, 43.65), "ARLINGTON": (-97.11, 32.74),
        "CHICAGO": (-87.63, 41.88), "MUNICH": (11.58, 48.14), "BOGOTA": (-74.07, 4.71),
        "LIMA": (-77.04, -12.05), "SANTIAGO": (-70.65, -33.45), "BALTIMORE": (-76.61, 39.29),
        "PARIS": (2.35, 48.86), "LONDON": (-0.13, 51.51), "BRUSSELS": (4.35, 50.85),
        "MADRID": (-3.70, 40.42), "iHEART FEST": (-118.24, 34.05),
        "WORLD CUP 2026": (-74.10, 40.83),
    }
    if prev_city not in CITY_GEO:
        sys.exit('前一站 %s 没有经纬度，先补 CITY_GEO' % prev_city)
    p1, p2 = CITY_GEO[prev_city], (lon, lat)
    dist = haversine(p1, p2)
    if dist > 3000:
        segs, kind = split(gc(p1, p2)), 'arc'
    else:
        segs, kind = split([p1, p2]), 'land'
    i = len(order) - 2                      # 与 build_route.py 的索引一致
    for s in segs:
        data['legs'].append({'d': d_of(s), 'color': PALETTE[i % len(PALETTE)], 'kind': kind})
    print('  + 路线 %s -> %s  %.0f km  %s  segs=%d' % (prev_city, name, dist, kind, len(segs)))

    print('cities %d 座 / legs %d 段' % (len(cities), len(data['legs'])))

    if args.dry:
        print('(--dry，没有写文件)')
        return

    with open(DATA, 'w', encoding='utf-8') as f:
        f.write('window.SITE_DATA = ' + json.dumps(data, ensure_ascii=False,
                                                   separators=(', ', ': ')) + ';\n')
    print('写回 data.js')
    print('⚠️  记得到 index.html 把侧栏的 <b>96</b>looks / <b>22</b>cities 改成 %d / %d'
          % (len(looks), len(cities)))


if __name__ == '__main__':
    main()
