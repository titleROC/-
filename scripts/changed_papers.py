#!/usr/bin/env python3
"""列出相对某个提交需要重新编译的试卷和专题练习（CI 用它决定重编哪些 PDF）。

用法：
  python3 scripts/changed_papers.py <基准提交>

每行输出一个 scripts/build_gaokao_pdfs.sh 能接受的目标，如 2023/湖南、专题练习/动量与碰撞，
即 LaTeX源码/ 中文件有变化的卷。公共文档类、宏包、tools/、编译脚本或字体配置变了时只输出一行 all
（要全部重新编译）；没有要编译的就不输出。年份索引、异常记录、订正补丁和说明文档不影响 PDF。
只用 Python 标准库。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMON_RE = re.compile(r"^LaTeX源码/(?:gaokaozhenti\.cls|ChoiceQuestion\.sty|PhyUnit\.sty|package/|tools/)"
                       r"|^scripts/(?:build_gaokao_pdfs\.sh|fonts\.conf)$")
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
    out = subprocess.run(["git", "-C", str(REPO), "-c", "core.quotepath=off", "diff", "--name-only", sys.argv[1], "HEAD"],
                         capture_output=True, text=True, check=True).stdout
    for t in targets(out.splitlines()):
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
