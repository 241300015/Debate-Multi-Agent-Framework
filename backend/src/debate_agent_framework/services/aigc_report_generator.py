"""AIGC 检测报告 PDF 生成器（适配 qhz 项目的 AigcDetectionResult 数据结构）。

样式参考 qinhaozhe 项目的 AIGC 结构化报告：包含封面（环图 + 信息表 + 统计数据）、
章节详细分析（进度条表格）、风险评估。

技术选型：
- 图表（环图 / 进度条）用 matplotlib 渲染成图片，中文字体用思源黑体（Noto Sans SC）。
- 页面排版用 fpdf2，纯 Python、无 GTK/系统字体依赖，部署无痛。
"""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

from ..aigc.schemas import AigcDetectionResult

logger = logging.getLogger("debate.aigc_report")

# 中文字体路径：项目根 backend/assets/fonts/NotoSansSC-Regular.ttf。
# 本文件位于 backend/src/debate_agent_framework/services/，向上 4 级到 backend/。
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_FONT_CANDIDATES = (
    _BACKEND_DIR / "assets" / "fonts" / "NotoSansSC-Regular.ttf",
    Path(__file__).resolve().parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf",
    Path("/usr/share/fonts") / "NotoSansSC-Regular.ttf",
)


def _resolve_font() -> Path:
    for cand in _FONT_CANDIDATES:
        if cand.exists():
            return cand
    return _FONT_CANDIDATES[0]

# 风险等级颜色（与前端一致）
COLOR_LOW = "rgb(76,175,80)"
COLOR_MEDIUM = "rgb(255,152,0)"
COLOR_HIGH = "rgb(220,38,127)"
COLOR_PRIMARY = (0, 51, 102)  # 深蓝表头
COLOR_AIGC = "#dc267f"  # 环图 AIGC 扇区
COLOR_HUMAN = "#66b2ff"  # 环图人工扇区

# 报告版式常量
A4_W_MM = 210
A4_H_MM = 297
MARGIN_L = 18
MARGIN_R = 18
MARGIN_T = 18
MARGIN_B = 20

# 报告使用北京时间（Asia/Shanghai, UTC+8），避免服务器系统时区为 UTC 时显示偏差。
_BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _now_local() -> datetime:
    return datetime.now(_BEIJING_TZ)


