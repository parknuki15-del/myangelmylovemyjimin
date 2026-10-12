#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从「毛毡/」那四张图里切出网站要用的素材：

  毛毡板.jpg   -> assets/felt/cork.jpg        软木/毛毡板贴图（无缝平铺）
  篮子.jpg     -> assets/felt/basket.png      粉色铁丝篮子（抠白底）
  装饰素材.jpg -> assets/felt/trinket-XX.png   Y2K 小物（抠黑底）
  装饰.jpg     -> assets/felt/clip-XX.png      长尾夹 / 别针 / 图钉（抠白底）

抠图原理：
  1) 从四条边做 flood fill，把「连到边缘的背景色」标成背景。
     只用阈值 + flood fill（不是全局阈值），物件内部的黑色/白色（比如 CD 的孔、
     拍立得的黑边）才不会被误伤。
  2) 对剩下的前景做连通域分析，筛掉太小的碎片。
  3) alpha 做 0.8px 高斯羽化；再按背景色反预乘（un-premultiply）把边缘的
     黑边/白边洗掉 —— 这一步不做的话贴上去会有一圈脏边。

用法：
    python3 build_felt.py                # 生成全部素材 + 一张 contact-sheet 预览
    python3 build_felt.py --sheet-only   # 只重新拼预览图
