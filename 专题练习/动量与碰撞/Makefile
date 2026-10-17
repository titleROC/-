# 动量与碰撞专题练习的编译脚本
#
#   make            编译学生版和教师版，并复制到上一级目录 专题练习/
#   make student    仅学生版（答案留空、不含详解）
#   make teacher    仅教师版（含答案与详解）
#   make links      建立指向 LaTeX源码/ 公共文档类和宏包的软链接（便于 TeXStudio 直接编译）
#   make clean      清理辅助文件
#   make distclean  再删除本目录的 PDF、svg-inkscape/ 和软链接
#
# 文档类和宏包用 LaTeX源码/ 里的公共文件，学生版、教师版来自同一个 .tex（由 \gkver 切换）。
ROOT     := ../../LaTeX源码
export TEXINPUTS := $(ROOT):
# 经 tools/bin/inkscape（flock 串行化）调用 Inkscape
export PATH := $(abspath $(ROOT))/tools/bin:$(PATH)
# svg 宏包需调用 Inkscape，故开启 shell-escape
LATEXMK  := latexmk -xelatex -shell-escape -interaction=nonstopmode -halt-on-error
NAME     := 动量与碰撞

.PHONY: all student teacher links clean distclean

all: student teacher
	cp $(NAME)_学生版.pdf $(NAME)_教师版.pdf ../

student: links
	$(LATEXMK) -jobname=$(NAME)_学生版 $(NAME).tex >$(NAME)_学生版.make.log 2>&1 \
		|| { tail -30 $(NAME)_学生版.make.log; exit 1; }

teacher: links
	$(LATEXMK) -jobname=$(NAME)_教师版 -usepretex='\def\gkver{teacher}' $(NAME).tex >$(NAME)_教师版.make.log 2>&1 \
		|| { tail -30 $(NAME)_教师版.make.log; exit 1; }

links:
	@python3 $(ROOT)/tools/tex_links.py . >/dev/null

clean:
	rm -f *.aux *.log *.out *.toc *.synctex.gz *.fls *.fdb_latexmk *.xdv

distclean: clean
	rm -rf *.pdf svg-inkscape
	rm -f gaokaozhenti.cls PhyUnit.sty ChoiceQuestion.sty package
