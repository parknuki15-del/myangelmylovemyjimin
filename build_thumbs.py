#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成巡演页「造型总览」用的缩略图。

为什么需要：
  assets/looks/look001.png ~ look096.png 是 330x560 左右的像素小人，单张 ~93 KB，
  96 张一共 9.3 MB。总览格里一张只显示 ~85px 宽，直接铺原图太重了。
  这里按 1/4 整数倍最近邻缩放（560 -> 140），像素画不会糊，总大小降到 ~1.3 MB。

用法：
    python3 build_thumbs.py            # 重算 assets/looks-thumb/
    python3 build_thumbs.py --force    # 忽略时间戳，全部重算

换掉 assets/looks/ 里的图之后重跑一次即可。
需要 Pillow：pip install pillow
"""

import argparse
import glob
import os
import sys

SRC = 'assets/looks'
DST = 'assets/looks-thumb'
SCALE = 4          # 整数倍缩放：像素画按整数比缩才不会出现锯齿/糊边


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='全部重算，忽略时间戳')
    args = ap.parse_args()

    try:
        from PIL import Image
    except ImportError:
        sys.exit('缺少 Pillow，先跑：pip install pillow')

    if not os.path.isdir(SRC):
        sys.exit('找不到 %s' % SRC)

    os.makedirs(DST, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, '*.png')))
    if not files:
        sys.exit('%s 里没有 png' % SRC)

    made = skipped = 0
    total = 0
    for p in files:
        out = os.path.join(DST, os.path.basename(p))
        if (not args.force and os.path.exists(out)
                and os.path.getmtime(out) >= os.path.getmtime(p)):
            skipped += 1
            total += os.path.getsize(out)
            continue
        im = Image.open(p).convert('RGBA')
        w, h = im.size
        # 1/4 之后不足 1px 的也留 1px，避免极端窄图变成 0 宽
        nt = im.resize((max(1, round(w / SCALE)), max(1, round(h / SCALE))), Image.NEAREST)
        nt.save(out, optimize=True)
        made += 1
        total += os.path.getsize(out)

    print('源图 %d 张 -> 生成 %d / 跳过 %d，合计 %.1f MB（原图约 %.1f MB）' % (
        len(files), made, skipped, total / 1048576,
        sum(os.path.getsize(f) for f in files) / 1048576))


if __name__ == '__main__':
    main()
