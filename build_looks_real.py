#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把巡演真人原图对到 96 套像素造型上。

造型（assets/looks/lookNNN.png）是 build_assets2.py 从「朴智旻造型/」根目录的
精灵图切的，名字里带日期城市（260701...BRUSSELS.png）。真人原图就躺在同一个目录里，
命名同源（260701-BTSWORLDTOUR'ARIRANG'INBRUSSELS.jpg），所以按 (日期, 城市) 对上即可。

几点说明：
  · 造型的顺序由精灵图文件名排序 + md5 去重决定，是确定的。本脚本重新走一遍同样的
    枚举，逐条跟现有 data.js 核对，确保下标一一对应；对不上就直接报错退出。
  · 没有真人原图的日期（TOKYO 04.17-04.28 / EL PASO 05.02-05.03 / MEXICO CITY
    05.07-05.10 / STANFORD 05.16-05.19，共 26 套）另有一批「前26张」，
    存在 Desktop/朴智旻造型/前26张/，文件名是微信序号 `2xxxxxxx_.pic_hd.jpg`，
    里面没有日期城市，没法自动对。这批图已按造型逐套人工比对（精灵图 vs 现场照），
    写死在下面的 MANUAL 里，下标从 1 开始（对应 data.js 的 looks[0]）。
  · 根目录还有 32 张 `2xxxxxxx_.pic_hd.jpg`（微信存的图），名字里没有日期城市，
    对不上号，忽略；判据是文件名里必须出现 ARIRANG / iHeartRadio / World Cup。

用法：
    python3 build_looks_real.py            # 生成 assets/looks-real + 回写 data.js
    python3 build_looks_real.py --dry      # 只打印配对结果，不写文件