"""

import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = '/Users/whitekunckles/Desktop/朴智旻造型/毛毡'
OUT = 'assets/felt'

MIN_AREA = 1800          # 小于这个像素数的连通域当噪点丢掉
PAD = 6                  # 裁切时留的边
INSIDE_TOL = 22          # 「小件落在它框里」判定容差
INSIDE_FLAT = 0.72       # 小件要比大件扁到这个比例以内，才算「同一件的碎片」


# ---------------------------------------------------------------- 连通域
def label(mask):
    """两趟扫描 + 并查集的行游程连通域标记，返回 (labels, n)。只用 numpy 也能跑得动。"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    prev_runs = []            # [(start, end, label)]
    nxt = 1
    m8 = mask.astype(np.int8)
    for y in range(h):
        row = m8[y]
        if not row.any():
            prev_runs = []
            continue
        d = np.diff(np.concatenate(([0], row, [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        cur = []
        for s, e in zip(starts, ends):
            # 和上一行的游程比对，找重叠的接管它的标号
            touch = [pl for (ps, pe, pl) in prev_runs if ps < e and pe > s]
            if touch:
                pl = min(touch)
                for t in touch[1:]:
                    union(pl, t)
                lab[y, s:e] = pl
            else:
                parent.append(nxt)
                lab[y, s:e] = nxt
                pl = nxt
                nxt += 1
            cur.append((int(s), int(e), pl))
        prev_runs = cur

    # 把临时标号统一成根标号，再压成 1..n
    flat = lab.ravel()
    roots = np.array([find(i) for i in range(nxt)], dtype=np.int32)
    flat = roots[flat]
    uniq, inv = np.unique(flat, return_inverse=True)
    keep = uniq != 0
    remap = np.zeros(len(uniq), np.int32)
    remap[keep] = np.arange(1, keep.sum() + 1)
    lab = remap[inv].reshape(h, w)
    return lab, int(keep.sum())


# ---------------------------------------------------------------- 抠图
def background_mask(arr, thresh, mode):
    """从四条边 flood fill，返回「属于背景」的布尔图。mode: 'dark' | 'light'"""
    h, w, _ = arr.shape
    lum = arr.mean(2)
    cand = lum < thresh if mode == 'dark' else lum > thresh
    bg = np.zeros((h, w), bool)
    # 边界上所有候选点做种子
    seed = np.zeros((h, w), bool)
    seed[0, :] = cand[0, :]
    seed[-1, :] = cand[-1, :]
    seed[:, 0] = cand[:, 0]
    seed[:, -1] = cand[:, -1]
    bg |= seed
    while True:
        grow = bg.copy()
        grow[1:, :] |= bg[:-1, :]
        grow[:-1, :] |= bg[1:, :]
        grow[:, 1:] |= bg[:, :-1]
        grow[:, :-1] |= bg[:, 1:]
        grow &= cand
        if grow.sum() == bg.sum():
            break
        bg = grow
    return bg


def cut(arr, bg, feather=0.8):
    """bg=True 的地方透明；反预乘洗掉边缘残留的背景色。"""
    a = (~bg).astype(np.float32)
    if feather:
        aimg = Image.fromarray((a * 255).astype(np.uint8), 'L')
        aimg = aimg.filter(ImageFilter.GaussianBlur(feather))
        a = np.asarray(aimg).astype(np.float32) / 255.0
    al = np.clip(a, 1e-3, 1)[..., None]
    bgcol = arr[bg].mean(0) if bg.any() else np.zeros(3)
    # observed = true*a + bg*(1-a)  =>  true = (observed - bg*(1-a)) / a
    true = (arr.astype(np.float32) - bgcol * (1 - al)) / al
    rgb = np.clip(true, 0, 255).astype(np.uint8)
    out = np.dstack([rgb, (a * 255).astype(np.uint8)])
    return out


def extract(path, mode, thresh, min_area=MIN_AREA, min_side=26,
            merge_gap=0, merge_ratio=0.25, merge_inside=False, max_side=0, colors=0):
    """抠出图上的每一个小物件。

    merge_gap>0 时，会把「包围盒距离小于该值」的连通域并成一个物件 ——
    耳机的两只耳塞和 iPod 是分开的连通域，不并的话会被切成三块。
    merge_ratio 控制「多小才算碎片」：只有面积小于宿主这个比例的小块才会被并，
    调小了才不会把梳子、星星这种独立小件也吞进旁边的大件里。

    merge_inside=True 时，再把「整个框落在另一个更大件的框里、并且明显更扁」的
    连通域并进大件。金色安全别针会被抠成上下两半、长尾夹底部会漏下一条细边，
    靠这条规则合回去。注意不能用「框相交」：拼贴图里相邻大件的框咬得很紧。
    """
    im = Image.open(path).convert('RGB')
    arr = np.asarray(im)
    bg = background_mask(arr, thresh, mode)
    lab, n = label(~bg)

    boxes = {}
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < min_area:
            continue
        boxes[i] = [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, len(ys)]

    host = {i: i for i in boxes}
    if merge_inside:
        order = sorted(boxes, key=lambda k: -boxes[k][4])
        for b in order:
            for a in order:
                if a == b or boxes[b][4] >= boxes[a][4]:
                    continue
                bx, ax = boxes[b], boxes[a]
                if not (bx[0] >= ax[0] - INSIDE_TOL and bx[1] >= ax[1] - INSIDE_TOL
                        and bx[2] <= ax[2] + INSIDE_TOL and bx[3] <= ax[3] + INSIDE_TOL):
                    continue
                if min(bx[2] - bx[0], bx[3] - bx[1]) > min(ax[2] - ax[0], ax[3] - ax[1]) * INSIDE_FLAT:
                    continue          # 体量相当 —— 是两个各自独立的物件
                host[b] = a
                break

    groups = {}
    for i in boxes:
        groups.setdefault(host[i], []).append(i)
    groups = list(groups.values())

    if merge_gap:
        # 按面积从大到小，把小碎片并进它旁边的大物件里。
        # 不能无脑用「包围盒相交」——拼贴图里大物件的框互相咬得很紧，
        # 那样会链式合并成一大坨（第一版就整个并成 1 个）。
        order = sorted(groups, key=lambda g: -sum(boxes[k][4] for k in g))
        kept = []
        for grp in order:
            a = sum(boxes[k][4] for k in grp)
            ba = [min(boxes[k][0] for k in grp), min(boxes[k][1] for k in grp),
                  max(boxes[k][2] for k in grp), max(boxes[k][3] for k in grp)]
            host_grp = None
            for h in kept:
                if a > sum(boxes[k][4] for k in h) * merge_ratio:
                    continue                     # 旗鼓相当的两个大件不并
                hb = [min(boxes[k][0] for k in h), min(boxes[k][1] for k in h),
                      max(boxes[k][2] for k in h), max(boxes[k][3] for k in h)]
                if (ba[0] - merge_gap < hb[2] and hb[0] - merge_gap < ba[2]
                        and ba[1] - merge_gap < hb[3] and hb[1] - merge_gap < ba[3]):
                    host_grp = h
                    break
            if host_grp is not None:
                host_grp += grp
            else:
                kept.append(grp)
        groups = kept

    items = []
    for grp in groups:
        m = np.isin(lab, grp)
        ys, xs = np.where(m)
        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        if (y1 - y0) < min_side and (x1 - x0) < min_side:
            continue
        a0, b0 = max(0, y0 - PAD), max(0, x0 - PAD)
        a1, b1 = min(arr.shape[0], y1 + PAD), min(arr.shape[1], x1 + PAD)
        rgba = cut(arr[a0:a1, b0:b1], ~m[a0:a1, b0:b1])
        out = Image.fromarray(rgba, 'RGBA')
        if max_side and max(out.size) > max_side:
            s = max_side / max(out.size)
            out = out.resize((max(1, round(out.width * s)), max(1, round(out.height * s))), Image.LANCZOS)
        if colors:
            q = out.quantize(colors=colors, method=Image.FASTOCTREE)
            out = q.convert('RGBA') if 'transparency' not in q.info else q
        items.append((out, len(ys)))
    items.sort(key=lambda t: -t[1])
    return im, items


def contact_sheet(items, path, cols=6, cell=190):
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * cell), (247, 247, 247))
    d = ImageDraw.Draw(sheet)
    for i, (im, area) in enumerate(items):
        s = min((cell - 30) / im.width, (cell - 30) / im.height)
        t = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        cx, cy = (i % cols) * cell, (i // cols) * cell
        sheet.paste(t, (cx + (cell - t.width) // 2, cy + (cell - t.height) // 2), t)
        d.rectangle([cx, cy, cx + cell - 1, cy + cell - 1], outline=(210, 210, 210))
        d.text((cx + 6, cy + cell - 18), '#%02d %dx%d' % (i + 1, im.width, im.height), fill=(90, 90, 90))
    sheet.save(path)
    print('  sheet ->', path, sheet.size, '共', len(items), '个')
    return rows


def save_items(items, pattern):
    tot = 0
    names = []
    for i, (im, _area) in enumerate(items):
        p = pattern % (i + 1)
        im.save(p, optimize=True)
        names.append(os.path.basename(p))
        tot += os.path.getsize(p)
    print('  写出 %d 个（%s … %s）  %.0f KB' % (len(items), names[0], names[-1], tot / 1024))
    return tot


# ---------------------------------------------------------------- cork
def make_cork(src, dst, size=(1180, 760), desat=.10, light=1.00,
              tint=(246, 226, 222), tint_amt=.12, blur=1.0):
    """软木板贴图。

    原图是偏橘的原色软木，直接贴上会和站点的淡粉（--paper #fdeef1）打架，
    所以降一点饱和度、提一点亮，再往暖粉的方向兑一笔，才像「同一套配色里的板子」。
    裁成横构图给 background-size: cover 用 —— 平铺会在墙上露出接缝。
    收尾加一道很轻的高斯：一是软木本该是绒的，二是把麦粒噪点抹掉一点，
    JPEG 才压得下来（不糊的话同一张要 300KB，糊到 1px 就只要 160KB，肉眼看不出差别）。
    """
    im = Image.open(src).convert('RGB')
    w, h = im.size
    tw, th = size
    ar = tw / th
    if w / h > ar:
        cw, ch = int(h * ar), h
    else:
        cw, ch = w, int(w / ar)
    im = im.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2))
    im = im.resize((tw, th), Image.LANCZOS)

    a = np.asarray(im).astype(np.float32)
    g = a.mean(2, keepdims=True)
    a = a * (1 - desat) + g * desat                     # 降饱和
    a = a * light                                       # 提亮
    a = a * (1 - tint_amt) + np.array(tint, np.float32) * tint_amt
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if blur:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    out.save(dst, quality=80, optimize=True)
    print('  cork ->', dst, out.size, '%.0f KB' % (os.path.getsize(dst) / 1024))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sheet-only', action='store_true')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs('shots', exist_ok=True)

    if not args.sheet_only:
        print('毛毡板：')
        make_cork(os.path.join(SRC, '毛毡板.jpg'), os.path.join(OUT, 'cork.jpg'))

        print('篮子：')
        _, items = extract(os.path.join(SRC, '篮子.jpg'), 'light', 242,
                           min_area=6000, min_side=60)
        if items:
            b = items[0][0]
            if b.height > 460:
                s = 460 / b.height
                b = b.resize((round(b.width * s), 460), Image.LANCZOS)
            # 页面上只显示到 ~132px 宽，再留着 599 宽就是白烧流量；配色也简单，压到 96 色
            b = b.quantize(colors=96, method=Image.FASTOCTREE).convert('RGBA')
            b.save(os.path.join(OUT, 'basket.png'), optimize=True)
            print('  basket.png', b.size, '%.0f KB' % (os.path.getsize(os.path.join(OUT, 'basket.png')) / 1024))
        contact_sheet(items[:8], 'shots/felt-basket.png')

        # 「装饰.jpg」= Y2K 小物（相机 / iPod / 拓麻歌子 / 星星 / CD …），白底
        print('装饰素材 Y2K 小物：')
        _, tr = extract(os.path.join(SRC, '装饰.jpg'), 'light', 240,
                        min_area=1600, merge_gap=18, merge_ratio=0.08,
                        merge_inside=True, max_side=200, colors=128)
        save_items(tr, os.path.join(OUT, 'trinket-%02d.png'))
        contact_sheet(tr, 'shots/felt-trinkets.png')

        # 「装饰素材.jpg」= 长尾夹 / 别针 / 图钉，黑底。
        # 这张图排得很密，不做邻近合并（一合就把旁边的别针也吞进来）；
        # merge_inside 负责把裂成两半的金色别针、漏下来的细边合回去。
        print('装饰 夹子别针：')
        _, cl = extract(os.path.join(SRC, '装饰素材.jpg'), 'dark', 58,
                        min_area=5200, min_side=46, merge_inside=True,
                        max_side=200, colors=128)
        save_items(cl, os.path.join(OUT, 'clip-%02d.png'))
        contact_sheet(cl, 'shots/felt-clips.png')

    tot = sum(os.path.getsize(f) for f in glob.glob(os.path.join(OUT, '*.png')))
    print('assets/felt png 合计 %.2f MB' % (tot / 1048576))


if __name__ == '__main__':
    main()
