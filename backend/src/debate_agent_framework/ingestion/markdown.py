"""把 MinerU Markdown 确定性转换为 Debate 工作流输入。

章节切分采用“两级策略”：
1. 先跑无模型启发式解析（覆盖中文学位论文常见编号标题）；
2. 若解析结果“可疑”（退化成整篇单章等），再调用大模型进行辅助切分，
   模型只输出“章节边界标题 + 阶段”的清单，由本地代码把每个标题回映射到
   原始 Markdown 的实际位置并截取原文内容，保证章节正文始终来自原文，
   绝不用模型生成的内容替换。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Sequence

from ..schemas import ChapterInput, DebateReviewInput, PaperType

logger = logging.getLogger("debate.markdown")

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHAPTER = re.compile(r"^第\s*[一二三四五六七八九十百0-9]+\s*章")
_NUMBERED_CHAPTER = re.compile(r"^\d+\s*[\.、．](?!\d)\s*\S")
_CN_NUMBERED_CHAPTER = re.compile(r"^[一二三四五六七八九十百]+\s*[、．]\s*\S")
_KEYWORDS = re.compile(r"^(?:关键词|关键字|keywords?)\s*[：:]\s*(.+)$", re.I)
_NON_REVIEWABLE = (
    "摘要",
    "abstract",
    "目录",
    "参考文献",
    "references",
    "致谢",
    "附录",
    "攻读",
    "声明",
)
_GENERIC_COVER_TITLES = {"南京大学", "本科毕业论文", "毕业论文", "学位论文"}

# 常见但不符合中文编号规则的章节标题，启发式识别不到时视为“可疑”。
_KNOWN_CHAPTER_HINTS = (
    "introduction",
    "related work",
    "background",
    "method",
    "methodology",
    "proposed",
    "approach",
    "design",
    "implementation",
    "experiment",
    "evaluation",
    "result",
    "discussion",
    "analysis",
    "conclusion",
    "future work",
    "参考文献",
    "参考文献references",
)


@dataclass(frozen=True)
class MarkdownSection:
    level: int
    title: str
    lines: list[str]

    @property
    def content(self) -> str:
        return "\n".join(self.lines).strip()


class MarkdownPaperParser:
    """面向中文学位论文常见标题结构的无模型解析器。"""

    def __init__(
        self,
        model_client: Any | None = None,
        *,
        llm_split_enabled: bool | None = None,
    ) -> None:
        """初始化解析器。

        ``model_client`` 为可选的真实模型客户端（``backend.env.ModelClient``），
        用于二级切分兜底；为 None 时仅执行无模型启发式切分。

        ``llm_split_enabled``：是否允许在“启发式切分可疑”时调用大模型。
        None 时由环境变量 ``DEBATE_LLM_CHAPTER_SPLIT`` 决定（默认 0=关闭），
        True/False 显式覆盖。
        """
        self.model_client = model_client
        if llm_split_enabled is None:
            llm_split_enabled_env = os.getenv("DEBATE_LLM_CHAPTER_SPLIT", "0")
            llm_split_enabled = llm_split_enabled_env.strip().lower() not in {
                "0", "false", "no", "off",
            }
        self.llm_split_enabled = llm_split_enabled

    def parse(
        self,
        markdown: str,
        *,
        paper_type: PaperType | None = None,
        paper_id: str | None = None,
        title: str | None = None,
        source_filename: str | None = None,
        mineru_batch_id: str | None = None,
    ) -> DebateReviewInput:
        text = markdown.strip()
        if not text:
            raise ValueError("MinerU Markdown 不能为空")

        sections = self._sections(text)
        resolved_title = (
            title
            or self._detect_explicit_title(text)
            or self._detect_title(sections, source_filename)
        )
        chapters = self._chapters(sections, text)
        if (
            self.llm_split_enabled
            and self.model_client is not None
            and self._is_suspicious(sections, chapters)
        ):
            try:
                llm_chapters = self._llm_chapters(sections, text)
                if llm_chapters:
                    logger.info(
                        "启发式章节切分可疑，改由大模型辅助切分为 %d 章",
                        len(llm_chapters),
                    )
                    chapters = llm_chapters
            except Exception as exc:  # 兜底失败不阻断主流程
                logger.warning("大模型辅助切分失败，回退启发式结果: %s", exc)
        abstract = self._clean_abstract(
            self._extract_named_section(sections, ("摘要", "abstract"))
        )
        keywords = self._extract_keywords(text)
        references_text = self._extract_named_section(sections, ("参考文献", "references"))
        references = [
            line.strip(" -*\t")
            for line in references_text.splitlines()
            if line.strip(" -*\t")
        ]
        resolved_id = paper_id or "paper-" + hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()[:16]
        chapter_stage_source = (
            "heuristic_then_llm_fallback"
            if (self.llm_split_enabled and self.model_client is not None)
            else "markdown_heuristic"
        )
        metadata = {
            "ingestion": "mineru_markdown",
            "paper_type_source": "provided" if paper_type else "auto_pending",
            "chapter_stage_source": chapter_stage_source,
        }
        if source_filename:
            metadata["source_filename"] = source_filename
        if mineru_batch_id:
            metadata["mineru_batch_id"] = mineru_batch_id

        return DebateReviewInput(
            paper_id=resolved_id,
            title=resolved_title,
            abstract=abstract[:5000],
            keywords=keywords,
            full_text=text,
            paper_type=paper_type,
            chapters=chapters,
            references=references,
            metadata=metadata,
        )

    @staticmethod
    def _sections(markdown: str) -> list[MarkdownSection]:
        sections: list[MarkdownSection] = []
        current_title = "正文"
        current_level = 1
        current_lines: list[str] = []
        for line in markdown.splitlines():
            match = _HEADING.match(line)
            if match:
                if current_lines or sections:
                    sections.append(
                        MarkdownSection(current_level, current_title, current_lines)
                    )
                current_level = len(match.group(1))
                current_title = match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)
        sections.append(MarkdownSection(current_level, current_title, current_lines))
        return [section for section in sections if section.title or section.content]

    @staticmethod
    def _detect_title(
        sections: list[MarkdownSection], source_filename: str | None
    ) -> str:
        for section in sections:
            lowered = section.title.lower()
            if (
                section.title != "正文"
                and section.title.replace(" ", "") not in _GENERIC_COVER_TITLES
                and not _CHAPTER.match(section.title)
                and not any(
                marker in lowered for marker in ("摘要", "abstract", "目录")
                )
            ):
                return section.title
        if source_filename:
            return re.sub(r"(?i)\.pdf$", "", source_filename).strip() or "未命名论文"
        return "未命名论文"

    @staticmethod
    def _detect_explicit_title(markdown: str) -> str | None:
        for line in markdown.splitlines()[:80]:
            cleaned = line.strip().lstrip("#").strip()
            match = re.match(r"^题\s*目\s*[：:]\s*(.+)$", cleaned)
            if match and match.group(1).strip():
                return match.group(1).strip()[:120]
        return None

    @staticmethod
    def _is_chapter_heading(title: str) -> bool:
        if _CHAPTER.match(title):
            return True
        lowered = title.lower()
        if lowered in {"摘要", "abstract", "参考文献", "references", "致谢"}:
            return True
        if _NUMBERED_CHAPTER.match(title):
            return True
        if _CN_NUMBERED_CHAPTER.match(title):
            return True
        return False

    @staticmethod
    def _is_suspicious(
        sections: list[MarkdownSection], chapters: list[ChapterInput]
    ) -> bool:
        """判断启发式结果是否“可疑”，需要大模型辅助。

        - 整篇退化成一章“正文”：明显是编号规则没匹配上非规范标题；
        - 或任一章节正文远大于常见单章尺度（如 >60k 字符），说明多章被误并；
        - 或正文章节过少（<2）且存在已知但被漏识别的英文章标题关键词。
        """
        if len(chapters) == 1 and chapters[0].chapter_name == "正文":
            return True
        if any(len(chapter.content) > 60_000 for chapter in chapters):
            return True
        reviewable = [c for c in chapters if c.reviewable]
        if len(reviewable) < 2:
            seen = " ".join(s.title.lower() for s in sections)
            if any(hint in seen for hint in _KNOWN_CHAPTER_HINTS):
                return True
        return False

    def _llm_chapters(
        self, sections: list[MarkdownSection], full_text: str
    ) -> list[ChapterInput]:
        """用大模型辅助切分：模型只输出章标题清单，正文仍从原文截取。

        模型产物经严格 JSON 校验，章标题回映射到原始 Markdown 的标题位置，
        章节正文永远来自原文（保证 chapter_rubric 可锚定引文、不引入模型改写）。
        """
        from backend.env import ChatMessage, ModelCallOptions

        sample_lines = full_text.splitlines()[:300]
        llm_schema = {
            "type": "object",
            "properties": {
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chapter_title": {
                                "type": "string",
                                "description": "该章节在原文中的标题片段（尽量逐字一致）",
                            },
                        },
                        "required": ["chapter_title"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["chapters"],
            "additionalProperties": False,
        }
        user_prompt = (
            "请根据下面论文的 Markdown 结构，列出正文中的‘章级’标题清单。"
            "判断规则：章级标题是没有被更低层级拆分的顶层结构标题（如 第1章/1. 引言 / "
            "Introduction / 一、绪论 / 1 绪论 等）；不要把 1.1 这类小节当成章级。"
            "只输出章级标题，每个给出与原文尽量逐字一致的 chapter_title。"
            "若原文用了英文标题（Introduction、Related Work 等）也照常列出。"
            "只输出 schema 中的字段。"
        )
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是论文章节结构识别助手。只输出合法 JSON，"
                    "chapter_title 必须来自用户给出的原文，不许编造。"
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"{user_prompt}\n\n"
                    "严格按以下 JSON Schema 输出，只输出 schema 中声明过的字段：\n"
                    f"{json.dumps(llm_schema, ensure_ascii=False)}\n\n"
                    "输入数据：\n"
                    f"{json.dumps({'paper_preview': '\\n'.join(sample_lines)}, ensure_ascii=False)}"
                ),
            ),
        ]
        response = self.model_client.complete(
            messages,
            options=ModelCallOptions(
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
                stream=True,
            ),
        )
        # 简单容错提取：去掉可能的 ```json 围栏后取首个{...}
        content = response.content.strip()
        if content.startswith("```"):
            first_nl = content.find("\n")
            if first_nl != -1:
                content = content[first_nl + 1 :]
            if content.rstrip().endswith("```"):
                content = content.rstrip()[:-3]
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            content = content[start : end + 1]
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"大模型章节切分返回内容不是合法 JSON: {response.content[:200]}") from exc
        if "chapters" not in data or not isinstance(data["chapters"], list):
            raise ValueError("大模型章节切分返回缺少 chapters 列表")

        raw_titles = [item.get("chapter_title", "").strip() for item in data.get("chapters", [])]
        raw_titles = [t for t in raw_titles if t]
        if len(raw_titles) < 2:
            raise ValueError("大模型未识别出足够多章级标题")

        lines = full_text.splitlines()
        boundaries = self._map_boundaries(lines, raw_titles)
        if len(boundaries) < 2:
            raise ValueError("无法把模型标题回映射到原文边界")

        chapters: list[ChapterInput] = []
        for idx, start_line in enumerate(boundaries):
            end_line = (
                boundaries[idx + 1]
                if idx + 1 < len(boundaries)
                else len(lines)
            )
            seg = "\n".join(lines[start_line:end_line]).strip()
            if not seg:
                continue
            lead_title = self._heading_text(lines[start_line]) or f"章节{idx + 1}"
            chapters.append(
                ChapterInput(
                    chapter_id=f"C{len(chapters) + 1}",
                    chapter_name=lead_title,
                    stage=self._stage(lead_title),
                    content=seg,
                    section_titles=[],
                    reviewable=not any(
                        marker in lead_title.lower() for marker in _NON_REVIEWABLE
                    ),
                    metadata={"split_source": "llm_fallback",
                              "heading_level": "llm"},
                )
            )
        if not chapters:
            raise ValueError("大模型切分未产生任何章节")
        if not any(chapter.reviewable for chapter in chapters):
            chapters[0].reviewable = True
        return chapters

    @staticmethod
    def _heading_text(line: str) -> str:
        """提取一行中的标题文字（去掉 markdown 标记）。"""
        text = line.strip()
        text = re.sub(r"^#{1,6}\s*", "", text).strip()
        text = re.sub(r"^\*\*\s*", "", text).strip()
        text = re.sub(r"\s*\*\*$", "", text).strip()
        return text.strip(" \t#*")

    @staticmethod
    def _map_boundaries(lines: list[str], raw_titles: list[str]) -> list[int]:
        """把模型返回的章标题按顺序映射回原文行号。

        先找出所有“疑似标题行”（markdown #、加粗、或简短独立行），再把
        每个模型标题按顺序匹配到首个未被使用的标题行，返回有序的行号列表
        作为章节边界。采用贪心顺序匹配，防止模型返回顺序与原文不一致时错位。
        """
        candidates: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            is_markdown_head = bool(re.match(r"^#{1,6}\s+\S", stripped))
            is_bold = bool(re.match(r"^\*\*.+\*\*\s*$", stripped))
            if is_markdown_head or is_bold:
                candidates.append((i, stripped))
            else:
                # 简短独立行（无句末标点）也可能是非规范标题
                text = stripped.strip("*# ")
                if 1 <= len(text) <= 40 and not text.endswith(("。", "；", "，", ".")):
                    candidates.append((i, stripped))

        def norm(t: str) -> str:
            t = re.sub(r"^#{1,6}\s*", "", t).strip()
            t = re.sub(r"^\*\*", "", t).strip()
            t = re.sub(r"\*\*$", "", t).strip()
            t = re.sub(r"^\d+\s*[\.、．]\s*", "", t).strip()
            return re.sub(r"\s+", "", t).lower()

        used: list[int] = []
        cursor_pos = 0  # candidates 列表内的位置游标，保证顺序匹配
        min_line = 0  # 行号下界，保证不回退
        for want_raw in raw_titles:
            want = norm(want_raw)
            if not want:
                continue
            found: int | None = None
            found_pos: int | None = None
            for j in range(cursor_pos, len(candidates)):
                idx, line = candidates[j]
                if idx < min_line or idx in used:
                    continue
                norm_cand = norm(line)
                if not norm_cand:
                    continue
                if want in norm_cand or norm_cand in want:
                    found = idx
                    found_pos = j
                    break
                first_word = want.split()[0] if want.split() else ""
                if len(first_word) >= 2 and first_word in norm_cand:
                    found = idx
                    found_pos = j
                    break
            if found is not None and found_pos is not None:
                used.append(found)
                cursor_pos = found_pos + 1
                min_line = found + 1

        return sorted(set(used))

    def _chapters(
        self, sections: list[MarkdownSection], full_text: str
    ) -> list[ChapterInput]:
        chapter_starts = [
            index
            for index, section in enumerate(sections)
            if self._is_chapter_heading(section.title)
        ]
        if not chapter_starts:
            return [
                ChapterInput(
                    chapter_id="C1",
                    chapter_name="正文",
                    stage="正文",
                    content=full_text,
                )
            ]

        chapters: list[ChapterInput] = []
        for number, start in enumerate(chapter_starts, 1):
            end = chapter_starts[number] if number < len(chapter_starts) else len(sections)
            group = sections[start:end]
            lead = group[0]
            content = "\n\n".join(
                f"{'#' * item.level} {item.title}\n{item.content}".strip()
                for item in group
            )
            if not content.strip():
                continue
            chapters.append(
                ChapterInput(
                    chapter_id=f"C{len(chapters) + 1}",
                    chapter_name=lead.title,
                    stage=self._stage(lead.title),
                    content=content,
                    section_titles=[item.title for item in group[1:]],
                    reviewable=not any(
                        marker in lead.title.lower() for marker in _NON_REVIEWABLE
                    ),
                    metadata={"heading_level": str(lead.level)},
                )
            )
        if not any(chapter.reviewable for chapter in chapters):
            chapters[0].reviewable = True
        return chapters

    @staticmethod
    def _stage(title: str) -> str:
        lowered = title.lower()
        mappings = (
            (("摘要", "abstract"), "摘要"),
            (("绪论", "引言", "introduction"), "引言/绪论"),
            (("相关工作", "文献综述", "研究现状"), "相关工作"),
            (("方法", "模型", "算法", "设计"), "方法构建"),
            (("实验", "结果", "分析", "验证"), "实验验证"),
            (("结论", "总结", "展望"), "结论展望"),
            (("参考文献", "references"), "参考文献"),
            (("致谢",), "致谢"),
        )
        for keywords, stage in mappings:
            if any(keyword in lowered for keyword in keywords):
                return stage
        return "正文"

    @staticmethod
    def _extract_named_section(
        sections: list[MarkdownSection], names: tuple[str, ...]
    ) -> str:
        for section in sections:
            lowered = section.title.lower().strip()
            if any(name in lowered for name in names):
                return section.content
        return ""

    @staticmethod
    def _extract_keywords(markdown: str) -> list[str]:
        for line in markdown.splitlines():
            cleaned = line.strip().strip("*_")
            match = _KEYWORDS.match(cleaned)
            if match:
                return [
                    item.strip()
                    for item in re.split(r"[，,；;、]", match.group(1))
                    if item.strip()
                ]
        return []

    @staticmethod
    def _clean_abstract(value: str) -> str:
        lines = []
        for line in value.splitlines():
            if _KEYWORDS.match(line.strip().strip("*_")):
                break
            lines.append(line)
        return "\n".join(lines).strip()
