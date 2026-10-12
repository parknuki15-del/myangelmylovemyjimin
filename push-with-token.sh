#!/usr/bin/env bash
# ============================================================
#  push-with-token.sh —— 绕开终端那个「粘不进去」的密码框
#
#  为什么会有这个脚本：
#    git 弹出的 `Password for 'https://...'` 那个框有三个坑：
#      1. 它**一个字符都不回显**（连星号都没有），所以你粘没粘上看不出来
#      2. macOS 终端在密码提示下经常真的把 Cmd+V 吃掉（右键→粘贴 常常才行）
#      3. 最要命的是：**GitHub 从 2021 年起就不接受登录密码了**，
#         那儿必须填 Personal Access Token。填登录密码，粘进去了也是 401。
#
#  所以别跟那个框较劲。这个脚本改成：
#    在**普通命令行**里让你粘（粘贴一定是好的、而且能看见粘进去没有）→
#    先拿 GitHub API 验一下这个 token 到底行不行 → 存进钥匙串 → 推送。
#    以后 git push 再也不用输密码。
#
#  用法：
#      cd "/Users/whitekunckles/Desktop/朴智旻造型/myangelmylovemyjimin"
#      bash push-with-token.sh
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

URL="$(git remote get-url origin 2>/dev/null || echo '')"
if [ -z "$URL" ]; then
  echo "✗ 这个目录没挂 remote。"
  exit 1
fi
GH_PATH="$(printf '%s' "$URL" | sed -E 's#.*github\.com[:/]##; s#\.git$##')"
GH_USER="${GH_PATH%%/*}"
GH_REPO="${GH_PATH##*/}"

if printf '%s' "$URL" | grep -q '@github.com'; then
  echo "! remote 里已经嵌了一次 token（上次那种写法留下的），先清干净："
  git remote set-url origin "https://github.com/${GH_USER}/${GH_REPO}.git"
  echo "    ✓ 已还原成 https://github.com/${GH_USER}/${GH_REPO}.git"
fi

cat <<'EOF'

────────────────────────────────────────────────────────────
先确认你手上有一个 Personal Access Token（不是登录密码）

  1. 打开  https://github.com/settings/tokens
  2. 点  Generate new token  →  Generate new token (classic)
  3. Note 随便写（例如 jimin-site）
     Expiration 选 90 days 或 No expiration
  4. **勾选最上面那个 `repo` 大项**（勾上父项，子项会全选）
  5. 拉到底点  Generate token
  6. 页面会冒出一串 `ghp_xxxxxxxxxxxx` —— **只显示这一次**，马上复制

  没有这串东西，光有 GitHub 密码是推不上去的。
────────────────────────────────────────────────────────────

EOF

read -rp "把 Token 粘到这里再按回车（会显示出来，好让你确认粘上了；别截图）:
> " TOKEN
TOKEN="$(printf '%s' "$TOKEN" | tr -d ' \t\n\r')"

if [ -z "$TOKEN" ]; then
  echo "✗ 没读到内容。可能是粘贴没进去 —— 试试点右键 → 粘贴，或菜单栏 编辑 → 粘贴。"
  exit 1
fi
echo "    读到 ${#TOKEN} 个字符"

case "$TOKEN" in
  ghp_*|github_pat_*) echo "    看起来是 GitHub Token ✓" ;;
  *)
    echo "    ! 它不以 ghp_ / github_pat_ 开头。"
    echo "      如果你粘的是 GitHub 登录密码：GitHub 早就不认了，一定会失败。"
    read -rp "      还是拿它试一次？(yes / 其它键取消) " a
    [ "$a" = "yes" ] || exit 1
    ;;
esac

echo
echo "▶ 1/3 拿 GitHub 接口验一下这个 token"
CODE="$(curl -s -o /tmp/_ghme.json -w '%{http_code}' -m 20 \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/user 2>/dev/null)"
case "$CODE" in
  200)
    LOGIN="$(sed -n 's/.*"login"[：: ]*"\([^"]*\)".*/\1/p' /tmp/_ghme.json | head -1)"
    echo "    ✓ token 有效，账号是：${LOGIN:-?}"
    ;;
  401) echo "    ✗ 401：token 不对、或者已经被撤销 / 过期。回第 1 步重新生成一个。"; rm -f /tmp/_ghme.json; exit 1 ;;
  403) echo "    ! 403：IP 被限流或者没权限，先换个网络再试。"; rm -f /tmp/_ghme.json; exit 1 ;;
  000) echo "    ✗ 连不上 api.github.com。网络问题，开个代理再跑。"; rm -f /tmp/_ghme.json; exit 1 ;;
  *)   echo "    ! 意外返回码 $CODE，继续往下试。";;
esac
rm -f /tmp/_ghme.json

echo "▶ 2/3 存进 macOS 钥匙串（以后 git push 不再问密码）"
git config --global credential.helper osxkeychain
printf 'protocol=https\nhost=github.com\nusername=%s\npassword=%s\n\n' "$GH_USER" "$TOKEN" \
  | git credential-osxkeychain store
echo "    ✓ 已保存（不想留就把全局配置里的 credential.helper 删掉）"

echo "▶ 3/3 推送"
if git push -u origin "$(git rev-parse --abbrev-ref HEAD)"; then
  cat <<EOF

============================================================
✅ 推上去了！语言都不用再输密码了。

接着开 Pages（点 2 下）：
  https://github.com/${GH_USER}/${GH_REPO}/settings/pages
     Source 选  Deploy from a branch
     Branch 选  main  ，目录选  / (root)  →  Save

1~2 分钟后先看默认地址通不通：
  https://${GH_USER}.github.io/${GH_REPO}/

然后去域名商加解析（这是最后一步）：
     类型    主机记录   记录值
     A       @          185.199.108.153
     A       @          185.199.109.153
     A       @          185.199.110.153
     A       @          185.199.111.153
     CNAME   www        ${GH_USER}.github.io

回 Pages 设置，Custom domain 填 myangelmylovemyjimin.com → Save，
等解析生效（几分钟到 24 小时）后勾上 Enforce HTTPS。
最终网址： https://myangelmylovemyjimin.com/
============================================================
EOF
else
  echo
  echo "✗ 还是没推上去。把上面整段报错复制给我，我看看卡在哪。"
  echo "  常见原因："
  echo "   · 远程仓库里已经有提交了（比如建仓库时勾了 README）→ 需要先合并："
  echo "       git pull --rebase origin main   然后再推"
  echo "   · token 没勾 repo 权限 → 重新生成一个"
fi
