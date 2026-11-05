#!/usr/bin/env python3
"""检查仓库里所有 Markdown 文件中的相对链接：目标文件存在，#锚点对应目标文件中的标题。

用法：
  python3 scripts/check_links.py      有失效的链接时列出并以状态 1 退出

只检查 git 跟踪的 .md 文件，跳过代码块和网址；锚点按 GitHub 生成标题锚点的规则计算（小写、去掉标点、
空格变连字符，重名依次加 -1、-2）。只用 Python 标准库。
"""
from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CODE_BLOCK_RE = re.compile(r"^```.*?^```", re.M | re.S)


def slugify(heading: str) -> str:
    h = re.sub(r"<[^>]+>", "", heading)
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h).replace("`", "").strip().lower()
    return "".join("-" if c == " " else c for c in h
                   if c in "-_ " or unicodedata.category(c)[0] in "LN" or unicodedata.category(c) in ("Mn", "Mc"))


_anchors: dict[Path, set[str]] = {}


def anchors(path: Path) -> set[str]:
    if path not in _anchors:
        seen: dict[str, int] = {}
        found = set()
        text = path.read_text("utf-8")
        for line in CODE_BLOCK_RE.sub("", text).splitlines():
            m = HEADING_RE.match(line)
            if m:
                slug = slugify(m.group(2))
                n = seen.get(slug, 0)
                seen[slug] = n + 1
                found.add(slug if n == 0 else f"{slug}-{n}")
        found.update(re.findall(r'<a\s+(?:name|id)="([^"]+)"', text))
        _anchors[path] = found
    return _anchors[path]


def main() -> int:
    out = subprocess.run(["git", "-C", str(REPO), "-c", "core.quotepath=off", "ls-files", "*.md"],
                         capture_output=True, text=True, check=True).stdout
    total, bad = 0, []
    for name in filter(None, out.splitlines()):
        md = REPO / name
        for m in LINK_RE.finditer(CODE_BLOCK_RE.sub("", md.read_text("utf-8"))):
            url = m.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
                continue  # 网址、mailto: 等
            total += 1
            path, _, frag = url.partition("#")
            target = (md.parent / unquote(path)).resolve() if path else md
            if not target.exists():
                bad.append(f"{name}：{url}（文件不存在）")
            elif frag and target.suffix == ".md" and unquote(frag) not in anchors(target):
                bad.append(f"{name}：{url}（没有这个标题）")
    for b in bad:
        print(b, file=sys.stderr)
    print(f"检查了 {total} 个相对链接，失效 {len(bad)} 个")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
