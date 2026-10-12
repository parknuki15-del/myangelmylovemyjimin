#!/usr/bin/env python3
"""
把网站上用的字体从 Google Fonts 抓下来自托管（国内不翻墙也能正常显示）。

为什么不能直接下整包：
  ZCOOL KuaiLe 是**中文字体**，完整 TTF 有 1.4 MB、9 万多个字形，
  而站内真正用到的汉字只有两三百个。所以这里做**子集化**：
  只保留「站内出现过的字」+「GB2312 一级字库（3755 个常用字）」，
  体积能压到几十 KB，而且留言板里用户自己打的常用字也覆盖得到。

用法：
    /Users/whitekunckles/.workbuddy/binaries/python/envs/default/bin/python build_fonts.py

改了 index.html 里的文案之后重跑一遍即可。
"""
import hashlib
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'assets', 'fonts')
UA_MODERN = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
UA_OLD = 'Mozilla/4.0'          # 老 UA 才会返回整包 TTF，而不是 woff2 分包

# 站内实际用到的字体族（Caveat Brush / Kalam 全站 0 引用，已删掉不再下载）
LATIN_FAMILIES = [('Caveat', '500;700'), ('Gochi Hand', '400')]


def fetch(url, ua=UA_MODERN):
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def used_characters():
    """站内出现过的所有字符（把 JS 字符串也算上，宁多勿少）"""
    chars = set()
    for name in ('index.html', os.path.join('assets', 'data.js')):
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            chars |= set(open(p, encoding='utf-8').read())
    # ASCII 可打印 + 常用标点
    chars |= set(chr(c) for c in range(0x20, 0x7F))
    chars |= set('　、。〈〉《》「」『』【】〔〕・ー—–…‘’“”′″¥€£°±×÷≈≠≤≥←→↑↓♡♥★☆❀✿❁✾❋✽💜')
    return chars


def gb2312_level1():
    """GB2312 一级字库，3755 个最常用汉字 —— 覆盖留言板里用户随手打的字"""
    out = set()
    for hi in range(0xB0, 0xD8):
        for lo in range(0xA1, 0xFF):
            try:
                out.add(bytes([hi, lo]).decode('gb2312'))
            except UnicodeDecodeError:
                pass
    return out


def parse_css_blocks(css):
    """把 @font-face 拆成 dict，方便按 unicode-range 挑「latin」那一份"""
    blocks = []
    for m in re.finditer(r'@font-face\s*\{(.*?)\}', css, re.S):
        body = m.group(1)
        d = {}
        for k, v in re.findall(r'([a-z-]+)\s*:\s*([^;]+);', body):
            d[k.strip()] = v.strip()
        blocks.append(d)
    return blocks


def build_latin():
    """挑「latin」那一份子集下载。同一个 URL 被多个字重共用 = 可变字体，只存一份。"""
    by_url = {}
    query = '&'.join('family=' + f.replace(' ', '+') + ':wght@' + w
                     for f, w in LATIN_FAMILIES)
    css = fetch('https://fonts.googleapis.com/css2?%s&display=swap' % query).decode()
    for d in parse_css_blocks(css):
        fam = d.get('font-family', '').strip("'\"")
        weight = d.get('font-weight', '400')
        ur = d.get('unicode-range', '')
        # latin 子集的特征是覆盖到 U+0000-00FF
        if 'U+0000-00FF' not in ur and 'U+0000-00ff' not in ur.lower():
            continue
        m = re.search(r'url\((https://[^)]+)\)', d.get('src', ''))
        if not m:
            continue
        url = m.group(1)
        # 文件名只用族名；可变字体就一个文件管多个字重，不带字重后缀
        slug = fam.lower().replace(' ', '-')
        by_url.setdefault(url, {'fam': fam, 'slug': slug, 'weights': []})
        by_url[url]['weights'].append(weight)

    made = []
    for url, info in by_url.items():
        data = fetch(url)
        size = len(data)
        # 同一个文件被多个字重引用，且只有一个 woff2 → 可变字体，只落一份
        variable = size > 60000 and len(info['weights']) > 1
        name = ('%s.woff2' % info['slug']) if variable else \
               ('%s-%s.woff2' % (info['slug'], info['weights'][0]))
        with open(os.path.join(OUT, name), 'wb') as f:
            f.write(data)
        ws = sorted(int(w) for w in info['weights'])
        made.append((info['fam'], ws[0] if len(ws) == 1 else '%d %d' % (ws[0], ws[-1]), name))
        print('  ✔ %-14s %-8s → %s (%d KB)'
              % (info['fam'], made[-1][1], name, size // 1024))
    # 去重：同样的文件被写了两次就删掉多余那份
    seen = {}
    for root, _, files in os.walk(OUT):
        for f in files:
            if not f.endswith('.woff2'):
                continue
            p = os.path.join(root, f)
            h = hashlib.md5(open(p, 'rb').read()).hexdigest()
            if h in seen and seen[h] != f:
                os.remove(p)
                print('  (去重删掉了重复的 %s)' % f)
            else:
                seen[h] = f
    return made


def build_cjk():
    print('  · 拉 ZCOOL KuaiLe 整包 TTF …')
    ttf = fetch('https://fonts.gstatic.com/s/zcoolkuaile/v22/tssqApdaRQokwFjFJjvM6h2Wpg.ttf',
                ua=UA_OLD)
    tmp = os.path.join(OUT, '_zcool-full.ttf')
    with open(tmp, 'wb') as f:
        f.write(ttf)
    print('    整包 %d KB' % (len(ttf) // 1024))

    chars = used_characters() | gb2312_level1()
    print('  · 子集字符数 %d（站内用字 + GB2312 一级字库）' % len(chars))

    dst = os.path.join(OUT, 'zcool-kuaile-400.woff2')
    subprocess.run([
        sys.executable, '-m', 'fontTools.subset', tmp,
        '--text=' + ''.join(sorted(chars)),
        '--flavor=woff2',
        '--layout-features=*',
        '--desubroutinize',
        '--no-hinting',
        '--output-file=' + dst,
    ], check=True)
    os.remove(tmp)
    size = os.path.getsize(dst)
    print('  ✔ ZCOOL KuaiLe 子集 → %s (%d KB)' % (os.path.basename(dst), size // 1024))
    return dst, size


def write_css(latin, cjk_ok):
    lines = ['/* 自托管字体 —— 由 build_fonts.py 生成，不要手改 */', '']
    for fam, weight, name in latin:
        lines += [
            '@font-face {',
            "  font-family: '%s';" % fam,
            '  font-style: normal;',
            '  font-weight: %s;' % weight,
            '  font-display: swap;',
            "  src: url('./%s') format('woff2');" % name,
            '}',
            '',
        ]
    if cjk_ok:
        lines += [
            '@font-face {',
            "  font-family: 'ZCOOL KuaiLe';",
            '  font-style: normal;',
            '  font-weight: 400;',
            '  font-display: swap;',
            "  src: url('./zcool-kuaile-400.woff2') format('woff2');",
            '}',
            '',
        ]
    with open(os.path.join(OUT, 'fonts.css'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('  ✔ fonts.css 已生成')


def main():
    os.makedirs(OUT, exist_ok=True)
    print('▶ 拉丁字体（只挑 latin 子集）')
    latin = build_latin()
    print('▶ 中文标题字体（ZCOOL KuaiLe，子集化）')
    _, cjk_size = build_cjk()
    write_css(latin, cjk_size > 0)
    print('\n完成。去看 assets/fonts/ 目录，总大小：%d KB'
          % (sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)
                 if not f.startswith('_')) // 1024))


if __name__ == '__main__':
    main()
