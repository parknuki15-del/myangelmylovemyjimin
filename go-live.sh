#!/usr/bin/env bash
# ============================================================
#  go-live.sh —— 把改动推到 GitHub，让网站更新
#
#  和 publish.sh 的分工：
#     publish.sh  从零开始（建仓库、挂 remote、首次推送）—— 只用一次
#     go-live.sh  仓库已经配好了，以后每次改完点这个 —— 日常用
#
#  用法：
#      cd "/Users/whitekunckles/Desktop/朴智旻造型/myangelmylovemyjimin"
#      bash go-live.sh            # 自检 + 提交 + 推送
#      bash go-live.sh --check    # 只自检，不提交不推送（先看看有没有问题）
#
#  推送时会要账号密码：用户名填 parknuki15-del，
#  密码**不能填登录密码**，要填 Personal Access Token（见文末）。
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

REPO_URL="$(git remote get-url origin 2>/dev/null || echo '')"
if [ -z "$REPO_URL" ]; then
  echo "✗ 这个目录还没挂 remote。先跑一次： bash publish.sh parknuki15-del"
  exit 1
fi
# 从 remote 反推用户名 / 仓库名，这样以后改仓库名也不用改脚本
GH_PATH="$(printf '%s' "$REPO_URL" | sed -E 's#.*github\.com[:/]##; s#\.git$##')"
GH_USER="${GH_PATH%%/*}"
GH_REPO="${GH_PATH##*/}"

echo "▶ 1/5 仓库"
echo "    remote : $REPO_URL"
echo "    分支   : $(git rev-parse --abbrev-ref HEAD)"
echo "    提交数 : $(git rev-list --count HEAD)"

echo "▶ 2/5 页面引用的资源是否都在仓库里"
if ! command -v python3 >/dev/null 2>&1; then
  echo "    (没装 python3，跳过这项检查 —— 不影响推送)"
else
python3 - <<'PY' || exit 1
import re, os, subprocess, sys
tracked = set(subprocess.run(['git','ls-files'], capture_output=True, text=True).stdout.split('\n'))
refs = set()
for f in ('index.html', 'assets/data.js'):
    if os.path.exists(f):
        t = open(f, encoding='utf-8', errors='ignore').read()
        refs |= set(re.findall(r'assets/[A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg|gif|webp|svg|woff2?|ttf|otf|mp3|json|css|js)', t))
missing  = sorted(r for r in refs if not os.path.exists(r))
ignored  = sorted(r for r in refs if os.path.exists(r) and r not in tracked)
if missing:
    print(f"    ✗ 有的文件磁盘上就没有：{missing[:5]} —— 先把素材补齐再推")
    sys.exit(1)
if ignored:
    print(f"    ! 这些文件不在仓库里（线上会 404）：{ignored}")
    print("      assets/promise.mp3 是版权歌曲，故意不放 —— 线上唱片按钮会自动隐藏，属正常。")
else:
    print("    ✓ 全部齐全")
PY
fi

echo "▶ 3/5 关键文件"
for f in index.html CNAME .nojekyll; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then echo "    ✓ $f"; else echo "    ✗ $f 没进仓库（Pages 会出问题）"; fi
done
echo "    CNAME 内容: $(cat CNAME 2>/dev/null | tr -d '\n')"

echo "▶ 4/5 能不能连上 GitHub"
if curl -sI -m 10 https://github.com >/dev/null 2>&1; then
  echo "    ✓ 通"
else
  echo "    ✗ 连不上 github.com"
  echo "      国内网络常年抽风，试这些："
  echo "        · 换个网络 / 开代理再跑"
  echo "        · hosts 加速：见 README 的「部署」一节"
  echo "        · 或者改用 Cloudflare Pages（自定义域名同样不带第三方标识）"
  echo "      本次到此为止。"
  exit 1
fi

if [ "$CHECK_ONLY" = "1" ]; then
  echo "▶ 5/5 --check 模式，不提交不推送。自检全部通过 ✓"
  exit 0
fi

echo "▶ 5/5 提交 + 推送"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  echo "    本次提交 $(git diff --cached --name-only | wc -l | tr -d ' ') 个文件"
  git commit -q -m "update: $(date '+%Y-%m-%d %H:%M')"
else
  echo "    没有新改动，只推送已有提交"
fi

git push -u origin "$(git rev-parse --abbrev-ref HEAD)" || {
  echo
  echo "✗ 推送失败。最常见的原因是认证："
  echo "   用户名 : ${GH_USER}"
  echo "   密码   : 不能填登录密码，要填 Personal Access Token"
  echo "            生成地址 https://github.com/settings/tokens  →  Generate new token (classic)"
  echo "            勾选 repo ，有效期选长一点，生成后**立刻复制**（只显示一次）"
  echo
  echo "  更省事的办法用 SSH（配一次，以后不再要 token）："
  echo "    ssh-keygen -t ed25519 -C \"parknuki15-del@users.noreply.github.com\""
  echo "    pbcopy < ~/.ssh/id_ed25519.pub     # 然后粘到 https://github.com/settings/keys"
  echo "    git remote set-url origin git@github.com:${GH_USER}/${GH_REPO}.git"
  echo "    ssh -T git@github.com              # 出现 Hi ${GH_USER}! 就成功了"
  exit 1
}

cat <<EOF

============================================================
✅ 推上去了。剩下的是网页上点几下（只需做一次）：

【1】开 Pages
    https://github.com/${GH_USER}/${GH_REPO}/settings/pages
    Source 选 "Deploy from a branch"
    Branch 选 main，目录 / (root)，Save
    等 1~2 分钟，先拿到默认地址试试：
    https://${GH_USER}.github.io/${GH_REPO}/

【2】去域名商加记录（阿里云 / 腾讯云 / Cloudflare 都行）
    myangelmylovemyjimin.com 这个域名下加：

    类型     主机记录   记录值
    A        @          185.199.108.153
    A        @          185.199.109.153
    A        @          185.199.110.153
    A        @          185.199.111.153
    CNAME    www        ${GH_USER}.github.io

【3】回到 Pages 设置
    Custom domain 填 myangelmylovemyjimin.com → Save
    （仓库根已经有 CNAME 文件，通常会自动填上）

【4】等 DNS 生效（最快几分钟，最长 24 小时）
    生效后把 "Enforce HTTPS" 勾上
    最终网址：  https://myangelmylovemyjimin.com/

以后改完内容，只要再跑一次  bash go-live.sh  就更新了。
============================================================
EOF
