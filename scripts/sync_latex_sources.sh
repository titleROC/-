#!/usr/bin/env bash
# 从上游 YLXDXX/gaokao-physics-archive 导出指定年份的 LaTeX 源到「LaTeX源码/」。
#
# 用法：
#   scripts/sync_latex_sources.sh [起始年份] [结束年份]                  # 默认 2020 2026
#   SAVE_PATCHES=1 scripts/sync_latex_sources.sh [起始年份] [结束年份]   # 只重新生成本地订正补丁，见下文
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
#   4. 本地订正：应用 LaTeX源码/订正补丁/<年份>.patch（本仓库对上游 .tex 的订正和补上的图，说明见该目录的 README.md）
# 所有改动先在临时目录里完成，全部成功后才复制进 LaTeX源码/；订正补丁和上游冲突时报错退出，不改动任何文件。
#
# 导出后自动运行 scripts/gen_index.py，更新 知识点索引/ 和 答案速查/。
#
# 修改订正：直接改 LaTeX源码/<年份>/ 下的 .tex（要补的图放进该卷的 figs/），然后用 SAVE_PATCHES=1 运行本脚本。
# 它对比上游原样的文件和本地的 .tex 及 figs/ 中的图，重新生成这些年份的 订正补丁/<年份>.patch
# （没有差异时删除补丁），不改动 LaTeX源码/ 的其他文件。
#
# 环境变量：
#   ARCHIVE_DIR   上游仓库的本地克隆位置（默认 ./.cache/gaokao-physics-archive）
#   ARCHIVE_REV   上游提交（默认为下方固定的提交，保证可复现）
#   FORCE=1       LaTeX源码/ 有未提交的改动时也照样覆盖（默认拒绝运行）
#   SAVE_PATCHES=1  只重新生成订正补丁（见上文）
#
# 注意：无论年份范围是什么，公共文档类、宏包和 tools/ 都会整体替换为上游版本。
set -euo pipefail

FROM="${1:-2020}"
TO="${2:-2026}"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ARCHIVE_URL="https://github.com/YLXDXX/gaokao-physics-archive.git"
ARCHIVE_WEB="https://github.com/YLXDXX/gaokao-physics-archive/blob"
ARCHIVE_DIR="${ARCHIVE_DIR:-$REPO_ROOT/.cache/gaokao-physics-archive}"
ARCHIVE_REV="${ARCHIVE_REV:-5a60bb3e120613c366030bfe886f78cfb3c066a7}"
DEST="$REPO_ROOT/LaTeX源码"
PATCH_DIR="$DEST/订正补丁"
COMMON=(gaokaozhenti.cls ChoiceQuestion.sty PhyUnit.sty package LICENSE
        ChoiceQuestion-manual.md PhyUnit-manual.md LaTeX_format_ReadMe.md tools)

# 同步会覆盖 LaTeX源码/ 中的文件，有未提交的改动时先停下（SAVE_PATCHES 只读取 LaTeX源码/，不受限制）
if [ -z "${SAVE_PATCHES:-}" ] && [ -z "${FORCE:-}" ] \
   && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   && [ -n "$(git -C "$REPO_ROOT" status --porcelain -- LaTeX源码)" ]; then
  echo "LaTeX源码/ 有未提交的改动，同步会覆盖它们；确认不需要后用 FORCE=1 重新运行" >&2
  exit 1
fi

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
# 下面在临时目录里运行的 git 命令不要向上找到别的仓库
export GIT_CEILING_DIRECTORIES="$tmp"

