#!/usr/bin/env bash
# ============================================================
#  add-music.sh —— 给网站加背景音乐（本地能放，线上也能放）
#
#  用法：
#      cd "/Users/whitekunckles/Desktop/朴智旻造型/myangelmylovemyjimin"
#      bash add-music.sh "/路径/你想用的歌.mp3"
#
#  它会做四件事：
#      1. 检查这个文件是不是真的音频、多长、多大（太大给你提个醒）
#      2. 拷到 assets/promise.mp3（文件名保持不变，index.html 不用改）
#      3. 把 .gitignore 里排除 mp3 的那一行删掉
#      4. 提交 —— 然后你跑 bash go-live.sh 就上线了
#
#  ⚠️ 跑之前先读一遍下面的版权提醒，脚本也会再问你一次。
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

if [ "${1:-}" = "" ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

SRC="$1"
TARGET="assets/promise.mp3"

echo "▶ 1/4 检查音频文件"
if [ ! -f "$SRC" ]; then
  echo "    ✗ 找不到文件：$SRC"
  echo "      （路径里有空格的话要用引号包起来）"
  exit 1
fi

case "$(printf '%s' "$SRC" | tr 'A-Z' 'a-z')" in
  *.mp3|*.m4a|*.aac|*.ogg|*.oga|*.wav|*.flac) : ;;
  *) echo "    ! 扩展名看起来不是音频，还是我判断错了？继续之前先确认一下。"; ;;
esac

SIZE=$(wc -c < "$SRC" | tr -d ' ')
printf "    文件 : %s\n" "$(basename "$SRC")"
printf "    大小 : %s\n" "$(echo "$SIZE" | awk '{printf "%.2f MB", $1/1048576}')"

if command -v ffprobe >/dev/null 2>&1; then
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC" 2>/dev/null | cut -d. -f1)
  BR=$(ffprobe -v error -show_entries format=bit_rate -of csv=p=0 "$SRC" 2>/dev/null)
  if [ -n "${DUR:-}" ]; then
    printf "    时长 : %d 分 %d 秒\n" $((DUR/60)) $((DUR%60))
    [ -n "${BR:-}" ] && printf "    码率 : %d kbps\n" $((BR/1000))
    if [ "$DUR" -gt 330 ]; then
      echo "    ! 超过 5 分半了。网页 BGM 建议 2~3 分钟循环，太长的首屏要多等一会儿。"
    fi
  fi
  # 确认它真的是一路音频流
  if ! ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$SRC" 2>/dev/null | grep -q audio; then
    echo "    ✗ 这个文件里没有音频流，换一个吧。"
    exit 1
  fi
else
  echo "    (没装 ffprobe，跳过时长/码率检查 —— 不影响后面)"
fi

if [ "$SIZE" -gt 4194304 ]; then
  echo "    ! 超过 4 MB。建议压一下再放（单声道 64~96 kbps 就够了，听感几乎没差）："
  echo "      ffmpeg -i \"$SRC\" -ac 1 -b:a 80k assets/promise.mp3"
fi

echo
echo "────────────────────────────────────────────────────────"
echo "⚠️  版权提醒（看清楚再决定）"
echo
echo "  把一首商业歌曲放进公开仓库，等于在公开分发它。"
echo "  一旦被 BIGHIT / HYBE 之类投诉，GitHub 处理的是**整个 Pages 站点**："
echo "  不是只删掉那个 mp3，而是站直接打不开；账号还会吃一次 strike（累计会封号）。"
echo
echo "  想完全没这个风险，就用免费可商用的音乐，比如："
echo "    · Pixabay Music      https://pixabay.com/music/     （免署名，最好用）"
echo "    · Free Music Archive https://freemusicarchive.org/"
echo "    · YouTube 音频库      https://studio.youtube.com/    （需 Google 账号）"
echo "  找氛围的话搜这几个词：music box / lullaby / soft piano / birthday"
echo "────────────────────────────────────────────────────────"
read -rp "了解风险，继续？(输入 yes 继续，其它任意键取消) " ans
if [ "$ans" != "yes" ]; then
  echo "已取消，什么都没改。"
  exit 0
fi

echo
echo "▶ 2/4 放进 assets/"
mkdir -p assets
if [ -f "$TARGET" ] && ! cmp -s "$SRC" "$TARGET"; then
  cp "$TARGET" "$TARGET.bak" && echo "    旧的 $TARGET 备份成 $TARGET.bak"
fi
cp "$SRC" "$TARGET"
echo "    ✓ $TARGET  ($(echo "$SIZE" | awk '{printf "%.2f MB", $1/1048576}'))"

echo "▶ 3/4 放行 .gitignore"
if grep -q "assets/promise.mp3" .gitignore 2>/dev/null; then
  # 只删那一行，注释保留（注释解释了为什么当初不放）
  grep -v "^assets/promise.mp3$" .gitignore > .gitignore.tmp && mv .gitignore.tmp .gitignore
  echo "    ✓ 已删掉排除规则"
else
  echo "    (本来就没排除，跳过)"
fi

echo "▶ 4/4 提交"
git add -A
if git diff --cached --quiet; then
  echo "    没有变化，跳过"
else
  git commit -q -m "加入背景音乐（$(basename "$SRC")）"
  echo "    ✓ 已提交"
fi

cat <<EOF

============================================================
下一步：  bash go-live.sh      把它推上线（1~2 分钟后生效）

顺便说几件事：
 · 播放时机：点 "Open the Gift ♡" 那一下才开始放（浏览器不允许页面一打开
   就自动出声），右下角会冒出一个 ♪ 唱片按钮，点它可以暂停/继续。
 · 换歌：再跑一次这个脚本就行，旧文件会备份成 assets/promise.mp3.bak。
 · 想改回"线上不放音乐"：把 .gitignore 里这行加回去，再 go-live.sh —
       assets/promise.mp3
   线上就会恢复成没有 ♪ 按钮的干净版本。
 · 每次换歌 git 历史都会多留一份旧文件（约 1 MB），换很多次后想瘦身：
       git gc --aggressive --prune=now
============================================================
EOF
