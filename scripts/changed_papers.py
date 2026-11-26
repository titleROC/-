#!/usr/bin/env python3
"""列出相对某个提交需要重新编译的试卷和专题练习（CI 用它决定重编哪些 PDF）。

用法：
  python3 scripts/changed_papers.py <基准提交>

每行输出一个 scripts/build_gaokao_pdfs.sh 能接受的目标，如 2023/湖南、专题练习/动量与碰撞，
包括源文件有变化的卷，以及题页表中有改动、需要用成品核对的卷。公共文档类、宏包、tools/、
字体配置或共用的编译、验收脚本变动时输出 all。年份索引、异常记录、订正补丁和说明文档不影响 PDF。
只用 Python 标准库。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMON_RE = re.compile(r"^LaTeX源码/(?:gaokaozhenti\.cls|ChoiceQuestion\.sty|PhyUnit\.sty|package/|tools/)"
                       r"|^scripts/(?:build_gaokao_pdfs\.sh|check_pdf_pair\.py|gen_question_pages\.py|fonts\.conf)$")
SOURCE_RE = re.compile(r"^LaTeX源码/(\d{4}|专题练习)/([^/]+)/")


def targets(names: list[str]) -> list[str]:
    found = set()
    for name in names:
        if COMMON_RE.search(name):
            return ["all"]
        if m := SOURCE_RE.match(name):
            found.add(f"{m.group(1)}/{m.group(2)}")
    # 已删除的卷没有 Makefile，不用编译
    return sorted(t for t in found if (REPO / "LaTeX源码" / t / "Makefile").is_file())


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    diff = ["git", "-C", str(REPO), "-c", "core.quotepath=off", "diff", sys.argv[1], "HEAD"]
    names = subprocess.check_output([*diff, "--name-only"], text=True).splitlines()
    selected = set(targets(names))
    if "all" not in selected and "scripts/question_pages.csv" in names:
        rows = subprocess.check_output([*diff, "--unified=0", "--", "scripts/question_pages.csv"], text=True)
        for year, region in re.findall(r"^[+-](\d{4}),([^,\n]+),", rows, re.M):
            if (REPO / "LaTeX源码" / year / region / "Makefile").is_file():
                selected.add(f"{year}/{region}")
    for t in sorted(selected):
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
