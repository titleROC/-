#!/usr/bin/env bash
# 用本仓库「LaTeX源码/」中的 LaTeX 源编译高考物理真题 PDF，
# 并按「高考真题/<年份>/<年份>_<地区>_{学生版,教师版}.pdf」放入本仓库。
# （更新 LaTeX 源请先运行 scripts/sync_latex_sources.sh）
#
# 用法：
#   scripts/build_gaokao_pdfs.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 依赖（Ubuntu/Debian）：
#   apt-get install make python3 texlive-xetex texlive-lang-chinese texlive-latex-extra \
#     texlive-science texlive-pictures texlive-plain-generic latexmk inkscape fonts-noto-cjk
#   fonts-noto-cjk 是必需的：2020 全国理综Ⅱ/Ⅲ、2021 全国甲卷、2021 福建的教师版直接用 Noto CJK
#   字体排 ⑪ 以上的圈码，缺这个字体会编译失败；它也用于回退 Fandol 缺少的生僻字（如 2022 福建卷「躄躠」）。
#
# 只有本次编译成功的卷才会复制到 高考真题/；有卷失败时脚本以非零状态退出。
#
# 环境变量：
#   JOBS   并行编译的试卷数（默认 4）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
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

# 每卷 make all = TikZ 图 + 学生版 + 教师版；Inkscape 调用已由 tools/bin/inkscape 串行化。
# 成功的卷留下 .build-ok 标记，复制时只认这个标记，避免把旧 PDF 当成新结果。
for d in "${dirs[@]}"; do rm -f "$d/.build-ok"; done
printf '%s\0' "${dirs[@]}" | xargs -0 -r -n1 -P "$JOBS" sh -c '
  if make -C "$1" all > "$1/build.log" 2>&1; then
    touch "$1/.build-ok"; echo "OK   $1"
  else
    echo "FAIL $1"
  fi' sh

failed=()
for d in "${dirs[@]}"; do
  region="$(basename "$d")"
  year="$(basename "$(dirname "$d")")"
  if [ ! -f "$d/.build-ok" ]; then
    failed+=("$year/$region")
    continue
  fi
  if grep -qs "Missing character" "$d/${region}_学生版.log" "$d/${region}_教师版.log"; then
    echo "警告：$year/$region 有缺字（是否安装了 fonts-noto-cjk？），见 $d/${region}_学生版.log"
  fi
  mkdir -p "$OUT/$year"
  for ver in 学生版 教师版; do
    cp "$d/${region}_${ver}.pdf" "$OUT/$year/${year}_${region}_${ver}.pdf"
  done
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "以下 ${#failed[@]} 套卷编译失败，未更新它们的 PDF（日志见 LaTeX源码/<年份>/<地区>/build.log）："
  printf '  %s\n' "${failed[@]}"
  exit 1
fi
echo "完成，输出目录：$OUT"
