#!/usr/bin/env bash
# ============================================================
#  一键把「A Gift for Jimin」推上 GitHub
#
#  用法（在你自己的终端里跑，不是在这里）：
#      cd "/Users/whitekunckles/WorkBuddy/2026-10-08-20-02-18/birthday-site"
#      bash publish.sh 你的GitHub用户名
#
#  例：
#      bash publish.sh parknuki
#
#  仓库名默认就是 myangelmylovemyjimin —— 它决定网址：
#      https://你的用户名.github.io/myangelmylovemyjimin/
#
#  ⚠️ 事先要在 GitHub 网页上先建好同名空仓库（不要勾 README/gitignore/license）。
# ============================================================
set -euo pipefail

GH_USER="${1:-}"
REPO="${2:-myangelmylovemyjimin}"

if [ -z "$GH_USER" ]; then
  echo "用法: bash publish.sh <你的GitHub用户名> [仓库名]"
  echo "例:   bash publish.sh parknuki"
  echo "      bash publish.sh parknuki myangelmylovemyjimin   # 默认就是这个名字"
  exit 1
fi

cd "$(dirname "$0")"

echo "▶ 1/6 提交者身份（只写进这个仓库的 .git/config，不动全局设置）"
git config user.name  "$GH_USER"
git config user.email "${GH_USER}@users.noreply.github.com"

echo "▶ 2/6 初始化仓库（主分支叫 main）"
if [ ! -d .git ]; then
  git init -b main
else
  echo "   已经是 git 仓库了，跳过"
fi

echo "▶ 3/6 暂存文件"
git add -A
echo "   将提交 $(git diff --cached --name-only | wc -l | tr -d ' ') 个文件"

echo "▶ 4/6 提交"
if git diff --cached --quiet; then
  echo "   没有新改动，跳过提交"
  # 首次提交是用占位身份建的，把作者改成你自己，这样才会算到你 GitHub 账号头上
  if [ "$(git log -1 --format=%ae 2>/dev/null || true)" = "parknuki@users.noreply.github.com" ] \
     && [ "$GH_USER" != "parknuki" ]; then
    git commit --amend --reset-author --no-edit
    echo "   已把首个提交的作者改成 ${GH_USER}"
  fi
else
  git commit -m "A Gift for Jimin — 手账剪贴簿风格生日应援页"
fi

echo "▶ 5/6 挂远程"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GH_USER}/${REPO}.git"

echo "▶ 6/6 推送（会让你输用户名 + Personal Access Token 当密码）"
git push -u origin main

cat <<EOF

============================================================
✅ 推完了。接下来开 Pages + 绑域名：

【第 1 步】开 Pages
   1. 打开  https://github.com/${GH_USER}/${REPO}/settings/pages
   2. Source 选  "Deploy from a branch"
   3. Branch 选  main ，目录选  / (root) ，点 Save
   4. 现在就有默认地址了：
      https://${GH_USER}.github.io/${REPO}/

【第 2 步】去域名商（阿里云 / 腾讯云 / Namecheap / Cloudflare…）
   给 myangelmylovemyjimin.com 加下面这些记录：

   类型    主机记录   记录值
   A       @          185.199.108.153
   A       @          185.199.109.153
   A       @          185.199.110.153
   A       @          185.199.111.153
   AAAA    @          2606:50c0:8000::153
   AAAA    @          2606:50c0:8001::153
   AAAA    @          2606:50c0:8002::153
   AAAA    @          2606:50c0:8003::153
   CNAME   www        ${GH_USER}.github.io

【第 3 步】回到 Pages 设置
   Custom domain 里填  myangelmylovemyjimin.com ，点 Save
   （仓库根的 CNAME 文件已经建好了，这里通常会自动填上）

【第 4 步】等
   DNS 生效最长 24 小时。生效后把 "Enforce HTTPS" 勾上。
   最后网址就是：  https://myangelmylovemyjimin.com/

   想换网址 → 改仓库名或改 CNAME 文件 + 域名商记录即可。
============================================================
EOF
