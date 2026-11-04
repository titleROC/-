#!/usr/bin/env bash
# 用本仓库「LaTeX源码/」中的 LaTeX 源编译 PDF，放入本仓库：
#   试卷      LaTeX源码/<年份>/<地区>/  →  高考真题/<年份>/<年份>_<地区>_{学生版,教师版}.pdf
#   专题练习  LaTeX源码/专题练习/<专题>/  →  专题练习/<专题>_{学生版,教师版}.pdf
# （更新 LaTeX 源请先运行 scripts/sync_latex_sources.sh）
#
# 用法：
#   scripts/build_gaokao_pdfs.sh [起始年份] [结束年份]     # 默认 2020 2026，同时编译全部专题练习
#   scripts/build_gaokao_pdfs.sh 专题练习                  # 只编译专题练习
#
# 依赖（Ubuntu/Debian）：
#   apt-get install make python3 texlive-xetex texlive-lang-chinese texlive-latex-extra \
#     texlive-science texlive-pictures texlive-plain-generic latexmk inkscape fonts-noto-cjk
#   fonts-noto-cjk 是必需的：2020 全国理综Ⅱ/Ⅲ、2021 全国甲卷、2021 福建的教师版直接用 Noto CJK
#   字体排 ⑪ 以上的圈码，缺这个字体会编译失败；它也用于回退 Fandol 缺少的生僻字（如 2022 福建卷「躄躠」）。
#
# 只有本次编译成功的卷才会复制到输出目录；有卷失败时脚本以非零状态退出。
#
# 编译结果可复现：脚本固定了 SOURCE_DATE_EPOCH，PDF 里的创建时间、字体子集名和文件 ID 不再随编译时间变化。
# 用同一版本的 TeX Live 和 Inkscape 编译时，源文件没变的卷重新编译后与原来的 PDF 逐字节相同，
# 所以全量重新编译只会让内容真正变了的 PDF 出现在 git 改动里。
#
# 环境变量：
#   JOBS               并行编译的份数（默认 4）
#   TOPICS=0           不编译专题练习
#   SOURCE_DATE_EPOCH  写进 PDF 的时间（Unix 秒）。默认固定为 1791717565（2026-10-11，加入这个设置时
#                      LaTeX源码/ 所依据的上游提交 5a60bb3 的时间）。它只用来让编译可复现，不表示实际编译时间；
#                      同步到新的上游提交后也不必改它，改了会让全部 PDF 都变成“已修改”
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SRC="$REPO_ROOT/LaTeX源码"
OUT="$REPO_ROOT/高考真题"
TOPIC_OUT="$REPO_ROOT/专题练习"
JOBS="${JOBS:-4}"
TOPICS="${TOPICS:-1}"

# xdvipdfmx 用 SOURCE_DATE_EPOCH 生成 CreationDate/ModDate、字体子集名和文件 ID；
# FORCE_SOURCE_DATE=1 让 XeTeX 的 \today、\time 等也用这个时间
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1791717565}"
export FORCE_SOURCE_DATE=1

dirs=()
if [ "${1:-}" = 专题练习 ]; then
  TOPICS=1
else
  FROM="${1:-2020}"
  TO="${2:-2026}"
  for year in $(seq "$FROM" "$TO"); do
    for d in "$SRC/$year"/*/; do
      [ -f "$d/Makefile" ] && dirs+=("${d%/}")
    done
  done
  [ "${#dirs[@]}" -gt 0 ] || { echo "LaTeX源码/ 中没有 $FROM—$TO 年的试卷，请先运行 scripts/sync_latex_sources.sh"; exit 1; }
fi
npapers="${#dirs[@]}"
if [ "$TOPICS" != 0 ]; then
  for d in "$SRC/专题练习"/*/; do
    [ -f "$d/Makefile" ] && dirs+=("${d%/}")
  done
fi
[ "${#dirs[@]}" -gt 0 ] || { echo "LaTeX源码/专题练习/ 中没有专题练习"; exit 1; }
ntopics=$(( ${#dirs[@]} - npapers ))
summary="$npapers 套试卷、$ntopics 个专题练习"
[ "$ntopics" -eq 0 ] && summary="$npapers 套试卷"
[ "$npapers" -eq 0 ] && summary="$ntopics 个专题练习"
echo "共 $summary，开始编译（JOBS=$JOBS）..."

# 每份 make all = TikZ 图 + 学生版 + 教师版；Inkscape 调用已由 tools/bin/inkscape 串行化。
# 成功的留下 .build-ok 标记，复制时只认这个标记，避免把旧 PDF 当成新结果。
for d in "${dirs[@]}"; do rm -f "$d/.build-ok"; done
printf '%s\0' "${dirs[@]}" | xargs -0 -r -n1 -P "$JOBS" sh -c '
  if make -C "$1" all > "$1/build.log" 2>&1; then
    touch "$1/.build-ok"; echo "OK   $1"
  else
    echo "FAIL $1"
  fi' sh

failed=()
for d in "${dirs[@]}"; do
  name="$(basename "$d")"
  parent="$(basename "$(dirname "$d")")"
  if [ "$parent" = 专题练习 ]; then
    label="专题练习/$name"; dest="$TOPIC_OUT"; prefix="$name"
  else
    label="$parent/$name"; dest="$OUT/$parent"; prefix="${parent}_$name"
  fi
  if [ ! -f "$d/.build-ok" ]; then
    failed+=("$label")
    continue
  fi
  if grep -qs "Missing character" "$d/${name}_学生版.log" "$d/${name}_教师版.log"; then
    echo "警告：$label 有缺字（是否安装了 fonts-noto-cjk？），见 $d/${name}_学生版.log"
  fi
  mkdir -p "$dest"
  for ver in 学生版 教师版; do
    cp "$d/${name}_${ver}.pdf" "$dest/${prefix}_${ver}.pdf"
  done
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "以下 ${#failed[@]} 份编译失败，未更新它们的 PDF（日志见 LaTeX源码/ 下对应目录的 build.log）："
  printf '  %s\n' "${failed[@]}"
  exit 1
fi
echo "完成"
[ "$npapers" -gt 0 ] && echo "  试卷：$OUT"
[ "$ntopics" -gt 0 ] && echo "  专题练习：$TOPIC_OUT"
exit 0
