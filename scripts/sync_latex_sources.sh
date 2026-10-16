#!/usr/bin/env bash
# 从上游 YLXDXX/gaokao-physics-archive 导出指定年份的 LaTeX 源到「LaTeX源码/」。
#
# 用法：
#   scripts/sync_latex_sources.sh [起始年份] [结束年份]     # 默认 2020 2026
#
# 导出内容（均为上游 git 跟踪的文件，不含编译产物）：
#   LaTeX源码/<年份>/<地区>/     每卷的 .tex、Makefile、figs/、TikZ/ 等（来自上游 试卷/<年份>/<地区>/）
#   LaTeX源码/<年份>/README.md   年份索引（来自上游 试卷/<年份>/README.md）
#   LaTeX源码/异常记录/<年份>.md  上游记录的逐卷异常与待核验事项
#   LaTeX源码/ 根目录            公共文档类与宏包、tex_links.py、inkscape 包装、说明文档
#
# 相对上游的改动（导出时自动完成）：
#   1. 目录少一层（试卷/<年>/<地区> → <年>/<地区>），各卷 Makefile 的 ROOT 由 ../../.. 改为 ../..
#   2. gaokaozhenti.cls 在使用 Fandol 字体时，若系统装有 Noto Serif CJK SC，则用它回退生僻字
#   3. 年份索引与异常记录中指向上游其他文件的相对链接，改为指向本目录或上游仓库网址
#
# 环境变量：
#   ARCHIVE_DIR   上游仓库的本地克隆位置（默认 ./.cache/gaokao-physics-archive）
#   ARCHIVE_REV   上游提交（默认为下方固定的提交，保证可复现）
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE_URL="https://github.com/YLXDXX/gaokao-physics-archive.git"
ARCHIVE_WEB="https://github.com/YLXDXX/gaokao-physics-archive/blob"
ARCHIVE_DIR="${ARCHIVE_DIR:-$REPO_ROOT/.cache/gaokao-physics-archive}"
ARCHIVE_REV="${ARCHIVE_REV:-5a60bb3e120613c366030bfe886f78cfb3c066a7}"
DEST="$REPO_ROOT/LaTeX源码"

if [ ! -d "$ARCHIVE_DIR/.git" ]; then
  git clone "$ARCHIVE_URL" "$ARCHIVE_DIR"
fi
# 只读取提交内容（git archive），不切换上游克隆的工作区
git -C "$ARCHIVE_DIR" cat-file -e "$ARCHIVE_REV^{commit}" 2>/dev/null \
  || git -C "$ARCHIVE_DIR" fetch --quiet origin "$ARCHIVE_REV" \
  || git -C "$ARCHIVE_DIR" fetch --quiet origin

# 导出 = 上游提交里的文件（git archive 只含跟踪文件，不受本地编译产物影响）
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
paths=(gaokaozhenti.cls ChoiceQuestion.sty PhyUnit.sty package LICENSE
       ChoiceQuestion-manual.md PhyUnit-manual.md LaTeX_format_ReadMe.md
       tools/tex_links.py tools/bin/inkscape)
years=()
for year in $(seq "$FROM" "$TO"); do
  git -C "$ARCHIVE_DIR" cat-file -e "$ARCHIVE_REV:试卷/$year" 2>/dev/null || continue
  paths+=("试卷/$year")
  git -C "$ARCHIVE_DIR" cat-file -e "$ARCHIVE_REV:异常记录/$year.md" 2>/dev/null && paths+=("异常记录/$year.md")
  years+=("$year")
done
if [ "${#years[@]}" -eq 0 ]; then
  echo "上游提交 $ARCHIVE_REV 中没有 $FROM—$TO 年的试卷，未做任何改动" >&2
  exit 1
fi
git -C "$ARCHIVE_DIR" archive --format=tar "$ARCHIVE_REV" -- "${paths[@]}" | tar -x -C "$tmp"

mkdir -p "$DEST"
# 公共文件：整体替换，保证与上游一致
for p in gaokaozhenti.cls ChoiceQuestion.sty PhyUnit.sty package LICENSE \
         ChoiceQuestion-manual.md PhyUnit-manual.md LaTeX_format_ReadMe.md tools; do
  rm -rf "${DEST:?}/$p"
  cp -a "$tmp/$p" "$DEST/$p"
done
mkdir -p "$DEST/异常记录"

for year in "${years[@]}"; do
  ydir="$tmp/试卷/$year"
  rm -rf "${DEST:?}/$year"
  cp -a "$ydir" "$DEST/$year"
  # 1. Makefile 的项目根少一层
  find "$DEST/$year" -mindepth 2 -maxdepth 2 -name Makefile \
    -exec sed -i 's#^ROOT     := \.\./\.\./\.\.$#ROOT     := ../..#' {} +
  # 3. 年份索引里的上游链接
  if [ -f "$DEST/$year/README.md" ]; then
    sed -i \
      -e "s#](\.\./\.\./进度记录\.md)#]($ARCHIVE_WEB/$ARCHIVE_REV/进度记录.md)#g" \
      -e "s#](\.\./\.\./异常记录/#](../异常记录/#g" \
      "$DEST/$year/README.md"
  fi
  if [ -f "$tmp/异常记录/$year.md" ]; then
    cp "$tmp/异常记录/$year.md" "$DEST/异常记录/$year.md"
    sed -i \
      -e "s#](\.\./异常记录\.md)#]($ARCHIVE_WEB/$ARCHIVE_REV/异常记录.md)#g" \
      -e "s#](\.\./试卷/#](../#g" \
      "$DEST/异常记录/$year.md"
  fi
done

# 2. Fandol 缺生僻字时回退到 Noto Serif CJK SC（未安装 Noto 时不生效，不影响编译）
python3 -I - "$DEST/gaokaozhenti.cls" <<'PY'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
anchor = "    \\setCJKmonofont{FandolFang-Regular}[Extension=.otf]\n  }\n"
patch = (
    "    \\setCJKmonofont{FandolFang-Regular}[Extension=.otf]\n"
    "    % [LaTeX源码 副本补丁] Fandol 缺个别生僻字（如 2022 福建卷「躄躠」），\n"
    "    % 系统装有 Noto Serif CJK SC 时用它自动回退；未安装则保持原样\n"
    "    \\IfFontExistsTF{Noto Serif CJK SC}\n"
    "      {\\xeCJKsetup{AutoFallBack=true}\n"
    "       \\setCJKfallbackfamilyfont{\\CJKrmdefault}{Noto Serif CJK SC}}\n"
    "      {}\n"
    "  }\n"
)
if "[LaTeX源码 副本补丁]" not in src:
    if src.count(anchor) != 1:
        sys.exit("gaokaozhenti.cls 结构与预期不符，未打补丁")
    src = src.replace(anchor, patch)
    open(path, "w", encoding="utf-8").write(src)
PY

echo "已导出到 $DEST：$(find "$DEST" -mindepth 3 -maxdepth 3 -name Makefile | wc -l) 套试卷"
