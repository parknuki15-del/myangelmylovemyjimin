#!/usr/bin/env python3
"""
把云端导出的留言 JSON 变成网站上用的静态存档文件 assets/messages-saved.js。

为什么需要这一步：
  云开发环境到期停服之后，页面连不上云端 → 会退回「本机模式」，
  那时候访客只能看到自己浏览器里存的纸条，别人写的全看不见。
  所以要在环境还活着的时候，把纸条抓下来做成一份**静态快照**，
  跟网站一起发布。这样即使后端彻底没了，这些字也还在页面上。

用法：
  # 1. 先导出（环境活着才能导）
  node ~/.workbuddy/binaries/node/workspace/export_msg.mjs /tmp/messages-export.json

  # 2. 再生成存档
  /Users/whitekunckles/.workbuddy/binaries/python/envs/default/bin/python build_save_messages.py /tmp/messages-export.json

生成物 assets/messages-saved.js 里只有 name / text / time 三个字段 ——
不带 user_id、不带 id，谁写的归属信息不落到公开文件里。
"""
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'assets', 'messages-saved.js')

src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/messages-export.json'
if not os.path.exists(src):
    sys.exit('找不到导出文件：' + src)

raw = json.load(open(src, encoding='utf-8'))
rows = raw.get('rows') or raw.get('data') or []
if not isinstance(rows, list) or not rows:
    sys.exit('导出文件里没有纸条')

# 只留要展示的三样；按写入时间正序（页面上再倒序渲染）
clean = []
for r in rows:
    text = (r.get('text') or '').strip()
    if not text:
        continue
    clean.append({
        'name': (r.get('name') or '').strip()[:20],
        'text': text[:300],
        'time': (r.get('time') or '').strip(),
    })

clean.sort(key=lambda x: x['time'])          # "YYYY-MM-DD HH:MM" 直接按字符串比就是对的

payload = {
    'savedAt': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'envId': raw.get('envId') or '',
    'count': len(clean),
    'rows': clean,
}

body = json.dumps(payload, ensure_ascii=False, indent=1)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('/* 留言板静态存档 —— 由 build_save_messages.py 生成，别手改。\n'
            '   快照时间：%s，共 %d 张。\n'
            '   页面上只要 window.MSG_SAVED 在，就能在没后端的情况下把纸条画出来。 */\n'
            'window.MSG_SAVED = ' % (payload['savedAt'], payload['count']))
    f.write(body)
    f.write(';\n')

print('已生成 %s' % OUT)
print('  快照时间 %s' % payload['savedAt'])
print('  纸条 %d 张（%s → %s）' % (len(clean), clean[0]['time'], clean[-1]['time']))
print('  体积 %.1f KB' % (os.path.getsize(OUT) / 1024))
