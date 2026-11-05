#!/usr/bin/env python3
"""PDF 在 GitHub Release 中的文件名和下载地址。

PDF 不放在仓库里，而是由 .github/workflows/release.yml 编译后上传到 Release「pdf」。
GitHub 会改写 Release 附件名中的汉字，所以上传时改用拼音：
  2024_北京_学生版.pdf        → 2024-beijing-student.pdf
  动量与碰撞_教师版.pdf       → zhuanti-dongliang-yu-pengzhuang-teacher.pdf
知识点索引、答案速查和 README 中的 PDF 链接都指向 Release 中的这些文件。

用法（发布 PDF 的 workflow 用）：
  python3 scripts/pdf_names.py assets             每行一个“本地编译出的 PDF<TAB>Release 中的文件名”
  python3 scripts/pdf_names.py missing <清单>     <清单> 是 Release 现有附件名（每行一个），列出缺了 PDF 的卷
  python3 scripts/pdf_names.py stale <清单>       列出 Release 中已经没有对应卷的附件
  python3 scripts/pdf_names.py notes <提交>       生成 Release 说明：全部试卷和专题练习的下载链接

新增地区或专题时，在下面的表里加上它的拼音名；仓库改名后改 REPO，再运行 python3 scripts/gen_index.py。
只用 Python 标准库。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = "titleROC/-"
RELEASE_TAG = "pdf"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/{RELEASE_TAG}"
DOWNLOAD = f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}"

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "LaTeX源码"
VERSIONS = {"学生版": "student", "教师版": "teacher"}
REGIONS = {
    "全国理综": "quanguo-lizong", "全国理综Ⅰ": "quanguo-lizong-1", "全国理综Ⅱ": "quanguo-lizong-2",
    "全国理综Ⅲ": "quanguo-lizong-3", "全国新课标": "quanguo-xinkebiao", "全国甲卷": "quanguo-jia",
    "全国乙卷": "quanguo-yi", "北京": "beijing", "天津": "tianjin", "上海": "shanghai",
    "1月浙江": "zhejiang-1yue", "6月浙江": "zhejiang-6yue", "7月浙江": "zhejiang-7yue", "山东": "shandong",
    "江苏": "jiangsu", "安徽": "anhui", "江西": "jiangxi", "福建": "fujian", "广东": "guangdong",
    "河北": "hebei", "河南": "henan", "湖北": "hubei", "湖南": "hunan", "海南": "hainan", "辽宁": "liaoning",
    "重庆": "chongqing", "四川": "sichuan", "云南": "yunnan", "贵州": "guizhou", "广西": "guangxi",
    "甘肃": "gansu", "陕晋宁青": "shaan-jin-ning-qing", "陕晋青宁": "shaan-jin-qing-ning",
    "黑吉辽内": "hei-ji-liao-nei", "黑吉辽": "hei-ji-liao",
}
TOPICS = {"自感与涡流": "zigan-yu-woliu", "动量与碰撞": "dongliang-yu-pengzhuang"}
# 同一年内各卷在 Release 说明中的顺序（与 README 的收录表一致）
ORDER = list(REGIONS)


def paper_asset(year: str, region: str, version: str) -> str:
    return f"{year}-{REGIONS[region]}-{VERSIONS[version]}.pdf"


def topic_asset(topic: str, version: str) -> str:
    return f"zhuanti-{TOPICS[topic]}-{VERSIONS[version]}.pdf"


def paper_url(year: str, region: str, version: str) -> str:
    return f"{DOWNLOAD}/{paper_asset(year, region, version)}"


def topic_url(topic: str, version: str) -> str:
    return f"{DOWNLOAD}/{topic_asset(topic, version)}"


def papers() -> list[tuple[str, str]]:
    """LaTeX源码/ 中的全部试卷 [(年份, 地区)]，按年份从新到旧、卷按 ORDER 排列"""
    found = [(d.parent.name, d.name) for d in SRC.glob("[0-9][0-9][0-9][0-9]/*") if (d / "Makefile").is_file()]
    return sorted(found, key=lambda p: (-int(p[0]), ORDER.index(p[1]) if p[1] in ORDER else len(ORDER), p[1]))


def topics() -> list[str]:
    return sorted(d.name for d in (SRC / "专题练习").glob("*") if (d / "Makefile").is_file())


def entries() -> list[tuple[str, str, str]]:
    """[(编译目标, 本地 PDF 路径, Release 文件名)]，编译目标是 scripts/build_gaokao_pdfs.sh 接受的参数"""
    out = []
    for year, region in papers():
        for v in VERSIONS:
            out.append((f"{year}/{region}", f"高考真题/{year}/{year}_{region}_{v}.pdf", paper_asset(year, region, v)))
    for t in topics():
        for v in VERSIONS:
            out.append((f"专题练习/{t}", f"专题练习/{t}_{v}.pdf", topic_asset(t, v)))
    return out


def release_notes(commit: str) -> str:
    lines = [
        "仓库中全部高考真题试卷和专题练习的 PDF，由 GitHub Actions 根据 `LaTeX源码/` 自动编译，默认分支更新时随之更新。",
        "",
        f"编译依据的提交：`{commit}`",
        "",
        "GitHub 会改写附件名中的汉字，所以文件名用拼音：`<年份>-<地区>-student.pdf` 是学生版（只有试题），"
        "`-teacher.pdf` 是教师版（含答案和详解）。按知识点找题、对答案，见仓库中的知识点索引和答案速查。",
    ]
    year = None
    for y, region in papers():
        if y != year:
            year = y
            lines += ["", f"### {y} 年", "", "| 试卷 | 学生版 | 教师版 |", "| :-- | :-- | :-- |"]
        lines.append(f"| {region} | [下载]({paper_url(y, region, '学生版')}) | [下载]({paper_url(y, region, '教师版')}) |")
    lines += ["", "### 专题练习", "", "| 专题 | 学生版 | 教师版 |", "| :-- | :-- | :-- |"]
    for t in topics():
        lines.append(f"| {t} | [下载]({topic_url(t, '学生版')}) | [下载]({topic_url(t, '教师版')}) |")
    return "\n".join(lines) + "\n"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        items = entries()
    except KeyError as e:
        print(f"scripts/pdf_names.py 中没有「{e.args[0]}」的拼音名，请在 REGIONS 或 TOPICS 中加上", file=sys.stderr)
        return 1
    if cmd == "assets" and len(sys.argv) == 2:
        for _, local, asset in items:
            print(f"{local}\t{asset}")
    elif cmd in ("missing", "stale") and len(sys.argv) == 3:
        existing = {line.strip() for line in Path(sys.argv[2]).read_text("utf-8").splitlines() if line.strip()}
        if cmd == "missing":
            for target in dict.fromkeys(t for t, _, asset in items if asset not in existing):
                print(target)
        else:
            expected = {asset for _, _, asset in items}
            for name in sorted(existing - expected):
                print(name)
    elif cmd == "notes" and len(sys.argv) == 3:
        sys.stdout.write(release_notes(sys.argv[2]))
    else:
        print(__doc__.strip().split("\n\n")[2], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
