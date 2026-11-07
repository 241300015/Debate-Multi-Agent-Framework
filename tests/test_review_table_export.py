"""Review-table LaTeX generation and PDF export tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from debate_agent_framework.services.review_table_export import (
    build_review_table_data,
    chapter_advice_from_result,
    find_tectonic,
    latex_escape,
    overall_grade,
    parse_student_meta,
    render_review_table,
)


def test_parse_student_meta() -> None:
    assert parse_student_meta("201300020-吴智超.pdf") == ("201300020", "吴智超")
    assert parse_student_meta("201300020_吴智超.pdf") == ("201300020", "吴智超")
    assert parse_student_meta("thesis.pdf") == ("", "")
    assert parse_student_meta(None) == ("", "")


def test_overall_grade_bands() -> None:
    assert overall_grade(100) == "优秀"
    assert overall_grade(90) == "优秀"
    assert overall_grade(89) == "良好"
    assert overall_grade(75) == "良好"
    assert overall_grade(74) == "合格"
    assert overall_grade(60) == "合格"
    assert overall_grade(59) == "不合格"


def test_chapter_advice_from_result() -> None:
    result = {
        "synthesis": {
            "chapter_evaluation": {
                "chapter_1": {
                    "chapter_data": {
                        "chapter_name": "第一章 绪论",
                        "chapter_remark": "补充问题定义。",
                    }
                },
                "chapter_3": {
                    "chapter_data": {
                        "chapter_name": "第三章 实验",
                        "chapter_remark": "增加消融实验。",
                    }
                },
            }
        }
    }
    assert chapter_advice_from_result(result) == [
        ("第一章 绪论", "补充问题定义。"),
        ("第三章 实验", "增加消融实验。"),
    ]
    assert chapter_advice_from_result({}) == []
    assert chapter_advice_from_result(None) == []


def test_latex_escape() -> None:
    assert latex_escape("100%_ac_cd<&>") == "100\\%\\_ac\\_cd<\\&>"
    assert latex_escape("纯中文&特殊") == "纯中文\\&特殊"


def test_build_review_table_data_maps_scores() -> None:
    data = build_review_table_data(
        paper_title="步态识别系统",
        source_filename="201300020-吴智超.pdf",
        paper_type="工程实现",
        reviewer_name="teacher01",
        section_scores=[3, 2, 1, 0] * 4 + [3, 2],
        total_score=91,
        advice_content="补充实验。",
        chapter_advice=[("第一章", "补充背景")],
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
    )
    assert data.student_no == "201300020"
    assert data.student_name == "吴智超"
    assert len(data.entries) == 18
    assert [entry.level for entry in data.entries][:4] == [3, 2, 1, 0]
    assert [entry.index for entry in data.entries] == list(range(1, 19))


def test_render_review_table_layout() -> None:
    data = build_review_table_data(
        paper_title="步态识别系统",
        source_filename="201300020-吴智超.pdf",
        paper_type="工程实现",
        reviewer_name="teacher01",
        section_scores=[3] * 18,
        total_score=100,
        advice_content="建议补充对比实验。",
        chapter_advice=[("第一章 绪论", "建议补充研究背景。")],
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
    )
    tex = render_review_table(data)
    assert "\\documentclass[UTF8]{article}" in tex
    assert "\\usepackage[UTF8]{ctex}" in tex
    assert "\\checkmark" in tex  # 勾选符号
    # 官方模板的四个评议分组
    group_rows = {"论文格式": 6, "论文选题": 3, "论文水平": 2, "论文质量": 3}
    for group, rows in group_rows.items():
        assert f"\\multirow{{{rows}}}{{*}}{{{group}}}" in tex
    assert "请参照评分标准，对论文打分" in tex
    assert "总体评价（给出百分制总评成绩" in tex
    assert "论文修改建议:" in tex
    # 水印页脚
    assert "睿文智评AI预审评估系统通过大语言模型生成" in tex
    # 学生信息与勾选占位符
    assert "\\newcommand{\\studentid}{201300020}" in tex
    assert "\\newcommand{\\studentname}{吴智超}" in tex
    assert "\\newcommand{\\papertitle}{步态识别系统}" in tex
    assert "\\newcommand{\\formatScoreOneA}{\\checkmark}" in tex
    assert "\\newcommand{\\qualityScoreThreeA}{\\checkmark}" in tex
    assert "\\newcommand{\\totalScore}{100}" in tex
    # 建议内容进入 suggestions 占位符
    assert "[第一章 绪论] 建议补充研究背景。" in tex
    assert "建议补充对比实验。" in tex


def test_render_review_table_marks_follow_levels() -> None:
    data = build_review_table_data(
        paper_title="步态识别系统",
        source_filename="201300020-吴智超.pdf",
        paper_type="工程实现",
        reviewer_name="teacher01",
        section_scores=[3, 2, 1, 0] * 4 + [3, 2],
        total_score=88,
        advice_content="",
        chapter_advice=[],
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
    )
    tex = render_review_table(data)
    assert "\\newcommand{\\formatScoreOneA}{\\checkmark}" in tex  # 3 -> 优秀
    assert "\\newcommand{\\formatScoreTwoB}{\\checkmark}" in tex  # 2 -> 良好
    assert "\\newcommand{\\formatScoreThreeC}{\\checkmark}" in tex  # 1 -> 一般
    assert "\\newcommand{\\formatScoreFourD}{\\checkmark}" in tex  # 0 -> 较差
    assert "\\newcommand{\\levelScoreSixC}{\\checkmark}" in tex
    assert "\\newcommand{\\qualityScoreOneD}{\\checkmark}" in tex
    assert "\\newcommand{\\qualityScoreThreeB}{\\checkmark}" in tex
    assert "\\newcommand{\\suggestions}{}" in tex


@pytest.mark.parametrize("advice_case", ["empty", "short", "long"])
def test_review_pdf_keeps_suggestions_inside_frames(
    tmp_path: Path,
    advice_case: str,
) -> None:
    """Exercise actual TeX pagination rather than just inspecting its source."""
    pdfplumber = pytest.importorskip("pdfplumber")

    def color_channels(color: float | tuple[float, ...] | None) -> tuple[float, ...]:
        if isinstance(color, (int, float)):
            return (float(color),)
        return tuple(color) if color is not None else (0.0,)

    xelatex = shutil.which("xelatex")
    tectonic = find_tectonic() if not xelatex else None
    if not xelatex and not tectonic:
        pytest.skip("PDF layout regression requires XeLaTeX or Tectonic")

    # A single chapter must be able to continue through several pages. Splitting
    # only between chapters does not solve the original fixed-height overflow.
    repeated_advice = "补充实验数据来源并说明样本筛选过程，列出评价指标及对照组。"
    long_identifier = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789" * 16
    special_text = r"百分比100%_字段&参数{对象}\目录"
    is_long = advice_case == "long"
    short_advice = "" if advice_case == "empty" else "补充对比实验，并完善参考文献。"
    data = build_review_table_data(
        paper_title="基于多智能体协作的学术论文自动评审方法与实验分析" * (5 if is_long else 1),
        source_filename="202600001-测试学生.pdf",
        paper_type="工程实现",
        reviewer_name="layout-regression",
        section_scores=[3, 2, 1, 0] * 4 + [3, 2],
        total_score=88,
        advice_content=(
            "综合建议首行。\r\n综合建议次行。\r\n\r\n"
            f"{special_text}\n{long_identifier}\n综合建议结束标记。"
        ) if is_long else short_advice,
        chapter_advice=[
            ("单章跨页测试", "章节开始标记。" + repeated_advice * 190 + "章节结束标记。"),
            ("下一章", "后续章节建议完整保留。"),
        ] if is_long else [],
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
    )
    tex_path = tmp_path / f"review-{advice_case}.tex"
    tex_path.write_text(render_review_table(data), encoding="utf-8")
    if xelatex:
        command = [
            xelatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-output-directory={tmp_path}",
            str(tex_path),
        ]
    else:
        command = [
            str(tectonic),
            "-X",
            "compile",
            "--keep-logs",
            "--outdir",
            str(tmp_path),
            str(tex_path),
        ]
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    log_path = tex_path.with_suffix(".log")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"Overfull \\[hv]box", log), log

    with pdfplumber.open(tex_path.with_suffix(".pdf")) as pdf:
        full_text = "".join(
            char["text"] for page in pdf.pages for char in page.chars
            if not char["text"].isspace()
        )
        assert data.paper_title in full_text
        advice_pages = [
            page for page in pdf.pages if page.search("论文修改建议")
        ]
        if is_long:
            assert len(advice_pages) >= 3
        else:
            assert len(pdf.pages) == 2
            assert len(advice_pages) == 1
        frame_positions: set[tuple[float, float]] = set()
        body_texts: list[str] = []
        for index, page in enumerate(advice_pages):
            heading = page.search("论文修改建议")[0]
            # Select the enclosing outline, rather than its separate title and
            # background rectangles. Gray watermark glyphs are outside the form.
            frames = [
                rect for rect in page.rects
                if rect["width"] > page.width / 2 and rect["height"] > 20
            ]
            assert frames, f"Missing closed suggestion frame on page {page.page_number}"
            frame = max(frames, key=lambda rect: rect["width"] * rect["height"])
            frame_positions.add((round(frame["x0"], 2), round(frame["x1"], 2)))
            assert frame["bottom"] < page.height - 40
            # Break settings can accidentally remove the top/bottom rule.
            # Every white interior must leave a visible closed outer border.
            interiors = [
                rect for rect in page.rects
                if rect["width"] > page.width / 2
                if all(channel >= 0.9 for channel in color_channels(rect["non_stroking_color"]))
            ]
            assert interiors
            for interior in interiors:
                assert interior["x0"] - frame["x0"] >= 0.4
                assert frame["x1"] - interior["x1"] >= 0.4
                assert interior["top"] - frame["top"] >= 0.4
                assert frame["bottom"] - interior["bottom"] >= 0.4
            form_chars = [
                char for char in page.chars
                if char["top"] >= heading["top"] - 1
                and not char["text"].isspace()
                and all(channel <= 0.1 for channel in color_channels(char["non_stroking_color"]))
            ]
            assert form_chars
            for char in form_chars:
                assert frame["x0"] - 1 <= char["x0"] <= char["x1"] <= frame["x1"] + 1
                assert frame["top"] - 1 <= char["top"] <= char["bottom"] <= frame["bottom"] + 1
            body_text = "".join(
                char["text"] for char in form_chars
                if char["top"] > heading["bottom"] + 1
            )
            body_texts.append(body_text)
            # The dated signature belongs to the final frame only. Excluding
            # the gray footer also excludes its separate generated-at date.
            has_signature = bool(re.search(r"\d{4}年\d{2}月\d{2}日", body_text))
            assert has_signature == (index == len(advice_pages) - 1)
            if index:
                assert page.search("论文修改建议.*续")

        assert len(frame_positions) == 1
        frame_left, frame_right = next(iter(frame_positions))
        scoring_tables = 0
        for page in pdf.pages:
            vertical_rules = [
                line for line in page.lines
                if line["width"] < 0.1 and line["height"] > 5
            ]
            if vertical_rules:
                scoring_tables += 1
                assert min(line["x0"] for line in vertical_rules) == pytest.approx(frame_left, abs=1)
                assert max(line["x1"] for line in vertical_rules) == pytest.approx(frame_right, abs=1)
        assert scoring_tables == 2
        compact_text = "".join(body_texts)
        if not is_long:
            assert short_advice in compact_text
            return
        assert compact_text.count(repeated_advice) == 190
        for text in (
            "章节开始标记。",
            "章节结束标记。",
            "后续章节建议完整保留。",
            "综合建议首行。",
            "综合建议次行。",
            special_text,
            long_identifier,
            "综合建议结束标记。",
        ):
            assert text in compact_text

        page = next(page for page in advice_pages if page.search("综合建议首行。"))
        assert page.search("综合建议次行。")[0]["top"] > page.search("综合建议首行。")[0]["bottom"]
