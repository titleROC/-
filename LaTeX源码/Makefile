# 批量编译本目录下的试卷（每卷也可单独编译：make -C 2025/广东）
#
#   make                  编译全部试卷（每卷：TikZ 图片 + 学生版 + 教师版）
#   make YEAR=2025        只编译某一年
#   make JOBS=4           同时编译 4 套卷
#   make student|teacher  只编译学生版 / 教师版
#   make clean            清理辅助文件；make distclean 连同 PDF 成品一起清理
YEAR ?= [0-9][0-9][0-9][0-9]
JOBS ?= 1
DIRS := $(patsubst %/Makefile,%,$(wildcard $(YEAR)/*/Makefile))

.PHONY: all student teacher clean distclean
all student teacher clean distclean:
	@printf '%s\0' $(DIRS) | xargs -0 -r -P $(JOBS) -I{} \
		$(MAKE) --no-print-directory -C {} $@
