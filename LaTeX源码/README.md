# 高考物理真题 LaTeX 源码（2020—2026）

这里是 [`高考真题/`](../高考真题/) 中 131 套 PDF 的 LaTeX 源文件，可以直接修改并重新编译。
内容来自开源项目 [YLXDXX/gaokao-physics-archive](https://github.com/YLXDXX/gaokao-physics-archive)
提交 `5a60bb3`（2026-10-11），按上游 Git 跟踪的文件原样导出，不含编译产物。

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
├── 异常记录/<年份>.md        上游记录的逐卷异常和待人工核验事项
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

需要 XeLaTeX、latexmk 和 Inkscape（svg 宏包用它转换 SVG 图）。在 Ubuntu/Debian 上可以这样安装：

```bash
sudo apt-get install texlive-xetex texlive-lang-chinese texlive-latex-extra \
  texlive-science texlive-pictures texlive-plain-generic latexmk inkscape fonts-noto-cjk
```

```bash
make -C LaTeX源码/2025/广东            # 编译一套卷：生成 广东_学生版.pdf 和 广东_教师版.pdf
make -C LaTeX源码/2025/广东 teacher    # 只编译教师版（含答案与详解）
make -C LaTeX源码 YEAR=2025 JOBS=4     # 编译 2025 年全部试卷，4 套并行
make -C LaTeX源码 JOBS=4               # 编译全部试卷
make -C LaTeX源码 distclean            # 清理辅助文件和生成的 PDF
```

- 学生版和教师版来自同一个 `.tex`：Makefile 编译教师版时会预先定义 `\gkver` 为 `teacher`，源文件不需要改。
- 用 TeXStudio 等编辑器直接打开 `.tex` 编译前，先在该卷目录执行一次 `make links`，
  它会建立指向公共文档类和宏包的相对软链接（需要系统支持软链接）。
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

除这三处外，所有文件与上游逐字节相同。要同步上游的新内容，运行：

```bash
ARCHIVE_REV=<上游提交> scripts/sync_latex_sources.sh 2020 2026
```

## 许可

上游项目的许可声明见 [`LICENSE`](LICENSE)。高考试题的著作权归命题单位所有，仅供个人学习和研究使用。
