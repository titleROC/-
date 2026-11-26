"""答案速查中的选择小问应沿用题面编号。"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_index import answer_text, parse_paper


def render_answer(stem: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tex = Path(tmp) / "样卷.tex"
        tex.write_text("\\item\n%% number: 1\n%% type: 实验题\n%% body:\n" + stem, "utf-8")
        question, = parse_paper("0", "样卷", tex)
    return answer_text(question)


class ChoicePartTests(unittest.TestCase):
    def test_interleaved_numeric_blanks_keep_printed_item_numbers(self):
        stem = r"""
\begin{enumerate}
\item A．直尺 B．秒表。测长度选 \tkanswer{A}。
\item 长度为 \tkanswer{10} cm。
\item 测得的电流如何变化？\twochoices[answer=B]{变大}{变小}
\item 电流为 \tkanswer{2} mA。
\item A．直尺 B．秒表。测时间选 \tkanswer{B}。
\end{enumerate}
"""
        self.assertEqual(render_answer(stem), "1（选择小问）（1）A；（3）B；（5）B")

    def test_two_answers_share_one_printed_item_number(self):
        stem = r"""
\begin{enumerate}
\item 长度为 \tkanswer{10} cm。
\item A．直尺 B．秒表。测时间选 \tkanswer{B}，测长度选 \tkanswer{A}。
\end{enumerate}
"""
        self.assertEqual(render_answer(stem), "1（选择小问）（2）B、A")

    def test_unnumbered_blanks_remain_unnumbered(self):
        stem = r"A．直尺 B．秒表。测时间选 \tkanswer{B}，测长度选 \tkanswer{A}。"
        self.assertEqual(render_answer(stem), "1（选择小问）B、A")


if __name__ == "__main__":
    unittest.main()
