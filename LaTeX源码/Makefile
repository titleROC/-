# 批量编译本目录下的试卷（每卷也可单独编译：make -C 2025/广东）
#
#   make                  编译全部试卷（每卷：TikZ 图片 + 学生版 + 教师版）
#   make YEAR=2025        只编译某一年
#   make JOBS=4           同时编译 4 套卷
#   make student|teacher  只编译学生版 / 教师版
#   make clean            清理辅助文件
#   make distclean        恢复到刚检出的状态：再删除 PDF 成品、.xdv、svg-inkscape/ 和 make links 建立的软链接
YEAR ?= [0-9][0-9][0-9][0-9]
JOBS ?= 1
DIRS := $(patsubst %/Makefile,%,$(wildcard $(YEAR)/*/Makefile))
LINKS := gaokaozhenti.cls PhyUnit.sty ChoiceQuestion.sty package TikZ/PhyUnit.sty

.PHONY: all student teacher clean distclean
all student teacher clean:
	@printf '%s\0' $(DIRS) | xargs -0 -r -P $(JOBS) -I{} \
		$(MAKE) --no-print-directory -C {} $@

# 各卷 Makefile 的 distclean（与上游一致）不删 .xdv、svg-inkscape/ 和软链接，这里补上
distclean:
	@printf '%s\0' $(DIRS) | xargs -0 -r -P $(JOBS) -I{} \
		$(MAKE) --no-print-directory -C {} distclean
	@for d in $(DIRS); do \
		rm -rf "$$d"/*.xdv "$$d"/svg-inkscape "$$d"/.build-ok; \
		for l in $(LINKS); do [ -L "$$d/$$l" ] && rm -f "$$d/$$l"; done; \
	done; true
