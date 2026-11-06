from __future__ import annotations

from debate_agent_framework.ingestion import MarkdownPaperParser
from debate_agent_framework.schemas import PaperType


MARKDOWN = """# 多智能体论文评审研究

## 摘要
本文研究证据驱动的多智能体论文评审。

关键词：多智能体，论文评审；LangGraph

## 第一章 绪论
### 1.1 研究背景
本章介绍研究背景。

## 第二章 方法设计
### 2.1 总体架构
本文提出三个专家和一位 Chair。

## 第三章 实验验证
实验结果表明方法有效。

## 参考文献
[1] Example, 2026.

## 致谢
感谢指导教师。
"""


def test_markdown_parser_builds_review_input() -> None:
    result = MarkdownPaperParser().parse(
        MARKDOWN,
        paper_type=PaperType.METHOD,
        source_filename="fallback.pdf",
        mineru_batch_id="batch-1",
    )

    assert result.title == "多智能体论文评审研究"
    assert result.abstract.startswith("本文研究")
    assert result.keywords == ["多智能体", "论文评审", "LangGraph"]
    assert [chapter.chapter_name for chapter in result.chapters] == [
        "摘要",
        "第一章 绪论",
        "第二章 方法设计",
        "第三章 实验验证",
        "参考文献",
        "致谢",
    ]
    assert result.chapters[-1].reviewable is False
    assert result.chapters[0].reviewable is False
    assert result.references == ["[1] Example, 2026."]
    assert result.metadata["mineru_batch_id"] == "batch-1"


def test_markdown_parser_falls_back_to_single_chapter() -> None:
    result = MarkdownPaperParser().parse(
        "没有 Markdown 标题的正文",
        paper_type=PaperType.ENGINEERING,
        title="工程论文",
    )

    assert result.title == "工程论文"
    assert len(result.chapters) == 1
    assert result.chapters[0].content == "没有 Markdown 标题的正文"


def test_markdown_parser_prefers_cover_title_field() -> None:
    result = MarkdownPaperParser().parse(
        "# 南京大学\n\n题目：真正的论文标题\n\n# 第一章 绪论\n正文",
        paper_type=PaperType.THEORY,
    )

    assert result.title == "真正的论文标题"
    assert result.chapters[0].chapter_name == "第一章 绪论"


def test_markdown_parser_splits_numbered_chapters() -> None:
    result = MarkdownPaperParser().parse(
        """# 题目
\n## 1. 绪论\n绪论正文。\n\n## 1.1. 研究背景\n背景文字不应单独成章。\n\n## 2. 相关工作\n相关工作正文。\n\n## 5. 结论与展望\n结论正文。\n\n## 参考文献\n[1] Example, 2026.\n"""
    )

    assert [chapter.chapter_name for chapter in result.chapters] == [
        "1. 绪论",
        "2. 相关工作",
        "5. 结论与展望",
        "参考文献",
    ]
    assert [chapter.stage for chapter in result.chapters] == [
        "引言/绪论",
        "相关工作",
        "结论展望",
        "参考文献",
    ]
    assert all(chapter.reviewable for chapter in result.chapters[:-1])
    assert result.chapters[-1].reviewable is False
    assert "研究背景" in result.chapters[0].content
    assert "subsection" not in result.chapters[0].content


class _StubResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self._raw = {}

    raw = property(lambda self: self._raw)


class _StubClient:
    """仅返回预定 JSON 的假 ModelClient，不触发网络调用。"""

    def __init__(self, chapters: list[str]) -> None:
        import json

        self._payload = json.dumps(
            {"chapters": [{"chapter_title": t} for t in chapters]},
            ensure_ascii=False,
        )

    def complete(self, messages, *, options=None):
        return _StubResponse(self._payload)


FLAT_ENGLISH = (
    "Abstract\nWe study multi-agent debate.\n\n"
    "Introduction\nBackground.\n\n"
    "Method\nProposed framework.\n\n"
    "Experiment\nEvaluated.\n\n"
    "Conclusion\nSummary.\n"
)


def test_heuristic_degrades_flat_english_to_single_chapter() -> None:
    # 无客户端、默认两级关闭：英文无编号标题退化成单章“正文”，内容不丢
    result = MarkdownPaperParser().parse(FLAT_ENGLISH, title="EN")
    assert [c.chapter_name for c in result.chapters] == ["正文"]
    assert result.metadata["chapter_stage_source"] == "markdown_heuristic"


def test_llm_fallback_splits_suspicious_flat_english() -> None:
    # 两级切分开启 + 提供客户端：可疑单章论文由大模型辅助切成多个章节
    parser = MarkdownPaperParser(
        model_client=_StubClient(
            ["Abstract", "Introduction", "Method", "Experiment", "Conclusion"]
        ),
        llm_split_enabled=True,
    )
    result = parser.parse(FLAT_ENGLISH, title="EN")

    assert [c.chapter_name for c in result.chapters] == [
        "Abstract",
        "Introduction",
        "Method",
        "Experiment",
        "Conclusion",
    ]
    # 摘要不可评审，正文章节可评审
    assert result.chapters[0].reviewable is False
    assert all(c.reviewable for c in result.chapters[1:])
    # 正文必须来自原文（禁止模型生成内容替换）
    assert "Summary" in result.chapters[-1].content
    assert "Proposed framework" in result.chapters[2].content
    assert result.metadata["chapter_stage_source"] == "heuristic_then_llm_fallback"


def test_llm_fallback_not_used_for_normal_paper() -> None:
    # 规范编号论文不触发可疑判定，即使提供客户端也不用大模型
    parser = MarkdownPaperParser(
        model_client=_StubClient(
            ["摘要", "第一章 绪论", "第二章 方法", "第三章 实验"]
        ),
        llm_split_enabled=True,
    )
    result = parser.parse(MARKDOWN, title="规范")
    assert [c.chapter_name for c in result.chapters] == [
        "摘要",
        "第一章 绪论",
        "第二章 方法设计",
        "第三章 实验验证",
        "参考文献",
        "致谢",
    ]
    assert all(c.metadata.get("split_source") != "llm_fallback" for c in result.chapters)


class _StubClientBad:
    """返回非法 JSON，验证兜底失败回退启发式。"""

    def complete(self, messages, *, options=None):
        return _StubResponse("这不是合法 JSON")


def test_llm_fallback_failure_gracefully_returns_heuristic() -> None:
    parser = MarkdownPaperParser(
        model_client=_StubClientBad(), llm_split_enabled=True
    )
    result = parser.parse(FLAT_ENGLISH, title="EN")
    # 大模型失败不阻断主流程，回退到启发式单章兜底
    assert [c.chapter_name for c in result.chapters] == ["正文"]
