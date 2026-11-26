#!/usr/bin/env python3
"""在复制或上传 PDF 前，核对一套题的两版成品和最终 XeLaTeX 日志。"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

LOG_ERROR = re.compile(
    r"^Missing character:|^(?:LaTeX|Package [\w-]+) Warning: "
    r"(?:(?:Reference|Citation) .*undefined|There were undefined (?:references|citations))"
)
ANSWER = re.compile(r"\\(?:memoanswer|jdanswer)\b\s*\*?\s*(?:\[[^\]]*\]\s*)?\{")
HAN = re.compile(r"[\u3400-\u9fff]")


def solution_phrases(tex: str, aux: str) -> list[str]:
    """提取答案框中的连续中文字，排除题面中也出现的文字。"""
    source = re.sub(r"(?<!\\)%[^\n]*", "", tex)
    public, phrases = [], set()
    pos = 0
    while match := ANSWER.search(source, pos):
        public.append(source[pos:match.start()])
        start = pos = match.end()
        depth = 1
        while depth and pos < len(source):
            char = source[pos]
            if char == "\\":
                pos += 2
                continue
            depth += (char == "{") - (char == "}")
            pos += 1
        phrases.update(re.findall(r"[\u3400-\u9fff]{12}", source[start:pos - 1]))
    public.append(source[pos:])
    # 题干常写作“图~\ref{...}”，解析则照排“图乙”。两者指同一处时也应排除。
    labels = dict(re.findall(r"\\newlabel\{([^{}]+)\}\{\{([^{}]*)\}", aux))
    printed = re.sub(r"\\(?:ref|eqref)\*?\{([^{}]+)\}", lambda m: labels.get(m[1], m[0]), "".join(public))
    visible = "".join(HAN.findall(printed))
    return sorted(phrase for phrase in phrases if phrase not in visible)


def check(directory: Path) -> None:
    name = directory.name
    pdfs, texts = [], []
    for edition in ("学生版", "教师版"):
        log = directory / f"{name}_{edition}.log"
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if LOG_ERROR.search(line):
                raise ValueError(f"{log.name}：{line}")
        pdf = directory / f"{name}_{edition}.pdf"
        pdfs.append(pdf)
        text = subprocess.check_output(["pdftotext", "-raw", str(pdf), "-"], encoding="utf-8")
        texts.append("".join(text.split()))

    student, teacher = texts
    if student == teacher:
        # 纯作图题的师生版可能只有图不同。逐页渲染后比较，忽略文件名、元数据等差别。
        rendered = [subprocess.check_output(["pdftoppm", "-gray", "-r", "36", str(pdf)]) for pdf in pdfs]
        if rendered[0] == rendered[1]:
            raise ValueError("学生版和教师版的文字、页面渲染均相同")
    tex = (directory / f"{name}.tex").read_text(encoding="utf-8")
    aux = (directory / f"{name}_学生版.aux").read_text(encoding="utf-8")
    phrases = solution_phrases(tex, aux)
    for phrase in phrases:
        if phrase in student:
            raise ValueError(f"学生版出现教师答案或解析中的文字“{phrase}”")
    if phrases and not any(phrase in teacher for phrase in phrases):
        raise ValueError("教师版中未找到源码答案或解析的专有文字")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", type=Path, help="题卷或专题目录")
    directory = ap.parse_args().directory.resolve()
    try:
        check(directory)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"{directory}：PDF 验收失败，{error}")
