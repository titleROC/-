#!/usr/bin/env bash
# 从 YLXDXX/gaokao-physics-archive（LaTeX 源）编译高考物理真题 PDF，
# 并按「高考真题/<年份>/<年份>_<地区>_{学生版,教师版}.pdf」放入本仓库。
#
# 用法：
#   scripts/build_gaokao_pdfs.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 依赖（Ubuntu/Debian）：
#   apt-get install texlive-xetex texlive-lang-chinese texlive-latex-extra \
#     texlive-science texlive-pictures texlive-plain-generic latexmk inkscape
#
# 环境变量：
#   ARCHIVE_DIR   上游仓库的本地克隆位置（默认 ./.cache/gaokao-physics-archive）
#   ARCHIVE_REV   上游提交（默认为下方固定的提交，保证可复现）
#   JOBS          并行编译的试卷数（默认 4）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE_URL="https://github.com/YLXDXX/gaokao-physics-archive.git"
ARCHIVE_DIR="${ARCHIVE_DIR:-$REPO_ROOT/.cache/gaokao-physics-archive}"
ARCHIVE_REV="${ARCHIVE_REV:-5a60bb3e120613c366030bfe886f78cfb3c066a7}"
JOBS="${JOBS:-4}"
OUT="$REPO_ROOT/高考真题"

if [ ! -d "$ARCHIVE_DIR/.git" ]; then
  git clone "$ARCHIVE_URL" "$ARCHIVE_DIR"
fi
git -C "$ARCHIVE_DIR" fetch --quiet origin "$ARCHIVE_REV" 2>/dev/null || true
git -C "$ARCHIVE_DIR" checkout --quiet "$ARCHIVE_REV"

dirs=()
for year in $(seq "$FROM" "$TO"); do
  for d in "$ARCHIVE_DIR/试卷/$year"/*/; do
    [ -f "$d/Makefile" ] && dirs+=("$d")
  done
done
echo "共 ${#dirs[@]} 套试卷，开始编译（JOBS=$JOBS）..."

# 每卷 make all = TikZ 图 + 学生版 + 教师版；Inkscape 调用已由上游 tools/bin/inkscape 串行化
printf '%s\0' "${dirs[@]}" | xargs -0 -P "$JOBS" -I{} \
  sh -c 'make -C "{}" all > "{}/build.log" 2>&1 && echo "OK   {}" || echo "FAIL {}"'

for d in "${dirs[@]}"; do
  region="$(basename "$d")"
  year="$(basename "$(dirname "$d")")"
  mkdir -p "$OUT/$year"
  for ver in 学生版 教师版; do
    src="$d/${region}_${ver}.pdf"
    [ -f "$src" ] && cp "$src" "$OUT/$year/${year}_${region}_${ver}.pdf"
  done
done
echo "完成，输出目录：$OUT"