"""

import argparse
import hashlib
import json
import os
import re
import sys

import numpy as np
from PIL import Image

SRC = '/Users/whitekunckles/Desktop/朴智旻造型'
SRC26 = '/Users/whitekunckles/Desktop/朴智旻造型/前26张'
DATA = 'assets/data.js'
OUT = 'assets/looks-real'

# 「前26张」人工比对表：data.js 的 looks[下标-1] -> 前26张/ 里的文件名。
# 这批图没有日期城市，只能一套一套看造型认。认的时候按场次分块（同一天的图微信序号连着），
# 同一天两套只要分得清（毛领/网眼/破洞牛仔裤/宽檐帽）就按造型定，剩下一模一样的全黑皮衣
# 按序号先后落座。照片里有 5 张是多余的（蓝色运动服 / 灰T / 军绿外套 / 黑风衣 / 棕色连帽卫衣），
# 没有配上，见文件末尾的 EXTRA 注释。
MANUAL = {
    1:  '20291791459691_.pic_hd.jpg',   # GOYANG 04.11    黑皮衣+链条
    2:  '20311791459789_.pic_hd.jpg',   # GOYANG 04.12    黑毛领大衣（坐着）
    3:  '20371791462944_.pic_hd.jpg',   # TOKYO 04.17     棕短帽衫+灰长T（比耶）
    4:  '20341791459964_.pic_hd.jpg',   # TOKYO 04.17     黑羽饰长外套
    5:  '20431791463166_.pic_hd.jpg',   # TOKYO 04.25     浅灰拉链外套+白T+牛仔裤
    6:  '20421791463164_.pic_hd.jpg',   # TOKYO 04.25     黑皮衣+白T+灰裤
    7:  '20461791463230_.pic_hd.jpg',   # TOKYO 04.26     丸子头+白T+灰卍纹裤
    8:  '20451791463229_.pic_hd.jpg',   # TOKYO 04.26     丸子头+黑皮长衣
    9:  '20491791463541_.pic_hd.jpg',   # TOKYO 04.28     黑皮衣（蹲）
    10: '20481791463519_.pic_hd.jpg',   # TOKYO 04.28     藏蓝牛仔衬衫+牛仔裤（蹲）
    11: '20521791463638_.pic_hd.jpg',   # EL PASO 05.02   黑T+白马甲+米色工装裤
    12: '20531791463660_.pic_hd.jpg',   # EL PASO 05.02   黑皮衣+铆钉+链条
    13: '20541791463758_.pic_hd.jpg',   # EL PASO 05.03   黑皮长外套+腰带
    14: '20551791463758_.pic_hd.jpg',   # EL PASO 05.03   白T+破洞牛仔裤（拿麦）
    15: '20711791532366_.pic_hd.jpg',   # MEXICO 05.07    酒红网眼T+条纹袖+灰裤
    16: '20701791532365_.pic_hd.jpg',   # MEXICO 05.07    黑皮衣（坐）
    17: '20801791537951_.pic_hd.jpg',   # MEXICO 05.09    黑宽檐帽+黑上衣
    18: '20781791537927_.pic_hd.jpg',   # MEXICO 05.09    丸子头+黑皮衣（坐）
    19: '20841791538118_.pic_hd.jpg',   # MEXICO 05.10    黑宽檐帽+灰印花外套+破洞牛仔裤
    20: '20831791538115_.pic_hd.jpg',   # MEXICO 05.10    黑皮衣+链条（站）
    21: '20871791538712_.pic_hd.jpg',   # STANFORD 05.16  黑皮衣+金属扣（坐）
    22: '20861791538712_.pic_hd.jpg',   # STANFORD 05.16  灰连帽衫+灰牛仔
    23: '20911791539931_.pic_hd.jpg',   # STANFORD 05.17  灰外套+白T+灰裤（比耶）
    24: '20901791539930_.pic_hd.jpg',   # STANFORD 05.17  黑皮衣+白T（坐）
    25: '20941791540028_.pic_hd.jpg',   # STANFORD 05.19  酒红T+卡其工装裤（坐）
    26: '20931791540027_.pic_hd.jpg',   # STANFORD 05.19  黑皮衣（站）
}
# 没用上的 5 张：20281791459672(蓝运动服) 20321791459790(灰印花T) 20351791459965(军绿外套)
#                20381791462963(黑风衣+白T) 20401791463059(棕连帽衫，与 20371791462944 同款)


# 精灵图/原图文件名里能出现的城市。注意顺序：先长的后短的，免得 INEL PASO 先被别的吃掉
CITIES = ['EAST RUTHERFORD', 'MEXICO CITY', 'LAS VEGAS', 'LOS ANGELES',
          'IHEARTRADIO MUSIC FESTIVAL', 'ARLINGTON', 'BALTIMORE', 'FOXBOROUGH',
          'BRUSSELS', 'TORONTO', 'STANFORD', 'CHICAGO', 'GOYANG', 'MUNICH',
          'MADRID', 'LONDON', 'EL PASO', 'PARIS', 'BOGOTA', 'JAPAN', 'LIMA']

# 精灵图那一批把东京写成 JAPAN，later 的人工订正成 TOKYO；原图这边也要跟着认
CITY_FIX = {'JAPAN': 'TOKYO'}

TARGET_AR = 3 / 4          # 卡片是竖构图
Y_BIAS = 0.10              # 裁竖构图时从上往下 10% 起裁 —— 演唱会图人头都在画面上方
SIZE = (260, 346)          # 输出尺寸（3:4）
QUALITY = 76


def norm(fn):
    return fn.upper().replace('-', '').replace('_', '').replace(' ', '')


def parse_label(fn):
    """`260701-BTSWORLDTOUR'ARIRANG'INBRUSSELS.jpg` -> ('07.01', 'BRUSSELS')"""
    n = norm(fn)
    m = re.match(r'(\d{2})(\d{2})(\d{2})', n)
    if not m:
        return None, None
    date = '%s.%s' % (m.group(2), m.group(3))
    city = None
    for c in CITIES:
        if c.replace(' ', '') in n:
            city = c
            break
    if city == 'IHEARTRADIO MUSIC FESTIVAL':
        city = 'iHEART FEST'
    if 'WORLDCUP' in n or 'FIFA' in n:
        city = 'WORLD CUP 2026'
    if city is None:
        return None, None
    return date, CITY_FIX.get(city, city)


# ---------------------------------------------------------------- 复现造型顺序
def sprite_sequence():
    """按 build_assets2.py 的规则重新枚举精灵图：根目录 png + 两个 maple 子目录，
    按文件名排序，md5 去重。返回 [(date, city, filename)]。"""
    files = []
    for f in sorted(os.listdir(SRC)):
        if f.lower().endswith('.png'):
            files.append(os.path.join(SRC, f))
    for sub in ('maple精灵图/v4', 'maple精灵图/v5'):
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.png'):
                files.append(os.path.join(d, f))
    files.sort(key=lambda p: os.path.basename(p))

    seq, seen = [], set()
    for p in files:
        with open(p, 'rb') as fh:
            md5 = hashlib.md5(fh.read()).hexdigest()
        if md5 in seen:
            continue
        seen.add(md5)
        date, city = parse_label(os.path.basename(p))
        seq.append((date, city, os.path.basename(p)))
    return seq


# ---------------------------------------------------------------- 原图
def is_photo(path):
    """根目录里混了几张「精灵图另存成 jpg」的图（GOYANG 那几张），白底，
    不是现场照。判据：缩到 60px 看四边一圈的平均亮度，接近纯白就是精灵图。"""
    im = Image.open(path).convert('RGB').resize((60, 60))
    a = np.asarray(im).astype(np.float32)
    ring = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return ring.mean() <= 225


def real_photos():
    """根目录里的巡演原图，按日期分组。"""
    groups = {}
    skipped = []
    for f in sorted(os.listdir(SRC)):
        if not f.lower().endswith(('.jpg', '.jpeg')):
            continue
        if not re.search(r"ARIRANG|IHEART|WORLD\s?CUP|FIFA", f, re.I):
            continue                      # 微信存下来的无日期图，跳过
        date, city = parse_label(f)
        if not date:
            continue
        if not is_photo(os.path.join(SRC, f)):
            skipped.append(f)
            continue
        groups.setdefault(date, []).append(f)
    if skipped:
        print('  跳过 %d 张白底精灵图：%s' % (len(skipped), '、'.join(skipped[:3]) + ('…' if len(skipped) > 3 else '')))
    return groups


def crop_thumb(src, dst):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if w / h > TARGET_AR:                 # 太宽 -> 裁宽
        cw, ch, x0, y0 = int(h * TARGET_AR), h, (w - int(h * TARGET_AR)) // 2, 0
    else:                                 # 太高 -> 裁高，从上往下留一点头
        cw, ch = w, int(w / TARGET_AR)
        x0, y0 = 0, int((h - ch) * Y_BIAS)
    im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize(SIZE, Image.LANCZOS)
    im.save(dst, quality=QUALITY, optimize=True)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只打印，不写文件')
    args = ap.parse_args()

    txt = open(DATA, encoding='utf-8').read()
    data = json.loads(txt.split('=', 1)[1].strip().rstrip(';'))
    looks = data['looks']

    seq = sprite_sequence()
    if len(seq) != len(looks):
        sys.exit('造型数对不上：复现 %d 条，data.js %d 条' % (len(seq), len(looks)))
    for i, ((d, c, fn), lk) in enumerate(zip(seq, looks)):
        if d != lk['date']:
            sys.exit('第 %d 条对不上：精灵图 %s(%s,%s) vs data.js (%s,%s)'
                     % (i + 1, fn, d, c, lk['date'], lk['city']))
    print('顺序核对通过：%d 条逐条一致' % len(looks))

    photos = real_photos()
    print('巡演原图：%d 个日期 / %d 张' % (len(photos), sum(len(v) for v in photos.values())))

    if not args.dry:
        os.makedirs(OUT, exist_ok=True)

    per_date_seen = {}
    hit = miss = 0
    total = 0
    manual_hit = 0
    for i, lk in enumerate(looks):
        d = lk['date']
        pool = photos.get(d, [])
        src = None
        if pool:
            k = per_date_seen.get(d, 0)
            per_date_seen[d] = k + 1
            src = os.path.join(SRC, pool[k % len(pool)])
        elif (i + 1) in MANUAL:
            p = os.path.join(SRC26, MANUAL[i + 1])
            if not os.path.isfile(p):
                sys.exit('前26张 里找不到：%s' % MANUAL[i + 1])
            src = p
            manual_hit += 1
        if src:
            name = 'look%03d.jpg' % (i + 1)
            dst = os.path.join(OUT, name)
            if not args.dry:
                crop_thumb(src, dst)
                total += os.path.getsize(dst)
            lk['real'] = 'assets/looks-real/' + name
            hit += 1
        else:
            lk['real'] = None
            miss += 1

    print('配对成功 %d 套（其中「前26张」人工比对 %d 套）/ 缺原图 %d 套'
          % (hit, manual_hit, miss))
    missing = sorted({lk['date'] + ' ' + lk['city'] for lk in looks if not lk['real']})
    if missing:
        print('  缺原图的场次：' + '、'.join(missing))

    if args.dry:
        print('(--dry，没有写文件)')
        return

    with open(DATA, 'w', encoding='utf-8') as f:
        f.write('window.SITE_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(', ', ': ')) + ';\n')
    print('data.js 已回写，%d 张缩略图合计 %.1f MB' % (hit, total / 1048576))


if __name__ == '__main__':
    main()
