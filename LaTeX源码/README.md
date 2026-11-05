# 高考物理真题 LaTeX 源码（2020—2026）

这里是 [`高考真题/`](../高考真题/) 中 131 套 PDF 的 LaTeX 源文件，可以直接修改并重新编译。
内容来自开源项目 [YLXDXX/gaokao-physics-archive](https://github.com/YLXDXX/gaokao-physics-archive)
提交 `5a60bb3`（2026-10-11），按上游 Git 跟踪的文件导出，不含编译产物；本仓库订正了其中少量错误，见下文「相对上游的改动」。

## 目录结构

```
LaTeX源码/
├── <年份>/
│   ├── README.md            该年各卷的题数和制作说明（上游年份索引）
│   └── <地区>/
│       ├── <地区>.tex       试卷源文件：学生版和教师版共用这一个文件
│       ├── Makefile         本卷编译脚本
│       ├── figs/            本卷图片（png / svg / pdf，figs/ 下的 pdf 是源图，不要删）
│       └── TikZ/            个别卷有：人工重绘的 TikZ 图
├── 专题练习/<专题>/          专题练习的源文件（本仓库自己编排，不是上游导出的），PDF 在仓库根目录的 专题练习/
├── 异常记录/<年份>.md        上游记录的逐卷异常和待人工核验事项
├── 订正补丁/<年份>.patch     本仓库对上游 .tex 的订正（同步时自动重新应用），清单见 订正补丁/README.md
├── gaokaozhenti.cls         公共文档类（基于 ctexbook）
├── ChoiceQuestion.sty       选择题、图片、答案与解析命令
├── PhyUnit.sty              物理单位宏包
├── package/                 选项排版依赖（exam-zh-choices）
├── tools/                   tex_links.py（建立公共文件软链接）、bin/inkscape（Inkscape 串行化包装）
├── *-manual.md              ChoiceQuestion.sty / PhyUnit.sty 使用说明
├── LaTeX_format_ReadMe.md   上游的 LaTeX 书写规范
└── Makefile                 批量编译
```

## 编译

需要 GNU make、Python 3、XeLaTeX、latexmk、Inkscape、Noto CJK 字体和 Liberation 字体：

- Inkscape：svg 宏包用它把 SVG 图转成 PDF，所以编译时要开 `-shell-escape`（Makefile 已经加上）。
- Python 3：`make links` 用它建立指向公共文档类和宏包的软链接。
- Noto CJK 字体是**必需**的：2020 全国理综Ⅱ/Ⅲ、2021 全国甲卷、2021 福建的教师版直接用 Noto CJK 排 ⑪ 以上的圈码，
  缺字体时这几套卷会编译失败；它也用来回退 Fandol 缺少的生僻字（见下文「相对上游的改动」第 2 条）。
- SVG 图中的文字用 Liberation 字体和文鼎 PL 简报宋（texlive-lang-chinese 已依赖）：图里指定的是 Times New Roman、宋体等 Windows 字体，
  [`scripts/build_gaokao_pdfs.sh`](../scripts/build_gaokao_pdfs.sh) 按 [`scripts/fonts.conf`](../scripts/fonts.conf)
  把它们固定换成 Liberation Serif 和 AR PL SungtiL GB。直接用 `make` 编译时按本机的字体配置替换，图中字体可能与仓库里的 PDF 不同。

在 Ubuntu/Debian 上可以这样安装：

```bash
sudo apt-get install make python3 texlive-xetex texlive-lang-chinese texlive-latex-extra \
  texlive-science texlive-pictures texlive-plain-generic latexmk inkscape fonts-noto-cjk fonts-liberation
```

```bash
make -C LaTeX源码/2025/广东            # 编译一套卷：生成 广东_学生版.pdf 和 广东_教师版.pdf
make -C LaTeX源码/2025/广东 teacher    # 只编译教师版（含答案与详解）
make -C LaTeX源码 YEAR=2025 JOBS=4     # 编译 2025 年全部试卷，4 套并行
make -C LaTeX源码 JOBS=4               # 编译全部试卷和专题练习
make -C LaTeX源码 distclean            # 删除全部编译产物（含专题练习），恢复到刚检出的状态
```

- 这些命令只在源码目录里生成 PDF。要更新仓库里的 `高考真题/` 和 `专题练习/`，请用
  [`scripts/build_gaokao_pdfs.sh`](../scripts/build_gaokao_pdfs.sh)：它固定了写进 PDF 的时间戳和 SVG 图的字体替换
  （编译结果可复现），只复制编译成功的 PDF。
- 改了题目的标注（`%% chapter`、`%% point`、`%% type` 等）或答案后，运行 `python3 scripts/gen_index.py`
  更新 [`知识点索引/`](../知识点索引/README.md) 和 [`答案速查/`](../答案速查/README.md)。
- 改了 `<年份>/` 下的 `.tex` 后，运行 `SAVE_PATCHES=1 scripts/sync_latex_sources.sh <起始年份> <结束年份>`
  更新 [`订正补丁/`](订正补丁/README.md)，并在其中的清单里写明订正内容和依据；否则下次同步上游时这些改动会丢失。
- 学生版和教师版来自同一个 `.tex`：Makefile 编译教师版时会预先定义 `\gkver` 为 `teacher`，源文件不需要改。
- **用 TeXStudio 等编辑器直接编译**：
  1. 先在该卷目录执行一次 `make links tikz`。`links` 建立指向公共文档类和宏包的相对软链接（需要系统支持软链接），
     `tikz` 编译 `TikZ/` 下的图片（目前只有 2026/湖北 有，其他卷什么也不做）。
     要一次为全部试卷建立软链接，可以运行 `cd LaTeX源码 && python3 tools/tex_links.py 20*/*/`
     （不带参数时它会找上游的 `试卷/` 目录，这里不适用）。
  2. 编辑器里选 XeLaTeX，并在命令中加上 `-shell-escape`，否则带 SVG 图的卷（大多数）会报
     `File ..._svg-raw.pdf is missing`。TeXStudio 的设置位置：选项 → 设置 TeXstudio → 命令 → XeLaTeX，
     改为 `xelatex -shell-escape -synctex=1 -interaction=nonstopmode %.tex`。
     先用 `make` 完整编译过一次的卷，`svg-inkscape/` 里已有转换好的图，不加 `-shell-escape` 也能编译。
  3. 编辑器直接编译得到的是学生版；要得到教师版，把源文件第一行改成 `\def\gkver{teacher}`。
- 编译产物（PDF、辅助文件、软链接、`svg-inkscape/`）已在 `.gitignore` 中忽略。
- 各卷 Makefile 中的 `check`、`tikz-compare` 等自查目标依赖上游的完整 `tools/` 和原始材料，
  这里没有收录，需要时请到上游仓库使用。

## 相对上游的改动

导出由 [`scripts/sync_latex_sources.sh`](../scripts/sync_latex_sources.sh) 完成，只做了以下改动：

1. **目录少一层**：上游是 `试卷/<年份>/<地区>/`，这里是 `<年份>/<地区>/`，
   所以各卷 Makefile 的 `ROOT` 从 `../../..` 改成了 `../..`。
2. **生僻字回退**：`gaokaozhenti.cls` 在使用 Fandol 字体时，如果系统装有 Noto Serif CJK SC，
   就用它显示 Fandol 缺少的字（2020—2026 年只有 2022 福建卷的「躄躠」受影响）；没装 Noto 字体时与上游完全一致。
3. **链接修正**：年份索引和异常记录里指向上游其他文件的相对链接，改为指向本目录或上游仓库网址。
4. **本地订正**：应用 [`订正补丁/<年份>.patch`](订正补丁/README.md)，订正上游 `.tex` 中能确定的错误，
   包括 104 处没设尺寸、超出版心的图片，3 处误用了别的题的图，1 处漏标的选择题答案，4 处分值笔误，
   15 处超出版心的填空横线和公式，以及与专题练习一致的 8 题订正（详解、题干和表头中的错误）。
   补丁和上游冲突时，同步脚本报错退出，不改动任何文件。

除这四处外，从上游导出的文件与上游逐字节相同；本目录的 `README.md`、`Makefile`（批量编译）、`.gitignore`、
`订正补丁/` 和 `专题练习/` 是本仓库自己写的。`专题练习/` 中的题目和配图取自上游（包括 2020 年以前的年份），
出处和订正见 [`../专题练习/README.md`](../专题练习/README.md)；编译方法与各卷相同，如
`make -C LaTeX源码/专题练习/自感与涡流`。要同步上游的新内容，运行：

```bash
ARCHIVE_REV=<上游提交> scripts/sync_latex_sources.sh 2020 2026
```

同步会整体替换这些年份的试卷和异常记录，以及公共文档类、宏包和 `tools/`；订正补丁会重新应用，其他本地改动会丢失。
`LaTeX源码/` 有未提交的改动时脚本会拒绝运行；确认不需要这些改动后，用 `FORCE=1` 重新运行。

## 许可

上游项目的许可声明见 [`LICENSE`](LICENSE)。高考试题的著作权归命题单位所有，仅供个人学习和研究使用。
