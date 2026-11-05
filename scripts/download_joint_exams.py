#!/usr/bin/env python3
"""下载联考公开附件并校验SHA-256；原始文件仅保存在本地缓存。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "联考" / "资料目录.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def target_path(output: Path, relative: str) -> Path:
    target = (output / relative).resolve()
    if not target.is_relative_to(output.resolve()):
        raise ValueError(f"附件保存路径超出输出目录：{relative}")
    return target


def obtain(asset: dict, source: str, output: Path, verify_only: bool) -> str:
    target = target_path(output, asset["local_path"])
    expected = asset["sha256"]
    if target.exists():
        if sha256(target) != expected:
            raise ValueError(f"已有文件校验失败，未覆盖：{target}")
        return "校验通过"
    if verify_only:
        raise FileNotFoundError(f"缺少文件：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        temp = None
        try:
            req = Request(asset["url"], headers={"Referer": source})
            with urlopen(req, timeout=45) as response, tempfile.NamedTemporaryFile(
                dir=target.parent, prefix=".download-", delete=False
            ) as f:
                temp = Path(f.name)
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    f.write(block)
            if sha256(temp) != expected:
                raise ValueError(f"下载内容与2026-11-05记录不同，未保存：{asset['url']}")
            # Preserve files created by another downloader during this request.
            try:
                target.hardlink_to(temp)
            except FileExistsError:
                if sha256(target) != expected:
                    raise ValueError(f"目标文件已被其他进程创建且校验不符：{target}")
            return "下载完成"
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 2 or (isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(attempt + 1)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
    raise RuntimeError("下载未完成")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="列出考试ID和缺项")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="选择全部已取得的附件")
    group.add_argument("--exam", action="append", default=[], help="考试ID，可重复指定")
    parser.add_argument("--verify", action="store_true", help="只检查本地文件，不联网")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache" / "joint-exams")
    args = parser.parse_args()
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))
    known = {r["id"] for r in records}
    unknown = set(args.exam) - known
    if unknown:
        parser.error("未知考试ID：" + ", ".join(sorted(unknown)))
    selected = [r for r in records if not args.exam or r["id"] in args.exam]
    if args.list:
        for r in selected:
            print(f"{r['id']}\t{r['title']}\t{r['completeness']}")
        return 0
    if not (args.all or args.exam):
        parser.error("请指定 --list、--all 或 --exam ID")
    ok, failed = 0, 0
    for r in selected:
        for a in r["assets"]:
            try:
                result = obtain(a, r["source_page"], args.output, args.verify)
                print(f"{result}\t{a['local_path']}")
                ok += 1
            except (OSError, ValueError) as exc:
                print(f"失败\t{r['id']}\t{exc}", file=sys.stderr)
                failed += 1
    print(f"附件成功 {ok}，失败 {failed}；题目内容仍须按目录说明校对。")
    return int(failed > 0)


if __name__ == "__main__":
    sys.exit(main())