# ---------------------------------------------------------------------------
# SAVE_PATCHES=1：对比上游原样的文件和 LaTeX源码/ 中的文件，重新生成 订正补丁/<年份>.patch。
# 记录两类改动：上游已有的 .tex 的修改；各卷 figs/ 中新增或替换的图（二进制补丁）。
# ---------------------------------------------------------------------------
if [ -n "${SAVE_PATCHES:-}" ]; then
  up="$tmp/试卷"
  git -C "$up" init -q
  git -C "$up" add -A .
  git -C "$up" -c user.name=sync -c user.email=sync@localhost -c commit.gpgsign=false commit -q -m upstream
  mkdir -p "$PATCH_DIR"
  for year in "${years[@]}"; do
    [ -d "$DEST/$year" ] || continue
    # 本地的 .tex 和 figs/ 中的图：git 跟踪的和未跟踪但没有被忽略的文件
    while IFS= read -r -d '' p; do
      f="$REPO_ROOT/$p"
      rel="${p#LaTeX源码/}"
      [ -f "$f" ] || continue
      case "$rel" in
        *.tex)
          if [ -f "$up/$rel" ]; then
            cp "$f" "$up/$rel"
          else
            echo "跳过 $rel：上游没有这个文件（订正补丁只记录对上游 .tex 的修改和 figs/ 中的图）" >&2
          fi ;;
        */figs/*)
          if ! cmp -s "$f" "$up/$rel" 2>/dev/null; then
            mkdir -p "$(dirname -- "$up/$rel")"
            cp "$f" "$up/$rel"
          fi ;;
      esac
    done < <(git -C "$REPO_ROOT" ls-files -z -co --exclude-standard -- "LaTeX源码/$year" \
               | grep -z -E '(\.tex|/figs/[^/]+)$')
    git -C "$up" add -A -- "$year"
    patch="$PATCH_DIR/$year.patch"
    git -C "$up" -c core.quotepath=false diff --cached --binary --no-color --no-ext-diff \
      --src-prefix=a/ --dst-prefix=b/ -- "$year" > "$patch.new"
    if [ -s "$patch.new" ]; then
      mv "$patch.new" "$patch"
      echo "已写入 LaTeX源码/订正补丁/$year.patch（$(grep -c '^diff --git' "$patch") 个文件）"
    else
      rm -f "$patch.new"
      if [ -f "$patch" ]; then rm -f "$patch"; echo "$year 年没有本地订正，已删除 订正补丁/$year.patch"; fi
    fi
  done
  exit 0
fi

# ---------------------------------------------------------------------------
# 以下改动全部先在临时目录里完成
# ---------------------------------------------------------------------------
# 4. 本地订正
applied=0
for year in "${years[@]}"; do
  patch="$PATCH_DIR/$year.patch"
  [ -f "$patch" ] || continue
  if (cd "$tmp/试卷" && git apply --check "$patch" 2>/dev/null); then
    (cd "$tmp/试卷" && git apply --whitespace=nowarn "$patch")
    applied=$((applied + 1))
  elif (cd "$tmp/试卷" && git apply -R --check "$patch" 2>/dev/null); then
    echo "上游 $ARCHIVE_REV 已包含 订正补丁/$year.patch 的全部订正，可以删除这个补丁" >&2
  else
    echo "订正补丁/$year.patch 不能应用到上游 $ARCHIVE_REV（上游改动了相关内容），LaTeX源码/ 没有任何改动。" >&2
    echo "请对照上游逐条核对 订正补丁/README.md 中的订正，改好后用 SAVE_PATCHES=1 重新生成补丁。冲突详情：" >&2
    (cd "$tmp/试卷" && git apply --check "$patch") || true
    exit 1
  fi
done

for year in "${years[@]}"; do
  ydir="$tmp/试卷/$year"
  # 1. Makefile 的项目根少一层；改完逐个核对，上游 Makefile 格式变了就停下
  find "$ydir" -mindepth 2 -maxdepth 2 -name Makefile \
    -exec sed -i 's#^ROOT     := \.\./\.\./\.\.$#ROOT     := ../..#' {} +
  bad="$(find "$ydir" -mindepth 2 -maxdepth 2 -name Makefile -exec grep -L '^ROOT     := \.\./\.\.$' {} + || true)"
  if [ -n "$bad" ]; then
    echo "以下 Makefile 的 ROOT 没能改成 ../..（上游 Makefile 的格式变了？），LaTeX源码/ 没有任何改动：" >&2
    echo "${bad//"$tmp/试卷/"/}" >&2
    exit 1
  fi
  # 3. 年份索引和异常记录里的上游链接
  if [ -f "$ydir/README.md" ]; then
    sed -i \
      -e "s#](\.\./\.\./进度记录\.md)#]($ARCHIVE_WEB/$ARCHIVE_REV/进度记录.md)#g" \
      -e "s#](\.\./\.\./异常记录/#](../异常记录/#g" \
      "$ydir/README.md"
  fi
  if [ -f "$tmp/异常记录/$year.md" ]; then
    sed -i \
      -e "s#](\.\./异常记录\.md)#]($ARCHIVE_WEB/$ARCHIVE_REV/异常记录.md)#g" \
      -e "s#](\.\./试卷/#](../#g" \
      "$tmp/异常记录/$year.md"
  fi
done

# 2. Fandol 缺生僻字时回退到 Noto Serif CJK SC（未安装 Noto 时不生效，不影响编译）
python3 -I - "$tmp/gaokaozhenti.cls" <<'PY'
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
        sys.exit("gaokaozhenti.cls 结构与预期不符，未打补丁，LaTeX源码/ 没有任何改动")
    src = src.replace(anchor, patch)
    open(path, "w", encoding="utf-8").write(src)
PY

# ---------------------------------------------------------------------------
# 复制进 LaTeX源码/
# ---------------------------------------------------------------------------
mkdir -p "$DEST" "$DEST/异常记录"
# 公共文件：整体替换，保证与上游一致
for p in "${COMMON[@]}"; do
  rm -rf "${DEST:?}/$p"
  cp -a "$tmp/$p" "$DEST/$p"
done
for year in "${years[@]}"; do
  rm -rf "${DEST:?}/$year"
  cp -a "$tmp/试卷/$year" "$DEST/$year"
  if [ -f "$tmp/异常记录/$year.md" ]; then
    cp "$tmp/异常记录/$year.md" "$DEST/异常记录/$year.md"
  fi
done

echo "已导出到 $DEST：$(find "$DEST"/[0-9][0-9][0-9][0-9] -mindepth 2 -maxdepth 2 -name Makefile | wc -l) 套试卷，应用了 $applied 个订正补丁"

# 标注或答案可能变了，重新生成知识点索引和答案速查
python3 -I "$REPO_ROOT/scripts/gen_index.py"
