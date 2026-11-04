#!/usr/bin/env python3
"""根据 LaTeX源码/ 中每道题的标注，生成「知识点索引/」和「答案速查/」。

用法：
  python3 scripts/gen_index.py            重新生成 知识点索引/ 和 答案速查/
  python3 scripts/gen_index.py --check    只检查这两个目录是否是最新的（不是时以状态 1 退出）

每道题的源文件里都有题库平台的标注（%% chapter、%% point、%% type、%% score、%% degree 等）。
本脚本据此按章节、知识点汇总题目，并从选项命令的 answer= 和 \\xzanswer 读出选择题答案。
标注和题目本身对不上的（例如标成单选题、答案却是 AD），按题目结构推断题型，列入 知识点索引/存疑清单.md。
只用 Python 标准库；源文件不会被修改。
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "LaTeX源码"
INDEX_DIR = "知识点索引"
ANSWER_DIR = "答案速查"
CSV_NAME = "题目清单.csv"
ISSUES_NAME = "存疑清单.md"
GENERATED_NOTE = "由 [`scripts/gen_index.py`](../scripts/gen_index.py) 根据 `LaTeX源码/` 中的标注自动生成，请勿手改。"

# 章节按教材顺序排列；未列出的章节排在最后
CHAPTER_ORDER = [
    "直线运动", "力物体的平衡", "运动和力", "曲线运动", "功和能", "机械振动", "机械波", "气体性质",
    "电场", "电路", "磁场", "电磁感应", "交流电", "光学", "原子和原子核", "量子论简介", "相对论简介", "其他",
]
# 同一年内各卷的顺序（与仓库 README 的收录表一致）；未列出的排在最后
PAPER_ORDER = [
    "全国理综", "全国理综Ⅰ", "全国理综Ⅱ", "全国理综Ⅲ", "全国新课标", "全国甲卷", "全国乙卷",
    "北京", "天津", "上海", "1月浙江", "6月浙江", "7月浙江", "山东", "江苏", "安徽", "江西", "福建",
    "广东", "河北", "河南", "湖北", "湖南", "海南", "辽宁", "重庆", "四川", "云南", "贵州", "广西",
    "甘肃", "陕晋宁青", "陕晋青宁", "黑吉辽内", "黑吉辽",
]
CHOICE_TYPES = ("单选题", "多选题")

CHOICE_MACRO_RE = re.compile(r"\\(?:two|three|four|five|six|seven|eight|nine)choices\b")
CHOICES_RE = re.compile(r"\\(?:two|three|four|five|six|seven|eight|nine)choices\s*\[([^\]]*)\]")
XZ_RE = re.compile(r"\\xzanswer\{([^{}]*)\}")


@dataclass
class Question:
    year: str
    paper: str
    pos: int                 # PDF 上印的题号（题目在源文件中的顺序）
    number: str              # 源文件 %% number 标注的原题号
    tag_type: str            # 平台标注的题型
    tag_answer: str = ""     # 平台标注的答案（%% answer 注释，非选择题常是无意义的字母）
    type: str = ""           # 索引采用的题型
    type_note: str = ""      # 题型与标注不符时的说明
    inferred: bool = False   # 题型是否按题目结构推断
    chapter: str = ""
    point: str = ""
    score: str = ""          # 空表示缺失
    degree: str = ""         # 空表示缺失
    answers: list[str] = field(default_factory=list)
    pure_choice: bool = False
    answer_missing: bool = False  # 有选项、但源文件没有标出答案
    options_missing: bool = False  # 答案是选项字母、但题干里没有选项
    snippet: str = ""

    @property
    def num_label(self) -> str:
        """PDF 题号；与原题号不同时括注原题号"""
        return str(self.pos) if self.number == str(self.pos) else f"{self.pos}（原 {self.number}）"

    @property
    def difficulty(self) -> str:
        return f"{int(self.degree) / 1000:.2f}" if self.degree else ""

    def pdf(self, version: str) -> str:
        return f"高考真题/{self.year}/{self.year}_{self.paper}_{version}.pdf"


# ---------------------------------------------------------------------------
# 题干开头：把 LaTeX 粗略转成一行纯文本，只用来帮助辨认题目
# ---------------------------------------------------------------------------
def load_units() -> dict[str, str]:
    """PhyUnit.sty 中每个单位命令行尾的注释就是它的写法，如 `\\NewDocumentCommand \\UkW ... % kW （功率）`"""
    units = {}
    sty = SRC / "PhyUnit.sty"
    if sty.exists():
        for m in re.finditer(r"^\\NewDocumentCommand\s*\\(U\w+)\b.*?%\s*([^\s（(]+)", sty.read_text("utf-8"), re.M):
            units[m.group(1)] = m.group(2)
    return units


UNITS = load_units()
GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "eta": "η",
    "theta": "θ", "lambda": "λ", "mu": "μ", "nu": "ν", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ",
    "phi": "φ", "varphi": "φ", "omega": "ω", "Delta": "Δ", "Phi": "Φ", "Omega": "Ω", "Sigma": "Σ",
}
SYMBOLS = {
    "times": "×", "cdot": "·", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "approx": "≈",
    "pm": "±", "sim": "~", "infty": "∞", "to": "→", "rightarrow": "→", "perp": "⊥", "parallel": "∥",
    "angle": "∠", "triangle": "△", "prime": "′", "cdots": "…", "ldots": "…", "degree": "°",
    "left": "", "right": "", "quad": " ", "qquad": " ", "mathrm": "", "rm": "",
}
SUP = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")
SUB = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


def _script(text: str, table: dict, caret: str) -> str:
    text = text.strip()
    if text and all(c in "0123456789+-=()" for c in text):
        return text.translate(table)
    return text if caret == "_" else f"^({text})" if len(text) > 1 else f"^{text}"


def math_to_text(m: str) -> str:
    """简单公式转成纯文本（如 v₀、10⁻⁹ m、T/8），复杂的用“…”代替"""
    s = re.sub(r"\\(U\w+)(?:\[[^\]]*\])?", lambda x: " " + UNITS[x.group(1)] if x.group(1) in UNITS else x.group(0), m)
    s = re.sub(r"\\(?:mathrm|text|mathbf|mathit|boldsymbol|operatorname|vec|overrightarrow)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\{\}\s*\^\s*\{?\\circ\}?|\^\s*\{?\\circ\}?", "°", s)

    def frac(x: re.Match) -> str:
        a, b = (f"({t})" if re.search(r"[\s+\-]", t.strip()) else t.strip() for t in (x.group(1), x.group(2)))
        return f"{a}/{b}"
    s = re.sub(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", frac, s)
    s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", lambda x: "√" + (x.group(1) if len(x.group(1)) == 1 else f"({x.group(1)})"), s)
    s = re.sub(r"\\([A-Za-z]+)", lambda x: GREEK.get(x.group(1), SYMBOLS.get(x.group(1), "\0")), s)
    s = re.sub(r"\\[,;:! ]", " ", s)
    if "\0" in s or "\\" in s:
        return "…"
    s = re.sub(r"\^\{([^{}]*)\}|\^(\S)", lambda x: _script(x.group(1) or x.group(2), SUP, "^"), s)
    s = re.sub(r"_\{([^{}]*)\}|_(\S)", lambda x: _script(x.group(1) or x.group(2), SUB, "_"), s)
    s = re.sub(r"\s+", " ", s.replace("{", "").replace("}", "")).strip()
    return "…" if not s or len(s) > 24 else s


def drop_macros_with_args(s: str, pattern: str) -> str:
    """删除命令及其可选参数和后面所有花括号参数（花括号可嵌套），用于图片命令"""
    out, i = [], 0
    for m in re.finditer(pattern, s):
        if m.start() < i:
            continue
        out.append(s[i:m.start()])
        j = m.end()
        while True:
            k = j
            while k < len(s) and s[k] in " \t\n":
                k += 1
            if k < len(s) and s[k] == "[":
                end = s.find("]", k)
                j = end + 1 if end != -1 else len(s)
                continue
            if k < len(s) and s[k] == "{":
                depth = 0
                for t in range(k, len(s)):
                    depth += {"{": 1, "}": -1}.get(s[t], 0)
                    if depth == 0:
                        break
                j = t + 1
                continue
            break
        i = j
    out.append(s[i:])
    return "".join(out)


SNIPPET_CUT = re.compile(r"\\xzanswer|\\\w+choices|\\begin\{|\\jdanswer|^%% answer:", re.M)


def snippet(stem: str, limit: int = 32) -> str:
    s = re.sub(r"(?<!\\)%.*", "", stem)
    s = drop_macros_with_args(s, r"\\(?:\w*picture|includegraphics|includesvg)\*?")
    s = SNIPPET_CUT.split(s, 1)[0]
    s = re.sub(r"\\tkanswer\s*(?:\[[^\]]*\])?\s*\{(?:[^{}]|\{[^{}]*\})*\}", "____", s)
    s = re.sub(r"\\(?:ref|eqref|label|cite)\s*\{[^{}]*\}", "", s)
    s = re.sub(r"\$\$(.+?)\$\$|\$([^$]+)\$|\\\((.+?)\\\)", lambda x: math_to_text(next(g for g in x.groups() if g)), s, flags=re.S)
    s = re.sub(r"\\[%&_#$]", lambda x: x.group(0)[1], s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", s)
    s = re.sub(r"[{}~]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?:…\s*){2,}", "…", s)
    s = re.sub(r"\s*([，。；：、（）“”！？])\s*", r"\1", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", s)  # 删掉 \ref 等留下的汉字间空格
    return s if len(s) <= limit else s[:limit].rstrip("，、；： ") + "…"


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
def guess_nonchoice(stem: str, before_memo: str) -> str:
    tk = "\\tkanswer" in stem
    sub = "\\begin{enumerate}" in before_memo
    if tk and not sub and "\\jdanswer" not in before_memo:
        return "填空题"
    return "实验题" if tk else "计算题"


def classify(q: Question, stem: str, before_memo: str) -> None:
    has_sub = bool(re.search(r"\\begin\{enumerate\}|（2）|\(2\)", stem))
    has_options = bool(q.answers) or bool(CHOICE_MACRO_RE.search(stem))
    q.pure_choice = has_options and not has_sub and "\\tkanswer" not in stem
    tag = q.tag_type
    if tag in CHOICE_TYPES:
        if not q.answers and q.pure_choice:
            q.type, q.answer_missing = tag, True
        elif not q.answers:
            q.type, q.inferred = guess_nonchoice(stem, before_memo), True
            q.type_note = "正文中没有选项和选择题答案"
        elif tag == "单选题" and q.pure_choice and any(len(a) > 1 for a in q.answers):
            q.type = "多选题"
            q.type_note = f"答案为 {'、'.join(q.answers)}"
        else:
            q.type = tag
    elif q.pure_choice and q.answers:
        q.type = "多选题" if any(len(a) > 1 for a in q.answers) else "单选题"
        q.type_note = (f"题干里没有选项，答案 {'、'.join(q.answers)} 写在 \\jdanswer 中" if q.options_missing
                       else f"只有一问，是选择题，答案为 {'、'.join(q.answers)}")
    else:
        q.type = tag or "未标注"
        q.answer_missing = q.pure_choice and not q.answers
        if not tag:
            q.type_note = "没有题型标注"


def parse_paper(year: str, paper: str, tex: Path) -> list[Question]:
    questions = []
    blocks = re.split(r"^%% number:", tex.read_text("utf-8"), flags=re.M)[1:]
    for pos, block in enumerate(blocks, 1):
        number, _, rest = block.partition("\n")
        head, _, body = rest.partition("%% body:\n")
        meta = dict(re.findall(r"^%% (\w+):[ \t]*(.*?)[ \t]*$", head, flags=re.M))
        before_memo = body.split("%% memo:", 1)[0]
        stem = before_memo.split("%% answer:", 1)[0]
        answers = [m.group(1) for o in CHOICES_RE.findall(stem) if (m := re.search(r"answer\s*=\s*([A-Z]+)", o))]
        tag_answer = re.search(r"^%% answer:[ \t]*(.*?)[ \t]*$", before_memo, flags=re.M)
        # 题干没有选项、作答却只有选项字母：是丢了选项的选择题
        options_missing = False
        if not answers and not XZ_RE.search(stem) and not CHOICE_MACRO_RE.search(stem):
            jd = re.search(r"\\jdanswer\*?\{\s*([A-H]{1,5})\s*\}", before_memo)
            if jd:
                answers, options_missing = [jd.group(1)], True
        q = Question(
            year=year, paper=paper, pos=pos, number=number.strip(), tag_type=meta.get("type", ""),
            tag_answer=tag_answer.group(1) if tag_answer else "",
            chapter=meta.get("chapter", "") or "未分类", point=meta.get("point", "") or "未分类",
            score=meta.get("score", "") if meta.get("score", "") not in ("", "0") else "",
            degree=meta.get("degree", "") if meta.get("degree", "").isdigit() and meta.get("degree") != "0" else "",
            answers=answers or [a.strip() for a in XZ_RE.findall(stem) if a.strip()],
            options_missing=options_missing,
            snippet=snippet(stem),
        )
        classify(q, stem, before_memo)
        questions.append(q)
    return questions


def load_all() -> list[Question]:
    questions = []
    for ydir in sorted(p for p in SRC.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}", p.name)):
        for pdir in sorted(p for p in ydir.iterdir() if p.is_dir()):
            tex = pdir / f"{pdir.name}.tex"
            if tex.exists():
                questions += parse_paper(ydir.name, pdir.name, tex)
    return questions


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def order_key(names: list[str], name: str) -> tuple:
    return (names.index(name), "") if name in names else (len(names), name)


def paper_key(q: Question) -> tuple:
    return (q.year, order_key(PAPER_ORDER, q.paper))


class Slugger:
    """与 GitHub 生成标题锚点的规则一致：小写、去掉标点、空格变连字符，重名依次加 -1、-2"""

    def __init__(self) -> None:
        self.seen: Counter = Counter()

    def __call__(self, text: str) -> str:
        base = re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")
        n = self.seen[base]
        self.seen[base] += 1
        return base if n == 0 else f"{base}-{n}"


def cell(text: str) -> str:
    """表格单元格：转义 Markdown 会解析的字符（| 分列，* _ 强调，< > HTML 标签）"""
    for a, b in (("\\", "\\\\"), ("|", "\\|"), ("*", "\\*"), ("_", "\\_"), ("<", "&lt;"), (">", "&gt;"), ("\n", " ")):
        text = text.replace(a, b)
    return text


def type_cell(q: Question) -> str:
    return f"{q.type}\\*" if q.type_note else q.type


def pdf_links(q: Question, prefix: str = "../") -> str:
    return f"[学生版]({prefix}{q.pdf('学生版')}) · [教师版]({prefix}{q.pdf('教师版')})"


def year_range(qs: list[Question]) -> str:
    years = sorted({q.year for q in qs})
    return f"{years[0]}—{years[-1]}" if len(years) > 1 else years[0]


def render_chapter(chapter: str, qs: list[Question]) -> str:
    slug = Slugger()
    slug(chapter)  # 一级标题
    by_point: dict[str, list[Question]] = defaultdict(list)
    for q in qs:
        by_point[q.point].append(q)
    points = sorted(by_point, key=lambda p: (-len(by_point[p]), p))
    lines = [
        f"# {chapter}",
        "",
        f"共 {len(qs)} 题，分 {len(points)} 个知识点，题量多的在前；每个知识点内按年份从新到旧排列。"
        "题型带 * 的，平台标注和题目对不上，见[存疑清单](存疑清单.md)。",
        "",
        "[返回知识点索引](README.md)",
        "",
    ]
    lines += [f"- [{p}](#{slug(p)})（{len(by_point[p])}）" for p in points]
    for p in points:
        lines += ["", f"## {p}", "", "| 年份 | 试卷 | 题号 | 题型 | 分值 | 难度 | 题目 | PDF |", "| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |"]
        for q in sorted(by_point[p], key=lambda q: (-int(q.year), order_key(PAPER_ORDER, q.paper), q.pos)):
            lines.append(
                f"| {q.year} | {q.paper} | {q.num_label} | {type_cell(q)} | {q.score or '—'} | {q.difficulty or '—'} "
                f"| {cell(q.snippet) or '—'} | {pdf_links(q)} |"
            )
    return "\n".join(lines) + "\n"


def render_index_readme(qs: list[Question], chapters: list[str], by_chapter: dict) -> str:
    papers = {(q.year, q.paper) for q in qs}
    lines = [
        "# 知识点索引",
        "",
        f"按知识点查 {year_range(qs)} 年 {len(papers)} 套卷中的 {len(qs)} 道题。{GENERATED_NOTE}",
        "",
        "- 每个章节一页，章节内按知识点分组；章节和知识点用的是题库平台的分类（例如动量归在“运动和力”下）。",
        "- **题号**是 PDF 上印的题号。少数卷 PDF 题号和原卷题号不一致（上游合并、拆分了同号题，或原始材料缺题），"
        "这时括注原题号，如“17（原 16）”。",
        "- **题型、分值、难度**来自平台标注。难度是平台给的难度值，0—1，越小越难，仅供参考。",
        "- 题型带 * 的，平台标注和题目对不上，索引按题目结构作了订正或推断，见[存疑清单](存疑清单.md)。",
        "- **题目**是题干开头，公式只做了粗略转写，复杂的公式用“…”代替。",
        f"- 全部题目的表格版：[`{CSV_NAME}`]({CSV_NAME})，可以用 Excel 或 WPS 打开筛选。",
        f"- 选择题答案见[答案速查](../{ANSWER_DIR}/README.md)。",
        "",
        "| 章节 | 题数 | 知识点数 | 题量最多的知识点 |",
        "| :-- | --: | --: | :-- |",
    ]
    for ch in chapters:
        cqs = by_chapter[ch]
        top = Counter(q.point for q in cqs).most_common(3)
        lines.append(
            f"| [{ch}]({ch}.md) | {len(cqs)} | {len({q.point for q in cqs})} "
            f"| {'、'.join(f'{p}（{n}）' for p, n in top)} |"
        )
    return "\n".join(lines) + "\n"


def render_csv(qs: list[Question]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["年份", "试卷", "题号", "原题号", "题型", "标注题型", "分值", "难度", "章节", "知识点", "选择题答案", "题目"])
    for q in sorted(qs, key=lambda q: (paper_key(q), q.pos)):
        w.writerow([q.year, q.paper, q.pos, q.number, q.type, q.tag_type, q.score, q.difficulty, q.chapter, q.point,
                    "、".join(q.answers), q.snippet])
    return "\ufeff" + buf.getvalue()  # 带 BOM，Excel 才能正确识别 UTF-8


def ranges(pairs: list[tuple[int, int]]) -> str:
    """[(PDF 题号, 原题号)] → “4—6 → 5—7；17 → 16”"""
    groups: list[list[tuple[int, int]]] = []
    for p, n in pairs:
        if groups and p == groups[-1][-1][0] + 1 and n == groups[-1][-1][1] + 1:
            groups[-1].append((p, n))
        else:
            groups.append([(p, n)])
    return "；".join(f"{g[0][0]} → {g[0][1]}" if len(g) == 1 else f"{g[0][0]}—{g[-1][0]} → {g[0][1]}—{g[-1][1]}" for g in groups)


def render_issues(qs: list[Question]) -> str:
    papers: dict[tuple, list[Question]] = defaultdict(list)
    for q in qs:
        papers[(q.year, q.paper)].append(q)
    keys = sorted(papers, key=lambda k: (k[0], order_key(PAPER_ORDER, k[1])))

    typed = [q for q in qs if q.type_note and not q.options_missing]
    lines = [
        "# 存疑清单",
        "",
        "生成[知识点索引](README.md)和[答案速查](../答案速查/README.md)时发现的、源文件中需要核对的地方："
        "题库平台的标注和题目本身对不上、选择题缺选项或没标答案、缺少分值，以及 PDF 题号和原卷题号不一致。"
        "索引已按下表处理，源文件没有改动。这些问题大多来自上游的平台数据，可以反馈给上游。",
        "",
        GENERATED_NOTE,
        "",
        f"## 题型标注与题目不符（{len(typed)} 题）",
        "",
        "“按题目结构推断”的规则：只有填空的算填空题，有填空又有小问或作答的算实验题，其余算计算题。推断可能出错，以原卷为准。",
        "",
        "| 年份 | 试卷 | 题号 | 标注题型 | 实际情况 | 索引中按 |",
        "| :-- | :-- | :-- | :-- | :-- | :-- |",
    ]
    for q in sorted(typed, key=lambda q: (paper_key(q), q.pos)):
        lines.append(f"| {q.year} | {q.paper} | {q.num_label} | {q.tag_type or '—'} | {q.type_note} "
                     f"| {q.type}{'（按题目结构推断）' if q.inferred else ''} |")

    no_options = [q for q in qs if q.options_missing]
    lines += [
        "",
        f"## 选择题缺少选项（{len(no_options)} 题）",
        "",
        "题干以“（ ）”结尾、作答只有选项字母，但源文件里没有选项，学生版和教师版 PDF 中都看不到选项，需要对照原卷补上。",
        "",
        "| 年份 | 试卷 | 题号 | 标注题型 | 答案 | 索引中按 |",
        "| :-- | :-- | :-- | :-- | :-- | :-- |",
    ]
    lines += [f"| {q.year} | {q.paper} | {q.num_label} | {q.tag_type or '—'} | {'、'.join(q.answers)} | {q.type} |"
              for q in sorted(no_options, key=lambda q: (paper_key(q), q.pos))]

    no_answer = [q for q in qs if q.answer_missing]
    lines += [
        "",
        f"## 选择题没有标出答案（{len(no_answer)} 题）",
        "",
        "题目有选项，但选项命令里没有 `answer=`，正文里也没有 `\\xzanswer`，所以教师版不会标出答案，答案速查中显示为“？”。",
        "",
        "| 年份 | 试卷 | 题号 | 题型 | 源文件中的 `%% answer` 注释 |",
        "| :-- | :-- | :-- | :-- | :-- |",
    ]
    lines += [f"| {q.year} | {q.paper} | {q.num_label} | {q.type} | {cell(q.tag_answer) or '（空）'} |"
              for q in sorted(no_answer, key=lambda q: (paper_key(q), q.pos))]

    missing = [(k, [q for q in papers[k] if not q.score]) for k in keys]
    missing = [(k, ms) for k, ms in missing if ms]
    lines += [
        "",
        f"## 缺少分值（{len(missing)} 套卷、{sum(len(ms) for _, ms in missing)} 题）",
        "",
        "平台标注的分值为 0 或为空，索引中显示为“—”。",
        "",
        "| 年份 | 试卷 | 题号 |",
        "| :-- | :-- | :-- |",
    ]
    for (y, p), ms in missing:
        nums = f"全部 {len(ms)} 题" if len(ms) == len(papers[(y, p)]) else "、".join(q.num_label for q in ms)
        lines.append(f"| {y} | {p} | {nums} |")

    renumbered = []
    for k in keys:
        pqs = papers[k]
        diff = [(q.pos, int(q.number)) for q in pqs if q.number != str(q.pos) and q.number.isdigit()]
        if not diff:
            continue
        nums = [int(q.number) for q in pqs if q.number.isdigit()]
        notes = []
        gaps = sorted(set(range(1, max(nums) + 1)) - set(nums))
        if gaps:
            notes.append("缺 " + "、".join(map(str, gaps)))
        notes += [f"{n} 出现 {c} 次" for n, c in sorted(Counter(nums).items()) if c > 1]
        renumbered.append((k, "；".join(notes) or "顺序不同", ranges(diff)))
    lines += [
        "",
        f"## PDF 题号与原卷题号不一致（{len(renumbered)} 套）",
        "",
        "源文件按原卷题号标注（理综卷是上游按物理部分重编的题号），PDF 则按题目顺序连续编号。"
        "上游合并、拆分了同号题，或原始材料缺题时，两者就会错开。索引和答案速查一律用 PDF 题号，"
        "原因见 [`LaTeX源码/异常记录/`](../LaTeX源码/异常记录/) 中对应年份的记录。",
        "",
        "| 年份 | 试卷 | 源文件中的原题号 | PDF 题号 → 原题号 |",
        "| :-- | :-- | :-- | :-- |",
    ]
    lines += [f"| {y} | {p} | {note} | {mapping} |" for (y, p), note, mapping in renumbered]
    return "\n".join(lines) + "\n"


def answer_text(q: Question) -> str:
    label = q.num_label
    if not (q.pure_choice and q.type in CHOICE_TYPES) and not q.answer_missing:
        label += "（选择小问）"
    answer = "？" if q.answer_missing else "、".join(q.answers)
    if q.options_missing:
        answer += "（题干缺选项）"
    return label + ("" if label.endswith("）") else " ") + answer


def render_answers_year(year: str, qs: list[Question]) -> str:
    papers: dict[str, list[Question]] = defaultdict(list)
    for q in qs:
        papers[q.paper].append(q)
    note = "题号是 PDF 上印的题号，括号里是原卷题号（两者不同时才写）。“选择小问”是非选择题中的选择小问，按出现顺序列出。"
    if any(q.answer_missing for q in qs):
        note += "“？”表示源文件没有标出答案，见[存疑清单](../知识点索引/存疑清单.md)。"
    lines = [
        f"# {year} 年选择题答案",
        "",
        note,
        "",
        "[返回答案速查](README.md)",
        "",
        "| 试卷 | 答案 |",
        "| :-- | :-- |",
    ]
    for paper in sorted(papers, key=lambda p: order_key(PAPER_ORDER, p)):
        items = [answer_text(q) for q in papers[paper] if q.answers or q.answer_missing]
        teacher = papers[paper][0].pdf("教师版")
        lines.append(f"| [{paper}](../{teacher}) | {'　'.join(items) if items else '—（本卷没有带选项的小题，见教师版）'} |")
    return "\n".join(lines) + "\n"


def render_answers_readme(qs: list[Question], years: list[str]) -> str:
    lines = [
        "# 选择题答案速查",
        "",
        f"{year_range(qs)} 年各卷选择题的答案，用学生版做完后对答案用；详解见各卷教师版。{GENERATED_NOTE}",
        "",
        "- 题号是 PDF 上印的题号；少数卷和原卷题号不一致，括号里注明原题号，见[存疑清单](../知识点索引/存疑清单.md)。",
        "- “选择小问”是非选择题中的选择小问，如全国卷选考题的第（1）问、上海卷综合题中的选择，按出现顺序列出。",
        "",
        "| 年份 | 套数 | 含选择答案的题 |",
        "| :-- | --: | --: |",
    ]
    for y in sorted(years, reverse=True):
        yqs = [q for q in qs if q.year == y]
        lines.append(f"| [{y}]({y}.md) | {len({q.paper for q in yqs})} | {sum(1 for q in yqs if q.answers or q.answer_missing)} |")
    return "\n".join(lines) + "\n"


def generate(qs: list[Question]) -> dict[str, str]:
    by_chapter: dict[str, list[Question]] = defaultdict(list)
    for q in qs:
        by_chapter[q.chapter].append(q)
    chapters = sorted(by_chapter, key=lambda c: order_key(CHAPTER_ORDER, c))
    years = sorted({q.year for q in qs})
    files = {f"{INDEX_DIR}/README.md": render_index_readme(qs, chapters, by_chapter)}
    files.update({f"{INDEX_DIR}/{ch}.md": render_chapter(ch, by_chapter[ch]) for ch in chapters})
    files[f"{INDEX_DIR}/{CSV_NAME}"] = render_csv(qs)
    files[f"{INDEX_DIR}/{ISSUES_NAME}"] = render_issues(qs)
    files[f"{ANSWER_DIR}/README.md"] = render_answers_readme(qs, years)
    files.update({f"{ANSWER_DIR}/{y}.md": render_answers_year(y, [q for q in qs if q.year == y]) for y in years})
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="只检查生成结果是否和仓库里的一致")
    args = ap.parse_args()

    qs = load_all()
    if not qs:
        print("LaTeX源码/ 中没有找到试卷", file=sys.stderr)
        return 1
    missing_pdfs = sorted({p for q in qs for p in (q.pdf("学生版"), q.pdf("教师版")) if not (REPO / p).exists()})
    for p in missing_pdfs:
        print(f"警告：找不到 {p}，索引中的链接会失效", file=sys.stderr)

    files = generate(qs)
    stale = [
        p.relative_to(REPO).as_posix()
        for d in (INDEX_DIR, ANSWER_DIR) if (REPO / d).is_dir()
        for p in (REPO / d).iterdir()
        if p.suffix in (".md", ".csv") and p.relative_to(REPO).as_posix() not in files
    ]
    changed = [rel for rel, text in files.items()
               if not (REPO / rel).exists() or (REPO / rel).read_bytes() != text.encode("utf-8")]
    if args.check:
        for rel in changed:
            print(f"过期：{rel}", file=sys.stderr)
        for rel in stale:
            print(f"多余：{rel}", file=sys.stderr)
        if changed or stale:
            print("知识点索引/ 或 答案速查/ 不是最新的，请运行 python3 scripts/gen_index.py", file=sys.stderr)
            return 1
        print(f"知识点索引/ 和 答案速查/ 是最新的（{len(qs)} 题）")
        return 0

    for rel in changed:
        (REPO / rel).parent.mkdir(parents=True, exist_ok=True)
        (REPO / rel).write_bytes(files[rel].encode("utf-8"))
    for rel in stale:
        (REPO / rel).unlink()
    print(f"共 {len(qs)} 题；更新 {len(changed)} 个文件，删除 {len(stale)} 个过期文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
