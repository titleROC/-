#!/usr/bin/env python3
"""从本地或 Release 的双版 PDF 提取每个题块所在的物理页。

先编译相应试卷，再运行 python3 scripts/gen_question_pages.py [2025/重庆 ...] 更新页码，
随后运行 python3 scripts/gen_index.py。--check 只比对。--pdf-dir 可指定已下载的 Release 附件目录。
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import csv
from itertools import zip_longest
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "scripts" / "question_pages.csv"
HEADER = ["年份", "试卷", "原题号", "分项", "学生版页码", "教师版页码"]
PageKey = tuple[str, str, str, str]
PageMap = dict[PageKey, tuple[int, int]]
# 一级 enumerate 的标签只有阿拉伯数字和半角句点；中文全角句点多用于教师解析。
LABEL = re.compile(r"^[ \t]*(\d+)\.(?!\d)", re.M)
ITEM = re.compile(r"^\\item(\[[^\]\n]*\])?[ \t]*\n%% number:", re.M)
HAN = re.compile(r"[\u3400-\u9fff]")
sys.path.insert(0, str(ROOT / "scripts"))  # 支持 python -I
import pdf_names  # noqa: E402


def read_table(path: Path = TABLE) -> PageMap:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        if next(reader, None) != HEADER:
            raise ValueError(f"{path}：页码表表头错误")
        result = {}
        for row in reader:
            if len(row) != 6:
                raise ValueError(f"{path}:{reader.line_num}：页码记录应有 6 列")
            year, region, number, part, student, teacher = row
            key = (year, region, number, part)
            if key in result or not all(re.fullmatch(r"[1-9][0-9]*", s) for s in (student, teacher)):
                raise ValueError(f"{path}:{reader.line_num}：{key} 重复或页码无效")
            result[key] = (int(student), int(teacher))
    return result


def pdf_path(directory: Path, year: str, region: str, edition: str) -> Path:
    built = directory / year / f"{year}_{region}_{edition}.pdf"
    released = directory / pdf_names.paper_asset(year, region, edition)
    for path in (built, released):
        if path.is_file():
            return path
    raise FileNotFoundError(f"{year}/{region} {edition}：缺少 {built} 或 {released}")


def han(text: str) -> str:
    return "".join(HAN.findall(text))


def extract(pdf: Path, questions, numbered: list[bool], paper_title: str) -> tuple[list[int], str]:
    """主列表按印出的题号核对；不重复印题号的分项在所属题块内精确找题干。"""
    text = subprocess.check_output(["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"], encoding="utf-8")
    title = "".join(text.partition("\n")[0].split())
    if title != paper_title:
        raise ValueError(f"卷首「{title}」与试卷不符")
    labels = list(LABEL.finditer(text))
    expected = [q for q, visible in zip(questions, numbered) if visible]
    for q, label in zip_longest(expected, labels):
        if q is None or label is None or q.printed != int(label[1]):
            want = f"原 {q.number}{q.part}（印 {q.printed}）" if q else "卷末"
            got = label[1] if label else "卷末"
            raise ValueError(f"一级题号序列不符：应为 {want}，实际为 {got}")

    breaks = [match.start() for match in re.finditer("\f", text)]
    result = []
    seq = 0
    for q, visible in zip(questions, numbered):
        if visible:
            marker = labels[seq]
            seq += 1
            stop = labels[seq].start() if seq < len(labels) else len(text)
            offset = marker.start()
            start = marker.end()
            # 分栏排版、浮动公式或下一行的文字可能先于题号被提取；题首至少一段文字应在附近。
            nearby = han(text[max(0, offset - 180):min(stop, start + 420)])
            sample = han(q.snippet)[:22]
            width = min(6, len(sample))
            if sample and not any(sample[i:i + width] in nearby for i in range(len(sample) - width + 1)):
                raise ValueError(f"原 {q.number}{q.part} 的题干和 PDF 第 {bisect_right(breaks, offset) + 1} 页不符：{q.snippet}")
        else:
            sample = han(q.snippet)[:16]
            chars = list(HAN.finditer(text, start, stop))
            within = "".join(m[0] for m in chars)
            if not sample or within.count(sample) != 1:
                raise ValueError(f"原 {q.number}{q.part} 的分项在原题内无法唯一定位：{q.snippet}")
            offset = chars[within.index(sample)].start()
            start = offset + 1
        result.append(bisect_right(breaks, offset) + 1)
    return result, han(text)


def paper_pages(year: str, region: str, directory: Path) -> PageMap:
    # 索引与提取器共用同一组原题号、分项和题干。只读表格的调用者无需加载 TeX 解析器。
    import gen_index
    from check_pdf_pair import solution_phrases

    tex = gen_index.SRC / year / region / f"{region}.tex"
    source = tex.read_text(encoding="utf-8")
    questions = gen_index.parse_paper(year, region, tex)
    numbered = [not tag for tag in ITEM.findall(source)]
    if not questions or len(numbered) != len(questions) or not numbered[0]:
        raise ValueError(f"{year}/{region}：题块结构与源文件题数不符")
    title = re.search(r"^\\chapter\{([^{}]+)\}", source, re.M)
    if not title:
        raise ValueError(f"{year}/{region}：无法读取卷首标题")
    versions = []
    for edition in ("学生版", "教师版"):
        pdf = pdf_path(directory, year, region, edition)
        try:
            versions.append(extract(pdf, questions, numbered, "".join(title[1].split())))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            raise ValueError(f"{year}/{region} {edition}：{error}") from error
    (student, student_text), (teacher, teacher_text) = versions
    phrases = solution_phrases(source, "")
    if phrases and not any(p in teacher_text and p not in student_text for p in phrases):
        raise ValueError(f"{year}/{region}：两份 PDF 中无法辨认教师版独有的解析，请核对版别")
    result = {(year, region, q.number, q.part): (s, t) for q, s, t in zip(questions, student, teacher)}
    if len(result) != len(questions):
        raise ValueError(f"{year}/{region}：原题号及分项合并后存在重复键")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="逐卷对照成品，只核对，不改页码表")
    parser.add_argument("--pdf-dir", type=Path, default=ROOT / "高考真题", help="PDF 根目录或 Release 附件目录")
    parser.add_argument("--table", type=Path, default=TABLE, help="页码 CSV 路径")
    parser.add_argument("targets", nargs="*", help="不指定或 all 为所有年度试卷；专题目标自动跳过")
    args = parser.parse_args()
    all_papers = sorted(pdf_names.papers())
    chosen = set()
    for target in args.targets:
        if target == "all" or target.startswith("专题练习/"):
            continue
        pair = tuple(target.split("/"))
        if pair not in all_papers:
            raise ValueError(f"未知试卷：{target}")
        chosen.add(pair)
    full = not args.targets or "all" in args.targets
    targets = all_papers if full else sorted(chosen)
    if not targets:
        print("所选目标只有专题练习，无年度真题页码需要核对")
        return

    current = read_table(args.table) if args.table.exists() else {}
    if args.check and not args.table.is_file():
        raise ValueError(f"缺少页码表 {args.table}")
    # 全量重算按源文件删除已移除的卷；增量重算仅替换所选卷，发生错误时保留原表。
    selected = set(targets)
    updated = {} if full else {key: pages for key, pages in current.items() if key[:2] not in selected}
    for year, region in targets:
        updated.update(paper_pages(year, region, args.pdf_dir))
    if args.check:
        mismatches = [k for k in dict.fromkeys([*current, *updated]) if current.get(k) != updated.get(k)]
        for year, region, number, part in mismatches:
            key = year, region, number, part
            print(f"{year}/{region} 原 {number}{part}（学生版、教师版）表中 {current.get(key)}，PDF {updated.get(key)}", file=sys.stderr)
        if mismatches:
            raise ValueError(f"{len(mismatches)} 条页码不符，请用对应成品更新")
    else:
        # 排序只按试卷，卷内保留原有题块顺序。
        with tempfile.TemporaryDirectory(dir=args.table.parent) as staging:
            temporary = Path(staging) / args.table.name
            with temporary.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(HEADER)
                for key in sorted(updated, key=lambda k: k[:2]):
                    writer.writerow([*key, *updated[key]])
            if args.table.exists():
                shutil.copymode(args.table, temporary)
            temporary.replace(args.table)
    count = sum(key[:2] in selected for key in updated)
    print(f"{len(targets)} 套、{count} 个题块的学生版及教师版页码已{'核对' if args.check else '更新'}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
