#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""照片墙「往后追加」新照片。

为什么不直接重跑 build_assets2.py：
  那个脚本是 copy_jpgs('照片墙','wall',760)，把整个目录按文件名排序重新编成
  001.jpg、002.jpg……一旦目录里多了 / 少了 / 改了名，已有 18 张的下标就会整体错位，
  页面上每张照片的位置和灯箱顺序都会跟着变。
  这里只做「在现有编号后面接着加」，已有 001~018 一个字节都不动。

用法：
    python3 build_add_wall.py            # 追加 照片墙/新增/ 里的全部 jpg
    python3 build_add_wall.py --dry      # 只打印，不写文件

加工参数跟 build_assets2.py 的 copy_jpgs 保持一致：宽超 760 才缩，quality=80。
"""
import argparse
import os
import shutil
import sys

from PIL import Image

SRC = '/Users/whitekunckles/Desktop/朴智旻造型/照片墙/新增'
OUT = 'assets/wall'
MAXW = 760
QUALITY = 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只打印，不写文件')
    args = ap.parse_args()

    if not os.path.isdir(SRC):
        sys.exit('找不到 %s' % SRC)
    os.makedirs(OUT, exist_ok=True)

    # 已有几张（严格按 NNN.jpg 数，避免混进别的文件）
    have = sorted(f for f in os.listdir(OUT)
                  if len(f) == 7 and f.endswith('.jpg') and f[:3].isdigit())
    start = int(have[-1][:3]) if have else 0
    print('现有 %d 张，最后一号 %03d，接着从 %03d 开始' % (len(have), start, start + 1))

    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(('.jpg', '.jpeg')))
    print('待追加 %d 张' % len(files))

    n = start
    for f in files:
        n += 1
        dst = os.path.join(OUT, '%03d.jpg' % n)
        src = os.path.join(SRC, f)
        im = Image.open(src)
        im = im.convert('RGB')
        w, h = im.size
        if w > MAXW:
            im = im.resize((MAXW, round(h * MAXW / w)), Image.LANCZOS)
        print('  %03d.jpg  <-  %s  %dx%d -> %dx%d' % (n, f, w, h, im.width, im.height))
        if not args.dry:
            im.save(dst, quality=QUALITY, optimize=True)

    if args.dry:
        print('(--dry，没有写文件)')
        return

    total = len([f for f in os.listdir(OUT) if f.endswith('.jpg')])
    print('完成：assets/wall 现在共 %d 张' % total)
    print('⚠️  记得到 data.js 把 counts.wall 改成 %d' % total)


if __name__ == '__main__':
    main()
