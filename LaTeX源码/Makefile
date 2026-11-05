# 批量编译本目录下的试卷和专题练习（每卷也可单独编译：make -C 2025/广东）
#
#   make                  编译全部试卷和专题练习（每份：TikZ 图片 + 学生版 + 教师版）
#   make YEAR=2025        只编译某一年的试卷（不含专题练习）
#   make JOBS=4           同时编译 4 份
#   make student|teacher  只编译学生版 / 教师版
#   make clean            清理辅助文件
#   make distclean        恢复到刚检出的状态：再删除 PDF 成品、.xdv、svg-inkscape/ 和 make links 建立的软链接
#
# 这里只在各自目录里生成 PDF。要得到和 Release 中一样的 PDF，请用 scripts/build_gaokao_pdfs.sh，
# 它会固定 PDF 里的时间戳（编译结果可复现），并只复制编译成功的 PDF 到仓库根目录的 高考真题/ 和 专题练习/。
ifeq ($(origin YEAR),undefined)
TOPIC_DIRS := $(patsubst %/Makefile,%,$(wildcard 专题练习/*/Makefile))
endif
YEAR ?= [0-9][0-9][0-9][0-9]
JOBS ?= 1
DIRS := $(patsubst %/Makefile,%,$(wildcard $(YEAR)/*/Makefile)) $(TOPIC_DIRS)
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
