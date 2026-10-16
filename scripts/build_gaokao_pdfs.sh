#!/usr/bin/env bash
# 用本仓库「LaTeX源码/」中的 LaTeX 源编译高考物理真题 PDF，
# 并按「高考真题/<年份>/<年份>_<地区>_{学生版,教师版}.pdf」放入本仓库。
# （更新 LaTeX 源请先运行 scripts/sync_latex_sources.sh）
#
# 用法：
#   scripts/build_gaokao_pdfs.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 依赖（Ubuntu/Debian）：
#   apt-get install texlive-xetex texlive-lang-chinese texlive-latex-extra \
#     texlive-science texlive-pictures texlive-plain-generic latexmk inkscape fonts-noto-cjk
#   （fonts-noto-cjk 用于回退 Fandol 字体缺少的生僻字，如 2022 福建卷的「躄躠」）
#
# 环境变量：
#   JOBS   并行编译的试卷数（默认 4）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/LaTeX源码"
OUT="$REPO_ROOT/高考真题"
JOBS="${JOBS:-4}"

dirs=()
for year in $(seq "$FROM" "$TO"); do
  for d in "$SRC/$year"/*/; do
    [ -f "$d/Makefile" ] && dirs+=("${d%/}")
  done
done
[ "${#dirs[@]}" -gt 0 ] || { echo "LaTeX源码/ 中没有 $FROM—$TO 年的试卷，请先运行 scripts/sync_latex_sources.sh"; exit 1; }
echo "共 ${#dirs[@]} 套试卷，开始编译（JOBS=$JOBS）..."

# 每卷 make all = TikZ 图 + 学生版 + 教师版；Inkscape 调用已由 tools/bin/inkscape 串行化
printf '%s\0' "${dirs[@]}" | xargs -0 -P "$JOBS" -I{} \
  sh -c 'make -C "{}" all > "{}/build.log" 2>&1 && echo "OK   {}" || echo "FAIL {}"'

fail=0
for d in "${dirs[@]}"; do
  region="$(basename "$d")"
  year="$(basename "$(dirname "$d")")"
  if grep -qs "Missing character" "$d/${region}_学生版.log" "$d/${region}_教师版.log"; then
    echo "警告：$year/$region 有缺字（是否安装了 fonts-noto-cjk？），见 $d/${region}_学生版.log"
  fi
  mkdir -p "$OUT/$year"
  for ver in 学生版 教师版; do
    src="$d/${region}_${ver}.pdf"
    if [ -f "$src" ]; then
      cp "$src" "$OUT/$year/${year}_${region}_${ver}.pdf"
    else
      echo "缺少 $src（编译日志：$d/build.log）"
      fail=1
    fi
  done
done
[ "$fail" -eq 0 ] && echo "完成，输出目录：$OUT" || { echo "部分试卷编译失败"; exit 1; }
