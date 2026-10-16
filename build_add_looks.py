#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""往巡演造型列表「末尾追加」新造型（当前 96 套 -> 100 套）。

为什么不重跑 build_assets2.py：
  那个脚本把「朴智旻造型/根目录 png + maple精灵图/v4 + v5」整个枚举一遍，按文件名
  排序 + md5 去重，从头编号。一旦目录里多了/少了/改了名，已有 96 套的下标和城市标签
  就会整体错位，页面上「造型 ↔ 真人原图」的配对会全崩（而且它还会把躺在
  maple精灵图/ 里的 原创BGM-分析图.png 误收成一套）。
  这里只做「在现有编号后面接着加」，已有 001~096 一个字节都不动。

加工参数严格复刻 build_assets2.py，保证新图跟老图观感一致：
  抠白底 → 裁边 → 统一高 560 → 量化 192 色
缩略图复刻 build_thumbs.py：1/4 整数倍最近邻。
真人图复刻 build_looks_real.py：裁 3:4、260x346、quality 76。

用法：
    python3 build_add_looks.py            # 追加
    python3 build_add_looks.py --dry      # 只打印，不写文件
"""
import argparse
import json
import os
import sys
from collections import deque

from PIL import Image

SRC = '/Users/whitekunckles/Desktop/朴智旻造型'
LOOKS = 'assets/looks'
THUMB = 'assets/looks-thumb'
REAL = 'assets/looks-real'
DATA = 'assets/data.js'

# 新增造型：按这个顺序追加成 look097、look098……
# 每项 = (日期, 城市, 精灵图路径, 真人原图路径 或 None)
NEW = [
    ('10.10', 'LIMA',
     os.path.join(SRC, "maple精灵图/v5/261010 BTS WORLD TOUR 'ARIRANG' IN LIMA.png"),
     os.path.join(SRC, "新增/261010 BTS WORLD TOUR 'ARIRANG' IN LIMA.jpg")),
    ('10.10', 'LIMA',
     os.path.join(SRC, "maple精灵图/v5/261010BTS WORLD TOUR 'ARIRANG' IN LIMA.png"),
     os.path.join(SRC, "新增/261010BTS WORLD TOUR 'ARIRANG' IN LIMA.jpg")),
    ('10.14', 'SANTIAGO',
     os.path.join(SRC, "maple精灵图/v5/261014 BTS WORLD TOUR 'ARIRANG' IN SANTIAGO.png"),
     os.path.join(SRC, "新增/261014 BTS WORLD TOUR 'ARIRANG' IN SANTIAGO.jpg")),
    # 第 4 套：用户指定的 261014BTS...SANTIAGO.png
    # ⚠️ 实测其 md5 与「候选_生日/生日_A_蛋糕版_更萌.png」完全相同
    ('10.14', 'SANTIAGO',
     os.path.join(SRC, "maple精灵图/v5/261014BTS WORLD TOUR 'ARIRANG' IN SANTIAGO.png"),
     os.path.join(SRC, "新增/261014BTS WORLD TOUR 'ARIRANG' IN SANTIAGO.jpg")),
]

TARGET_AR = 3 / 4
Y_BIAS = 0.10
SIZE = (260, 346)
QUALITY = 76
SCALE = 4


def flood_remove_white(img, thresh=238):
    rgb = img.convert('RGB')
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
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and alpha[ny][nx] == 255:
                r, g, b = px[nx, ny]
                if r >= thresh and g >= thresh and b >= thresh:
                    alpha[ny][nx] = 0
                    q.append((nx, ny))
    out = img.convert('RGBA')
    mask = Image.new('L', (w, h), 255)
    mp = mask.load()
    for y in range(h):
        row = alpha[y]
        for x in range(w):
            if row[x] == 0:
                mp[x, y] = 0
    out.putalpha(mask)
    return out


def trim(im, pad=4):
    bbox = im.getchannel('A').getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    return im.crop((max(0, l - pad), max(0, t - pad),
                    min(im.width, r + pad), min(im.height, b + pad)))


def crop_thumb(src, dst):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if w / h > TARGET_AR:
        cw, ch, x0, y0 = int(h * TARGET_AR), h, (w - int(h * TARGET_AR)) // 2, 0
    else:
        cw, ch = w, int(w / TARGET_AR)
        x0, y0 = 0, int((h - ch) * Y_BIAS)
    im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize(SIZE, Image.LANCZOS)
    im.save(dst, quality=QUALITY, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只打印，不写文件')
    ap.add_argument('--only', help='只重做 NEW 里的第几套（1-based，可逗号分隔）。'
                                   '换图之后覆盖写回同一个编号，不再往后追加。例：--only 4')
    args = ap.parse_args()
    only = [int(x) for x in args.only.split(',')] if args.only else None

    for _, _, sp, rp in NEW:
        if not os.path.isfile(sp):
            sys.exit('找不到精灵图：%s' % sp)
        if rp and not os.path.isfile(rp):
            sys.exit('找不到真人图：%s' % rp)

    have = sorted(f for f in os.listdir(LOOKS) if f.startswith('look') and f.endswith('.png'))
    start = int(have[-1][4:7]) if have else 0
    print('现有造型 %d 套，最后一号 look%03d，接着从 look%03d 开始' % (len(have), start, start + 1))

    txt = open(DATA, encoding='utf-8').read()
    data = json.loads(txt.split('=', 1)[1].strip().rstrip(';'))
    if len(data['looks']) != start:
        sys.exit('data.js 里 %d 条，但 assets/looks 有 %d 张，对不上，先查清楚'
                 % (len(data['looks']), start))

    if not args.dry:
        os.makedirs(THUMB, exist_ok=True)
        os.makedirs(REAL, exist_ok=True)

    total_sprite = total_thumb = total_real = 0
    for i, (date, city, sp, rp) in enumerate(NEW):
        if only is not None and (i + 1) not in only:
            continue
        # 正常追加：start+1 起。重做：回推到这套原本的编号（start 里已经含它自己）
        n = (start - len(NEW) + 1 + i) if only is not None else (start + i + 1)
        name = 'look%03d' % n

        im = flood_remove_white(Image.open(sp))
        im = trim(im)
        s = 560 / im.height
        im = im.resize((round(im.width * s), 560), Image.LANCZOS)
        im = im.quantize(colors=192, method=Image.FASTOCTREE).convert('RGBA')
        if not args.dry:
            im.save(os.path.join(LOOKS, name + '.png'), optimize=True)
            total_sprite += os.path.getsize(os.path.join(LOOKS, name + '.png'))
            # 缩略图：1/4 整数倍最近邻
            nt = im.resize((max(1, round(im.width / SCALE)), max(1, round(im.height / SCALE))), Image.NEAREST)
            nt.save(os.path.join(THUMB, name + '.png'), optimize=True)
            total_thumb += os.path.getsize(os.path.join(THUMB, name + '.png'))
            # 真人原图
            crop_thumb(rp, os.path.join(REAL, name + '.jpg'))
            total_real += os.path.getsize(os.path.join(REAL, name + '.jpg'))

        entry = {'img': 'assets/looks/%s.png' % name, 'date': date, 'city': city,
                 'real': ('assets/looks-real/%s.jpg' % name) if rp else None}
        if only is not None:
            data['looks'][n - 1] = entry          # 覆盖同一编号
        else:
            data['looks'].append(entry)
        print('  %s  %s %-9s  %-58s  %s' % (name, date, city,
                                           os.path.basename(sp),
                                           os.path.basename(rp) if rp else '(无真人图)'))

    if args.dry:
        print('(--dry，没有写文件)')
        return

    with open(DATA, 'w', encoding='utf-8') as f:
        f.write('window.SITE_DATA = ' + json.dumps(data, ensure_ascii=False,
                                                   separators=(', ', ': ')) + ';\n')
    if only is not None:
        print('完成：重做第 %s 套（覆盖同一编号），造型总数仍为 %d 套'
              % (args.only, len(data['looks'])))
    else:
        print('完成：造型 %d -> %d 套' % (start, start + len(NEW)))
    print('  造型图 %.2f MB / 缩略图 %.2f MB / 真人图 %.2f MB'
          % (total_sprite / 1048576, total_thumb / 1048576, total_real / 1048576))
    print('⚠️  需要同步：造型总览格子数、路线图坐标（如果新城市要上图）')


if __name__ == '__main__':
    main()