class AigcReportGenerator:
    """根据 AigcDetectionResult 生成 AIGC 检测报告 PDF。"""

    def __init__(self, font_path: str | Path | None = None) -> None:
        self.font_path = Path(font_path) if font_path else _resolve_font()
        if not self.font_path.exists():
            raise RuntimeError(f"AIGC 报告中文字体缺失: {self.font_path}")

    # ---------- 工具 ----------
    @staticmethod
    def _risk_level(rate: float) -> str:
        if rate < 0.4:
            return "低风险"
        if rate < 0.7:
            return "中风险"
        return "高风险"

    @staticmethod
    def _risk_description(rate: float) -> str:
        if rate < 0.4:
            return "论文整体 AIGC 含量较低，以人工创作为主，但建议对个别片段抽查复核。"
        if rate < 0.7:
            return "论文中存在部分疑似 AIGC 生成内容，建议对高风险章节进行人工复核和确认。"
        return "论文疑似 AIGC 含量较高，建议进行全面人工复核和修改，必要时重新撰写。"
    @staticmethod
    def _risk_color(rate: float) -> tuple[int, int, int]:
        if rate < 0.4:
            return (76, 175, 80)
        if rate < 0.7:
            return (255, 152, 0)
        return (220, 38, 127)

    def _register_font(self, pdf) -> None:  # noqa: ANN001
        family = os.path.splitext(self.font_path.name)[0]
        pdf.add_font(family, "", str(self.font_path))
        pdf.set_font(family, size=10)
        return family

    # ---------- 图表生成 ----------
    def _donut_image(self, aigc_rate: float) -> io.BytesIO:
        """生成环图 PNG，返回二进制流。"""
        import base64
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import font_manager, pyplot as plt

        font_manager.fontManager.addfont(str(self.font_path))
        prop = font_manager.FontProperties(fname=str(self.font_path))

        fig, ax = plt.subplots(figsize=(3.0, 3.0), dpi=140)
        percent = max(0.0, min(1.0, aigc_rate)) * 100
        ax.pie(
            [percent, 100 - percent],
            colors=[COLOR_AIGC, COLOR_HUMAN],
            startangle=90,
            counterclock=False,
            wedgeprops=dict(width=0.35, edgecolor="white"),
        )
        ax.text(
            0, 0.12, f"{percent:.1f}%", ha="center", va="center",
            fontsize=16, fontweight="bold", color="#333", fontproperties=prop,
        )
        ax.text(
            0, -0.22, "疑似AI占比", ha="center", va="center",
            fontsize=8, color="#666", fontproperties=prop,
        )
        ax.set(aspect="equal")
        plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _progress_image(self, rate: float) -> io.BytesIO:
        """生成水平进度条 PNG，返回二进制流。"""
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import font_manager, pyplot as plt
        from matplotlib.patches import FancyBboxPatch

        font_manager.fontManager.addfont(str(self.font_path))
        r, g, b = self._risk_color(rate)
        percent = max(0.0, min(1.0, rate)) * 100

        fig, ax = plt.subplots(figsize=(3.2, 0.32), dpi=140)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 10)
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0, 2), 100, 6, boxstyle="round,pad=0,rounding_size=3",
                facecolor="#e5e5e5", edgecolor="none",
            )
        )
        if percent > 0:
            ax.add_patch(
                FancyBboxPatch(
                    (0, 2), percent, 6, boxstyle="round,pad=0,rounding_size=3",
                    facecolor=f"#{r:02x}{g:02x}{b:02x}", edgecolor="none",
                )
            )
        ax.text(
            percent + 2, 5, f"{percent:.1f}%", va="center", ha="left",
            fontsize=8, color="#555", fontproperties=font_manager.FontProperties(
                fname=str(self.font_path)
            ),
        )
        plt.subplots_adjust(left=0.01, right=1.0, top=1.0, bottom=0.0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True)
        plt.close(fig)
        buf.seek(0)
        return buf

    # ---------- PDF 排版 ----------
    def generate(self, source_filename: str, result: AigcDetectionResult) -> io.BytesIO:
        """生成报告 PDF，返回内存中的字节流。"""
        from fpdf import FPDF

        pdf = FPDF("P", "mm", "A4")
        pdf.set_auto_page_break(auto=True, margin=MARGIN_B)
        pdf.set_margins(MARGIN_L, MARGIN_T)

        family = self._register_font(pdf)
        pdf.add_page()
        self._header_title(pdf, family)
        self._cover_page(pdf, family, source_filename, result)

        pdf.add_page()
        self._chapter_page(pdf, family, result)
        self._risk_page(pdf, family, result)

        if any(seg.risk_level in ("medium", "high") for seg in result.segments):
            pdf.add_page()
            self._risk_excerpts(pdf, family, result)

        buf = io.BytesIO()
        pdf.output(buf)
        buf.seek(0)
        return buf

    def _header_title(self, pdf, family: str) -> None:  # noqa: ANN001
        pdf.set_font(family, size=20)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 12, "AIGC 检测结构化报告", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, size=11)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, "睿文智评 AI 预审评估系统", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    def _cover_page(self, pdf, family: str, source_filename: str, result: AigcDetectionResult) -> None:  # noqa: ANN001
        pdf.set_font(family, size=14)
        pdf.cell(0, 10, "论文信息", new_x="LMARGIN", new_y="NEXT")
        info = [
            ("论文标题", source_filename),
            ("生成时间", _now_local().strftime("%Y年%m月%d日 %H:%M")),
            ("检测模型", result.model_id),
            ("判定阈值", f"{result.suspicious_threshold * 100:.1f}%"),
        ]
        pdf.set_font(family, size=10)
        for label, value in info:
            pdf.cell(35, 8, label, align="L")
            pdf.multi_cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")

        # 环图（居中）
        donut_buf = self._donut_image(result.suspicious_ratio)
        img_w = 70
        left = (A4_W_MM - MARGIN_L - MARGIN_R - img_w) / 2 + MARGIN_L
        pdf.image(donut_buf, x=left, w=img_w)
        pdf.ln(4)

        # 统计数据
        total_tokens = result.token_count
        suspicious_tokens = int(total_tokens * result.suspicious_ratio)
        human_tokens = total_tokens - suspicious_tokens
        pdf.set_font(family, size=13)
        pdf.cell(0, 9, "统计概览", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font(family, size=9)
        pdf.set_fill_color(*COLOR_PRIMARY)
        pdf.set_text_color(255, 255, 255)
        headers = ["总 Token", "疑似 Token", "人工 Token", "疑似AI占比"]
        col_w = (A4_W_MM - MARGIN_L - MARGIN_R) / 4
        for h in headers:
            pdf.cell(col_w, 7, h, border=1, align="C", fill=True)
        pdf.ln(7)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        rows = [
            f"{total_tokens:,}",
            f"{suspicious_tokens:,}",
            f"{human_tokens:,}",
            f"{result.suspicious_ratio * 100:.1f}%",
        ]
        for rv in rows:
            pdf.cell(col_w, 7, rv, border=1, align="C", fill=True)
        pdf.ln(7)
        pdf.ln(3)

        pdf.set_font(family, size=10)
        pdf.multi_cell(
            0, 6,
            "注：Token 为模型分词后的数量，与字符数可能略有差异。报告仅作辅助筛查，"
            "须人工复核后使用，不能直接作为最终鉴定结论。",
            new_x="LMARGIN", new_y="NEXT",
        )

    def _chapter_page(self, pdf, family: str, result: AigcDetectionResult) -> None:  # noqa: ANN001
        pdf.set_font(family, size=14)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 10, "章节详细分析", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        headings = ["章节", "Token", "疑似占比", "风险等级"]
        pdf.set_font(family, size=9)
        pdf.set_fill_color(*COLOR_PRIMARY)
        pdf.set_text_color(255, 255, 255)
        w = (A4_W_MM - MARGIN_L - MARGIN_R)
        widths = [w * 0.42, w * 0.14, w * 0.28, w * 0.16]
        for i, h in enumerate(headings):
            pdf.cell(widths[i], 7, h, border=1, align="C", fill=True)
        pdf.ln(7)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)

        chapters = result.chapters or []
        for ch in chapters:
            rate = ch.suspicious_ratio
            name = (ch.chapter_name or "")[:28]
            with pdf.local_context(text_color=(40, 40, 40)):  # type: ignore[attr-defined]
                pdf.cell(widths[0], 9, name, border=1, align="L")
            pdf.cell(widths[1], 9, f"{ch.token_count:,}", border=1, align="C")
            # 进度条占位：此处放百分号文字，实际进度条图片在另一页更合适，为简洁用色块百分比。
            r, g, b = self._risk_color(rate)
            pdf.set_text_color(r, g, b)
            pdf.cell(widths[2], 9, f"{rate * 100:.1f}%", border=1, align="C")
            pdf.set_text_color(0, 0, 0)
            pdf.cell(widths[3], 9, self._risk_level(rate), border=1, align="C")
            pdf.ln(9)

        pdf.ln(2)
        pdf.set_font(family, size=9)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(
            0, 6,
            "图例：低风险 <40%，中风险 40%~70%，高风险 ≥70%。占比基于该章节疑似 Token 占比。",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_text_color(0, 0, 0)

    def _risk_page(self, pdf, family: str, result: AigcDetectionResult) -> None:  # noqa: ANN001
        pdf.set_font(family, size=14)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 10, "风险评估", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        rate = result.suspicious_ratio
        r, g, b = self._risk_color(rate)
        pdf.set_font(family, size=12)
        pdf.set_text_color(r, g, b)
        pdf.cell(0, 9, f"风险等级：{self._risk_level(rate)}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(family, size=10)
        pdf.multi_cell(0, 7, self._risk_description(rate), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)
        pdf.set_font(family, size=9)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(
            0, 6,
            f"检测模型：{result.model_id}\n"
            f"预处理版本：{result.preprocessing_version}\n"
            f"生成时间：{_now_local().strftime('%Y-%m-%d %H:%M')}\n"
            f"声明：{result.disclaimer or '检测结果仅用于辅助筛查，不能单独作为认定 AI 生成或学术不端的依据。'}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_text_color(0, 0, 0)


    def _risk_excerpts(self, pdf, family: str, result: AigcDetectionResult) -> None:  # noqa: ANN001
        """附上中/高风险检测窗口的原文片段（取自 content_preview）。"""
        pdf.set_font(family, size=14)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 10, "中高风险原文片段", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        targets = [
            seg for seg in result.segments if seg.risk_level in ("medium", "high")
        ]
        if not targets:
            pdf.set_font(family, size=10)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(0, 7, "未发现中高风险片段。", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            return

        pdf.set_font(family, size=9)
        pdf.set_fill_color(*COLOR_PRIMARY)
        pdf.set_text_color(255, 255, 255)
        pdf.multi_cell(
            0, 6,
            "以下为中/高风险检测窗口的文本片段，供人工复核定位。片段不完整，正式引用请以原始论文为准。",
            border=1, fill=True, new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        risk_labels = {"low": "低风险", "medium": "中风险", "high": "高风险"}
        risk_colors = {
            "medium": (255, 152, 0),
            "high": (220, 38, 127),
        }

        for seg in targets:
            color = risk_colors.get(seg.risk_level, (90, 90, 90))
            label = risk_labels.get(seg.risk_level, seg.risk_level)
            # 标题行：风险等级 + 章节 + 概率
            pdf.set_font(family, size=9)
            pdf.set_text_color(*color)
            pdf.cell(
                0, 6,
                f"[{label}] {seg.chapter_name or '未知章节'}  ·  "
                f"疑似概率 {seg.ai_probability * 100:.1f}%",
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.set_text_color(0, 0, 0)
            # 原文片段
            preview = (seg.content_preview or "（无预览片段）").replace("\n", " ")
            pdf.set_font(family, size=9)
            pdf.multi_cell(
                0, 5, preview, new_x="LMARGIN", new_y="NEXT",
            )
            pdf.ln(2)


def generate_aigc_pdf(source_filename: str, result: AigcDetectionResult) -> io.BytesIO:
    """便捷函数：生成 AIGC 检测报告 PDF，返回字节流。"""
    return AigcReportGenerator().generate(source_filename, result)
