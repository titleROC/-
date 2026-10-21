#!/usr/bin/env bash
# 检查上游 YLXDXX/gaokao-physics-archive 的最新提交是否有「LaTeX源码/」里还没有的试卷，
# 用来发现缺卷（如 2026 年天津、安徽、江西、福建卷）何时被上游补上。只读，不改动本仓库。
#
# 用法：
#   scripts/check_upstream.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 退出状态：0 = 没有新卷；2 = 上游有新卷（同时打印同步和编译命令）；其他 = 出错。
#
# 环境变量：
#   ARCHIVE_DIR   上游仓库的本地克隆位置（默认 ./.cache/gaokao-physics-archive，与 sync_latex_sources.sh 共用）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ARCHIVE_URL="https://github.com/YLXDXX/gaokao-physics-archive.git"
ARCHIVE_DIR="${ARCHIVE_DIR:-$REPO_ROOT/.cache/gaokao-physics-archive}"
SRC="$REPO_ROOT/LaTeX源码"

if [ ! -d "$ARCHIVE_DIR/.git" ]; then
  git clone --quiet "$ARCHIVE_URL" "$ARCHIVE_DIR"
fi
# 取上游默认分支的最新提交（FETCH_HEAD），不切换上游克隆的工作区
git -C "$ARCHIVE_DIR" fetch --quiet origin HEAD
rev="$(git -C "$ARCHIVE_DIR" rev-parse FETCH_HEAD)"
echo "上游最新提交：$(git -C "$ARCHIVE_DIR" log -1 --format='%h %cs %s' "$rev")"

new=()
for year in $(seq "$FROM" "$TO"); do
  git -C "$ARCHIVE_DIR" cat-file -e "$rev:试卷/$year" 2>/dev/null || continue
  while IFS= read -r region; do
    [ -f "$SRC/$year/$region/Makefile" ] || new+=("$year/$region")
  done < <(git -C "$ARCHIVE_DIR" -c core.quotepath=off ls-tree -d --name-only "$rev:试卷/$year")
done

if [ "${#new[@]}" -eq 0 ]; then
  echo "$FROM—$TO 年没有 LaTeX源码/ 之外的新卷"
  exit 0
fi
echo "上游有 ${#new[@]} 套 LaTeX源码/ 里没有的试卷："
printf '  %s\n' "${new[@]}"
years="$(printf '%s\n' "${new[@]}" | cut -d/ -f1 | sort -u)"
y1="$(head -n1 <<<"$years")"
y2="$(tail -n1 <<<"$years")"
echo "同步并编译（之后把 sync_latex_sources.sh 的默认 ARCHIVE_REV 和 README 的收录表更新到这个提交）："
echo "  ARCHIVE_REV=$rev scripts/sync_latex_sources.sh $y1 $y2"
echo "  scripts/build_gaokao_pdfs.sh $y1 $y2"
exit 2
