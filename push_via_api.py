#!/usr/bin/env python3
"""用 GitHub API 推送（git push 在这个沙箱里走不通：github.com 网页域 CONNECT 502，
只有 api.github.com 能连）。思路：拿「本地文件内容的 git blob 哈希」跟「远程 tree 里的
哈希」比，只把真变了的文件传上去，再在远程 main 上新建一个 commit。

好处：不依赖本地 ref 是否跟远程同步 —— 之前用 API 建的 commit 本地没有对象，
直接 git push 会炸，这个脚本不受影响。

用法：
    /Users/whitekunckles/.workbuddy/binaries/python/envs/default/bin/python push_via_api.py "提交说明"

token 从 macOS 钥匙串现取（git credential-osxkeychain），脚本本身不含任何密钥。
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = 'parknuki15-del/myangelmylovemyjimin'
BRANCH = 'main'
API = 'https://api.github.com'

MSG = sys.argv[1] if len(sys.argv) > 1 else '更新（push_via_api.py 无说明提交）'


def get_token():
    out = subprocess.run(
        ['git', 'credential-osxkeychain', 'get'],
        input=b'protocol=https\nhost=github.com\n\n',
        capture_output=True, cwd=ROOT).stdout.decode()
    for line in out.splitlines():
        if line.startswith('password='):
            return line[len('password='):].strip()
    sys.exit('取不到 GitHub token（钥匙串里没有 github.com 的凭据）')


TOK = get_token()


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        API + path, data=data, method=method,
        headers={'Authorization': 'Bearer ' + TOK,
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json',
                 'User-Agent': 'push-script'})
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit('%s %s -> HTTP %s\n%s' % (method, path, e.code, e.read().decode()[:800]))


head = req('GET', '/repos/%s/git/ref/heads/%s' % (REPO, BRANCH))['object']['sha']
remote_tree = req('GET', '/repos/%s/git/trees/%s?recursive=1' % (REPO, head))
remote = {e['path']: e['sha'] for e in remote_tree.get('tree', []) if e['type'] == 'blob'}
print('远程 %s @ %s（%d 个文件）' % (BRANCH, head[:10], len(remote)))

# 本地文件清单走 git（自动遵守 .gitignore —— assets/promise.mp3 这类不该进仓库的不会被带上）
out = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                     cwd=ROOT, capture_output=True).stdout.decode()
paths = [p for p in out.splitlines() if p.strip()]

changed, added, same = [], [], 0
for rel in paths:
    full = os.path.join(ROOT, rel)
    if not os.path.isfile(full):
        continue
    sha = subprocess.run(['git', 'hash-object', full], cwd=ROOT,
                         capture_output=True).stdout.decode().strip()
    if not sha:
        continue
    if rel not in remote:
        added.append((rel, sha))
    elif remote[rel] != sha:
        changed.append((rel, sha))
    else:
        same += 1

print('未变 %d 个 / 改动 %d 个 / 新增 %d 个' % (same, len(changed), len(added)))
for p, _ in changed:
    print('  M ' + p)
for p, _ in added:
    print('  + ' + p)

if not changed and not added:
    print('没有要推的东西，收工')
    sys.exit(0)

entries = []
for rel, _ in changed + added:
    with open(os.path.join(ROOT, rel), 'rb') as fh:
        content = base64.b64encode(fh.read()).decode()
    b = req('POST', '/repos/%s/git/blobs' % REPO, {'content': content, 'encoding': 'base64'})
    entries.append({'path': rel, 'mode': '100644', 'type': 'blob', 'sha': b['sha']})
    print('  blob ✓ ' + rel)

tree = req('POST', '/repos/%s/git/trees' % REPO, {'base_tree': remote_tree['sha'], 'tree': entries})
commit = req('POST', '/repos/%s/git/commits' % REPO,
             {'message': MSG, 'tree': tree['sha'], 'parents': [head]})
req('PATCH', '/repos/%s/git/refs/heads/%s' % (REPO, BRANCH), {'sha': commit['sha'], 'force': False})

print('\n✅ 已推送 %s' % commit['sha'])
print('   新 tree %s' % tree['sha'])
