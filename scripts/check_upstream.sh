#!/usr/bin/env bash
# 检查上游 YLXDXX/gaokao-physics-archive 的最新提交，相对「LaTeX源码/」所依据的提交（sync_latex_sources.sh 中
# 固定的 ARCHIVE_REV）有没有要同步的内容：
#   - 新卷：上游有、LaTeX源码/ 里还没有的试卷（如 2026 年天津、安徽、江西、福建卷）；
#   - 已有试卷的改动：上游补了详解、补了缺题、订正了错误等；
#   - 其他改动：年份索引、异常记录，以及公共文档类、宏包和 tools/。
# 只读，不改动本仓库。
#
# 用法：
#   scripts/check_upstream.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 退出状态：0 = 没有要同步的内容；2 = 上游有新卷或改动（同时打印同步和编译命令）；其他 = 出错。
# 可以放进定时任务（仓库的 .github/workflows/upstream.yml 每周运行一次）。
#
# 环境变量：
#   ARCHIVE_DIR   上游仓库的本地克隆位置（默认 ./.cache/gaokao-physics-archive，与 sync_latex_sources.sh 共用；
#                 不存在时浅克隆一份）
#   ARCHIVE_REV   作为比较基准的上游提交（默认读取 sync_latex_sources.sh 中固定的提交）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ARCHIVE_URL="https://github.com/YLXDXX/gaokao-physics-archive.git"
ARCHIVE_DIR="${ARCHIVE_DIR:-$REPO_ROOT/.cache/gaokao-physics-archive}"
SRC="$REPO_ROOT/LaTeX源码"
COMMON=(gaokaozhenti.cls ChoiceQuestion.sty PhyUnit.sty package LICENSE
        ChoiceQuestion-manual.md PhyUnit-manual.md LaTeX_format_ReadMe.md tools/tex_links.py tools/bin/inkscape)

if [ -z "${ARCHIVE_REV:-}" ]; then
  ARCHIVE_REV="$(sed -n 's/^ARCHIVE_REV="\${ARCHIVE_REV:-\([0-9a-f]\{40\}\)}"$/\1/p' "$REPO_ROOT/scripts/sync_latex_sources.sh")"
  [ -n "$ARCHIVE_REV" ] || { echo "没能从 scripts/sync_latex_sources.sh 读出固定的 ARCHIVE_REV" >&2; exit 1; }
fi

up() { git -C "$ARCHIVE_DIR" -c core.quotepath=off "$@"; }
if [ ! -d "$ARCHIVE_DIR/.git" ]; then
  git clone --quiet --depth 1 "$ARCHIVE_URL" "$ARCHIVE_DIR"
fi
# 取上游默认分支的最新提交（FETCH_HEAD），不切换上游克隆的工作区
up fetch --quiet origin HEAD
rev="$(up rev-parse FETCH_HEAD)"
if ! up cat-file -e "$ARCHIVE_REV^{commit}" 2>/dev/null; then
  if [ "$(up rev-parse --is-shallow-repository)" = true ]; then
    up fetch --quiet --depth 1 origin "$ARCHIVE_REV"
  else
    up fetch --quiet origin "$ARCHIVE_REV"
  fi
fi
echo "上游最新提交：$(up log -1 --format='%h %cs %s' "$rev")"
echo "LaTeX源码/ 依据：$(up log -1 --format='%h %cs %s' "$ARCHIVE_REV")"
if [ "$(up rev-parse "$ARCHIVE_REV^{commit}")" = "$rev" ]; then
  echo "上游没有新提交"
  exit 0
fi

changed_in() { [ -n "$(up diff --name-only "$ARCHIVE_REV" "$rev" -- "$@")" ]; }
new=(); changed=(); removed=(); others=()
for year in $(seq "$FROM" "$TO"); do
  if up cat-file -e "$rev:试卷/$year" 2>/dev/null; then
    while IFS= read -r region; do
      if [ ! -f "$SRC/$year/$region/Makefile" ]; then
        new+=("$year/$region")
      elif changed_in "试卷/$year/$region"; then
        changed+=("$year/$region")
      fi
    done < <(up ls-tree -d --name-only "$rev:试卷/$year")
    changed_in "试卷/$year/README.md" && others+=("试卷/$year/README.md（年份索引）")
  fi
  for d in "$SRC/$year"/*/; do
    [ -f "$d/Makefile" ] || continue
    region="$(basename "$d")"
    up cat-file -e "$rev:试卷/$year/$region" 2>/dev/null || removed+=("$year/$region")
  done
  changed_in "异常记录/$year.md" && others+=("异常记录/$year.md")
done
common=0
for p in "${COMMON[@]}"; do
  if changed_in "$p"; then others+=("$p"); common=1; fi
done

if [ "${#new[@]}" -eq 0 ] && [ "${#changed[@]}" -eq 0 ] && [ "${#removed[@]}" -eq 0 ] && [ "${#others[@]}" -eq 0 ]; then
  echo "上游有新提交，但 $FROM—$TO 年的试卷、异常记录和公共文件都没有变"
  exit 0
fi
list() { local title="$1"; shift; [ "$#" -gt 0 ] || return 0; echo "$title（$#）："; printf '  %s\n' "$@"; }
list "新卷" "${new[@]}"
list "有改动的试卷" "${changed[@]}"
list "上游已删除的试卷" "${removed[@]}"
list "其他改动" "${others[@]}"

echo
echo "同步（会重新应用订正补丁；补丁和上游冲突时同步脚本会停下，见 LaTeX源码/订正补丁/README.md）："
echo "  ARCHIVE_REV=$rev scripts/sync_latex_sources.sh $FROM $TO"
echo "同步后把 sync_latex_sources.sh 中默认的 ARCHIVE_REV 和各 README 中的提交号改成 ${rev:0:7}，再编译 PDF："
papers=("${new[@]}" "${changed[@]}")
if [ "$common" = 1 ]; then
  echo "  scripts/build_gaokao_pdfs.sh $FROM $TO        # 公共文件变了，全部重新编译"
elif [ "${#papers[@]}" -gt 0 ]; then
  echo "  scripts/build_gaokao_pdfs.sh ${papers[*]}"
else
  echo "  （只有索引或异常记录变了，不用重新编译）"
fi
exit 2
