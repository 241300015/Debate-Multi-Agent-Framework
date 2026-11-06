"""生成《衡文云审：问题修复 · 格式解析 · 论文发表调研》PPT。

基于 docs/衡文云审-工作汇报-2026-09-26.pptx 的版式风格（紫金配色 #6F1E77、
白底标题栏、圆角浅紫卡片、页脚页码）手工重建，输出为独立新文件。
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

PURPLE = "6F1E77"
PURPLE_LIGHT = "F6F4FA"
LINE_COLOR = "E3DDEC"
TEXT_DARK = "2B2B2B"
TEXT_GRAY = "5A5A5A"
WHITE = "FFFFFF"
GREEN = "0D652D"
FONT = "微软雅黑"

SLIDE_W, SLIDE_H = 13.333, 7.5


def add_rect(slide, x, y, w, h, fill=None, shape=MSO_SHAPE.RECTANGLE):
    sp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        sp.fill.solid()
        sp.fill.fore_color.rgb = RGBColor.from_string(fill)
    else:
        sp.fill.background()
    sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def add_text(slide, x, y, w, h, lines, *, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.01)
    for i, spec in enumerate(lines):
        text, size, bold, color = spec
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = text
        f = r.font
        f.name = FONT
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = RGBColor.from_string(color)
    return tb


def cover(prs, subtitle, date_text):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=PURPLE)
    add_rect(slide, 0, 4.95, SLIDE_W, 0.06, shape=MSO_SHAPE.RECTANGLE)
    add_text(slide, 1.10, 1.60, 11.10, 1.00,
             [("衡文云审", 64, True, WHITE)])
    add_text(slide, 1.10, 2.60, 11.10, 0.60,
             [("基于多智能体辩论的毕业论文智能评审系统", 26, False, "EDDFF2")])
    add_text(slide, 1.10, 3.40, 11.10, 0.50,
             [(subtitle, 18, False, "D9C2E2")])
    add_text(slide, 1.10, 5.40, 11.10, 0.90,
             [(date_text, 14, False, "EDDFF2")])


def header(slide, title, subtitle, page):
    add_rect(slide, 0, 0, SLIDE_W, 1.02, fill=WHITE)
    add_rect(slide, 0.55, 0.33, 0.14, 0.46, fill=PURPLE)
    add_text(slide, 0.90, 0.22, 11.40, 0.60, [(title, 25, True, PURPLE)])
    add_text(slide, 0.92, 0.66, 11.40, 0.35, [(subtitle, 12, False, TEXT_GRAY)])
    add_rect(slide, 0.55, 1.02, 12.23, 0.02, fill=LINE_COLOR)
    add_rect(slide, 0.55, 7.00, 12.23, 0.01, fill=LINE_COLOR)
    add_text(slide, 0.60, 7.06, 12.10, 0.32,
             [(f"衡文云审 · 评审系统研发简报 | {page}", 10, False, TEXT_GRAY)])


def card(slide, x, y, w, h, lines, *, fill=PURPLE_LIGHT, align=PP_ALIGN.LEFT):
    add_rect(slide, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_text(slide, x + 0.18, y + 0.12, w - 0.36, h - 0.24, lines, align=align)


def content(prs, title, subtitle, page, body_fn):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, title, subtitle, page)
    body_fn(slide)
    return slide


def toc(prs, items):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, SLIDE_W, 1.02, fill=WHITE)
    add_rect(slide, 0.55, 0.33, 0.14, 0.46, fill=PURPLE)
    add_text(slide, 0.90, 0.22, 11.40, 0.60, [("目录", 25, True, PURPLE)])
    add_text(slide, 0.92, 0.66, 11.40, 0.35, [("CONTENTS", 12, False, TEXT_GRAY)])
    add_rect(slide, 0.55, 1.02, 12.23, 0.02, fill=LINE_COLOR)
    y = 1.50
    for item in items:
        card(slide, 0.90, y, 11.50, 0.78, [(item, 18, True, PURPLE)])
        y += 0.93
    add_rect(slide, 0.55, 7.00, 12.23, 0.01, fill=LINE_COLOR)
    add_text(slide, 0.60, 7.06, 12.10, 0.32,
             [("衡文云审 · 评审系统研发简报 | 2", 10, False, TEXT_GRAY)])


def closing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=PURPLE)
    add_rect(slide, 0, 4.95, SLIDE_W, 0.06)
    add_text(slide, 1.10, 2.30, 11.10, 1.00, [("谢谢", 64, True, WHITE)], align=PP_ALIGN.CENTER)
    add_text(slide, 1.10, 3.60, 11.10, 0.50,
             [("欢迎讨论：多智能体辩论评审 · 论文发表规划", 18, False, "D9C2E2")], align=PP_ALIGN.CENTER)


def main():
    prs = Presentation()
    prs.slide_width = Emu(12191695)
    prs.slide_height = Emu(6858000)

    cover(prs, "—— 问题修复 · 格式解析 · 论文发表调研 ——", "汇报人：____________        汇报日期：2026 年 10 月 11 日")

    toc(prs, [
        "01  上传失败 Bug：双模块导入冲突与修复",
        "02  章节切分流程与非规范格式论文的影响",
        "03  项目论文选题调研：三个方向与参考论文",
        "04  下一步建议",
    ])

    # ---- P3: Bug 现象 ----
    content(prs, "01 上传失败 Bug：现象与复现", "论文上传后评审任务直接失败", 3, lambda s: (
        card(s, 0.90, 1.35, 5.50, 3.90, [
            ("线上报错原文（Pydantic）", 15, True, PURPLE),
            ("1 validation error for DebateReviewInput", 13, False, TEXT_DARK),
            ("Input should be a valid dictionary or instance of DebateReviewInput", 13, False, TEXT_DARK),
            ("[type=model_type]", 13, True, PURPLE),
            ("input_value=DebateReviewInput(paper_id=…)", 13, False, TEXT_DARK),
            ("input_type=DebateReviewInput", 13, False, TEXT_DARK),
        ]),
        card(s, 6.70, 1.35, 5.70, 1.80, [
            ("触发时机", 15, True, PURPLE),
            ("上传 PDF → /papers/review 受理(202)", 13, False, TEXT_DARK),
            ("后台任务 service.execute → DebateWorkflow.arun", 13, False, TEXT_DARK),
            ("→ DebateReviewInput.model_validate() 抛错", 13, False, TEXT_DARK),
        ]),
        card(s, 6.70, 3.30, 5.70, 1.95, [
            ("关键线索", 15, True, PURPLE),
            ("传入的 input 本身就是 DebateReviewInput 实例", 13, False, TEXT_DARK),
            ("却仍然报“类型错误”→ 同类不同类", 13, True, PURPLE),
            ("→ 同一份代码存在两份类定义", 13, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 5.60, 11.50, 1.10, [
            ("定位结论：不是评审数据问题，而是模块被双重加载导致的类身份分裂。", 14, True, GREEN),
        ])))

    # ---- P4: 根因 ----
    content(prs, "01 根因：同代码被加载为两个互不相同的模块", "启动路径与包内绝对导入混用", 4, lambda s: (
        add_text(s, 0.90, 1.35, 11.50, 1.05, [
            ("双重身份：", 15, True, PURPLE),
            ("uvicorn backend.src.debate_agent_framework.main:app（从项目根目录启动）", 14, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 2.18, 11.50, 1.05, [
            ("包内部却混用绝对导入 debate_agent_framework.*：", 15, True, PURPLE),
            ("services/workflow_service.py、routers/runs.py、workflows/debate.py、cli.py", 14, False, TEXT_DARK),
        ]),
        card(s, 0.90, 3.30, 5.50, 2.35, [
            ("后果一", 15, True, PURPLE),
            ("同一源码被加载为两个模块身份", 13, False, TEXT_DARK),
            ("· backend.src.debate_agent_framework.*", 13, False, TEXT_DARK),
            ("· debate_agent_framework.*", 13, False, TEXT_DARK),
            ("⇒ DebateReviewInput 出现两份类定义", 13, True, PURPLE),
        ]),
        card(s, 6.70, 3.30, 5.70, 2.35, [
            ("后果二（线上报错链路）", 15, True, PURPLE),
            ("papers.py 用相对导入建实例（类A）", 13, False, TEXT_DARK),
            ("workflow 侧 model_validate 用类B", 13, False, TEXT_DARK),
            ("类A 实例 ≠ 类B 校验类 → model_type 报错", 13, True, PURPLE),
        ]),
        add_text(s, 0.90, 5.90, 11.50, 0.80, [
            ("已复现：ClsA is ClsB → False；ClsB.model_validate(ClsA 实例) → 与线上完全一致的报错。", 14, False, TEXT_DARK),
        ])))

    # ---- P5: 修复 ----
    content(prs, "01 修复方案与验证", "统一包内相对导入，消除双重身份", 5, lambda s: (
        add_text(s, 0.90, 1.35, 11.50, 0.55, [("修改四处绝对导入为包内相对导入：", 15, True, PURPLE)]),
        card(s, 0.90, 1.95, 5.50, 1.45, [
            ("services/workflow_service.py", 13, True, TEXT_DARK),
            ("from debate_agent_framework.schemas import …", 12, False, TEXT_GRAY),
            ("→ from ..schemas import …", 12, True, GREEN),
        ]),
        card(s, 6.70, 1.95, 5.70, 1.45, [
            ("routers/runs.py", 13, True, TEXT_DARK),
            ("from debate_agent_framework.schemas/jobs import …", 12, False, TEXT_GRAY),
            ("→ from ..schemas / ..services.jobs import …", 12, True, GREEN),
        ]),
        card(s, 0.90, 3.55, 5.50, 1.45, [
            ("workflows/debate.py", 13, True, TEXT_DARK),
            ("from debate_agent_framework.core.errors import …", 12, False, TEXT_GRAY),
            ("→ from ..core.errors import …", 12, True, GREEN),
        ]),
        card(s, 6.70, 3.55, 5.70, 1.45, [
            ("cli.py", 13, True, TEXT_DARK),
            ("from debate_agent_framework.core.errors import …", 12, False, TEXT_GRAY),
            ("→ from ..core.errors import …", 12, True, GREEN),
        ]),
        add_text(s, 0.90, 5.25, 11.50, 1.55, [
            ("验证结果：", 14, True, PURPLE),
            ("· 模拟线上启动方式（backend.src.* 入口）跑通 demo 全链路：arun → 3 份独立初审，无校验错误", 13, False, TEXT_DARK),
            ("· 运行中的服务 --reload 已自动生效（/docs 200），重新上传论文恢复正常", 13, False, TEXT_DARK),
            ("· 附带发现：frontend/src/portal-fixes.css 曾有未解决的合并冲突标记，已一并清理。", 13, False, TEXT_DARK),
        ])))

    # ---- P6: 章节切分流程 ----
    content(prs, "02 章节切分流程：无模型启发式解析", "ingestion/markdown.py · 五步完成切分", 6, lambda s: (
        card(s, 0.90, 1.35, 3.75, 4.55, [
            ("① PDF → Markdown", 14, True, PURPLE),
            ("MinerU 解析后进入 MarkdownPaperParser.parse()", 12, False, TEXT_DARK),
            ("② _sections() 按标题分段", 14, True, PURPLE),
            ("#~###### 逐行切段，开头无标题内容归入“正文”", 12, False, TEXT_DARK),
            ("③ _is_chapter_heading() 判定“章级”", 14, True, PURPLE),
            ("· 第X章 / 摘要、参考文献、致谢", 12, False, TEXT_DARK),
            ("· 数字编号 1. / 1、 / 1．(排除 1.1)", 12, False, TEXT_DARK),
            ("· 中文编号 一、 / 二、", 12, False, TEXT_DARK),
        ]),
        card(s, 4.80, 1.35, 3.75, 4.55, [
            ("④ _chapters() 组章", 14, True, PURPLE),
            ("起点之间截取合并为章节内容", 12, False, TEXT_DARK),
            ("每章生成 chapter_id / 章名 / stage /", 12, False, TEXT_DARK),
            ("section_titles / reviewable", 12, False, TEXT_DARK),
            ("无任何章级起点 → 整篇兜底单章“正文”", 12, True, PURPLE),
            ("⑤ _stage() 阶段标注 + 过滤", 14, True, PURPLE),
            ("标题关键词 → 引言/相关工作/方法/实验/结论等", 12, False, TEXT_DARK),
            ("无匹配回落“正文”", 12, False, TEXT_DARK),
        ]),
        card(s, 8.70, 1.35, 3.75, 4.55, [
            ("下游使用", 14, True, PURPLE),
            ("ContextPlanner 构造章节上下文", 12, False, TEXT_DARK),
            ("chapter_rubric 按 chapter.stage 匹配评审细则", 12, False, TEXT_DARK),
            ("无匹配 → 公共默认细则兜底", 12, False, TEXT_DARK),
            ("不可评审章（摘要/目录/参考文献/致谢/附录）", 12, False, TEXT_DARK),
            ("若全部不可评审 → 强制第一章可评审", 12, True, PURPLE),
        ]),
        add_text(s, 0.90, 6.10, 11.50, 0.70, [
            ("切分入口：routers/papers.py 上传 → MinerU → MarkdownPaperParser.parse() → 章节进入评审链路。", 13, False, TEXT_DARK),
        ])))

    # ---- P7: 格式影响 ----
    content(prs, "02 非规范格式论文对评审的影响", "结论先行：影响可控，主链路不受格式约束", 7, lambda s: (
        card(s, 0.90, 1.35, 5.50, 2.45, [
            ("① 章节粒度（最大风险）", 15, True, PURPLE),
            ("无编号标题（如裸英文 Introduction）不被识别为章起点", 13, False, TEXT_DARK),
            ("整篇退化为单个“正文”章节 → 评审粒度变粗", 13, True, GREEN),
        ]),
        card(s, 6.70, 1.35, 5.70, 2.45, [
            ("② 阶段匹配", 15, True, PURPLE),
            ("标题用词不匹配关键词映射 → stage=", 13, False, TEXT_DARK),
            ("“正文” → 走公共默认细则兜底，仍参与评审", 13, False, TEXT_DARK),
        ]),
        card(s, 0.90, 3.95, 5.50, 2.45, [
            ("③ 摘要 / 关键词 / 参考文献", 15, True, PURPLE),
            ("标签缺失（无“摘要/abstract”等字样）→ 字段为空", 13, False, TEXT_DARK),
            ("影响上下文构造与证据检索查询的输入质量", 13, False, TEXT_DARK),
        ]),
        card(s, 6.70, 3.95, 5.70, 2.45, [
            ("④ 论文类型无关", 15, True, PURPLE),
            ("类型（理论/方法/工程）不在格式判定范围内", 13, False, TEXT_DARK),
            ("未指定时走自动分类（auto_pending）", 13, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 6.55, 11.50, 0.40, [
            ("风险聚焦两点：完全无编号标题、摘要/关键词标签缺失。", 14, True, TEXT_DARK),
        ])))

    # ---- P8: 选题方向一 ----
    content(prs, "03 选题方向一：方法论文（推荐）", "争议驱动的多智能体结构化论文评审", 8, lambda s: (
        add_text(s, 0.90, 1.35, 11.50, 0.55, [("独特贡献点（现有文献少见）：", 15, True, PURPLE)]),
        card(s, 0.90, 1.95, 3.75, 2.20, [
            ("结构化评审而非整篇打分", 13, True, TEXT_DARK),
            ("分章解构 + 阶段标注 + 逐章评审细则", 12, False, TEXT_DARK),
        ]),
        card(s, 4.80, 1.95, 3.75, 2.20, [
            ("争议驱动 + 证据问询", 13, True, TEXT_DARK),
            ("三专家初审 → 议题争议 → 证据检索 → 主席裁决", 12, False, TEXT_DARK),
        ]),
        card(s, 8.70, 1.95, 3.75, 2.20, [
            ("历史专家 RAG + 评分校准层", 13, True, TEXT_DARK),
            ("仿射映射对齐真实专家分，天然可评测", 12, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 4.35, 11.50, 0.55, [("评测矩阵：", 15, True, PURPLE)]),
        card(s, 0.90, 4.95, 5.50, 1.60, [
            ("实验组", 13, True, TEXT_DARK),
            ("· vs 单LLM / 无辩论基线", 12, False, TEXT_DARK),
            ("· 与专家分 Pearson / Spearman 一致性", 12, False, TEXT_DARK),
        ]),
        card(s, 6.70, 4.95, 5.70, 1.60, [
            ("消融与可信", 13, True, TEXT_DARK),
            ("· 去掉 辩论/证据/分章/主席 四路消融", 12, False, TEXT_DARK),
            ("· 争议检出率 + 证据可验证性", 12, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 6.70, 11.50, 0.40, [
            ("目标会议：EMNLP / AAAI / CIKM / IJCAI。", 13, True, PURPLE),
        ])))

    # ---- P9: 方向二/三 ----
    content(prs, "03 选题方向二 / 三：系统落地与问题聚焦", "两条备选路径，增量各有侧重", 9, lambda s: (
        card(s, 0.90, 1.35, 5.50, 4.60, [
            ("方向二 系统落地论文", 16, True, PURPLE),
            ("全链路系统：解析→结构化评审→证据RAG→", 13, False, TEXT_DARK),
            ("AIGC检测→评分校准→Web平台", 13, False, TEXT_DARK),
            ("持久化 / 断点恢复 / 异步并发等工程能力完整", 13, False, TEXT_DARK),
            ("真实场景：南京大学本科毕业论文评审", 13, True, GREEN),
            ("输出：系统架构 + 案例 + 专家对比评估", 13, False, TEXT_DARK),
            ("目标：IJCAI Demo / 软件学报 / 计算机学报", 13, True, PURPLE),
        ]),
        card(s, 6.70, 1.35, 5.70, 4.60, [
            ("方向三 问题聚焦论文", 16, True, PURPLE),
            ("多智能体辩论的“问题漂移”与治理", 13, True, TEXT_DARK),
            ("议题上限 3 条 + 冷启动兜底议题 = 现成的漂移治理手段", 13, False, TEXT_DARK),
            ("可做：漂移量化分析 + 治理前后对比", 13, False, TEXT_DARK),
            ("对标：Stay Focused: Problem Drift in Multi-Agent Debate (EACL 2026)", 12, False, TEXT_DARK),
            ("篇幅小、增量明确，适合快速产出", 13, True, GREEN),
        ]),
        add_text(s, 0.90, 6.15, 11.50, 0.60, [
            ("建议主线：方向一为正文，方向二/三作为补充章节或并行工作。", 14, True, TEXT_DARK),
        ])))

    # ---- P10: 参考论文 ----
    content(prs, "03 参考论文清单", "多智能体辩论方法 + LLM 评审领域（均已核实可访问）", 10, lambda s: (
        card(s, 0.90, 1.35, 5.50, 4.90, [
            ("多智能体辩论（方法参考）", 15, True, PURPLE),
            ("MAD：Encouraging Divergent Thinking… — EMNLP 2024", 12, False, TEXT_DARK),
            ("  arxiv.org/abs/2305.19118", 11, False, TEXT_GRAY),
            ("Sparse Communication Topology", 12, False, TEXT_DARK),
            ("  arxiv.org/abs/2406.11776", 11, False, TEXT_GRAY),
            ("GroupDebate（分组辩论降成本）— AAMAS 2026", 12, False, TEXT_DARK),
            ("  arxiv.org/abs/2409.14051", 11, False, TEXT_GRAY),
            ("★ Problem Drift（辩论漂移，最相关）— EACL 2026", 12, True, GREEN),
            ("  arxiv.org/abs/2502.19559", 11, False, TEXT_GRAY),
        ]),
        card(s, 6.70, 1.35, 5.70, 4.90, [
            ("LLM 评审（领域对照）", 15, True, PURPLE),
            ("Beyond Imitation: Framework & Benchmark for LLM-Assisted Peer Review", 12, False, TEXT_DARK),
            ("  arxiv.org/abs/2610.11087（2026-10）", 11, False, TEXT_GRAY),
            ("SCOPE Fuzzing：LLM 评审者鲁棒性评测", 12, False, TEXT_DARK),
            ("  arxiv.org/abs/2609.37097", 11, False, TEXT_GRAY),
            ("经典基线：Can LLMs Write Good Referee Reports? — ICLR 2024", 12, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 6.45, 11.50, 0.60, [
            ("阅读建议：先读 Problem Drift 与 Beyond Imitation，两篇决定主叙事与评测设计。", 14, True, PURPLE),
        ])))

    # ---- P11: 下一步建议 ----
    content(prs, "04 下一步建议", "实验先行 · 解析增强 · 论文路线", 11, lambda s: (
        card(s, 0.90, 1.35, 5.50, 1.35, [
            ("1. 实验先行，定主叙事", 15, True, PURPLE),
            ("用 14 对专家配对分对比“单模型 vs 完整辩论链路”，验证辩论能提升与专家分的一致性", 12, False, TEXT_DARK),
        ]),
        card(s, 6.70, 1.35, 5.70, 1.35, [
            ("2. 解析增强，降低风险", 15, True, PURPLE),
            ("支持英文无编号标题识别（Introduction…），补摘要/关键词兜底规则", 12, False, TEXT_DARK),
        ]),
        card(s, 0.90, 2.85, 5.50, 1.35, [
            ("3. 论文路线", 15, True, PURPLE),
            ("评测 → 四路消融 → 撰写 → EMNLP/AAAI/CIKM；先以 Technical Report 沉淀基线数据", 12, False, TEXT_DARK),
        ]),
        card(s, 6.70, 2.85, 5.70, 1.35, [
            ("4. 工程收尾", 15, True, PURPLE),
            ("启动命令文档化（统一入口），包内相对导入规范成文，防止双重身份复发", 12, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 4.60, 11.50, 0.50, [("本轮交付小结：", 15, True, PURPLE)]),
        card(s, 0.90, 5.10, 11.50, 1.10, [
            ("· 根因级修复上传失败 Bug（双模块身份分裂），验证通过并已生效", 13, False, TEXT_DARK),
            ("· 梳理章节切分五步流程与格式影响边界", 13, False, TEXT_DARK),
            ("· 完成论文选题调研：三个方向 + 7 篇可参考论文（附 arXiv 链接）", 13, False, TEXT_DARK),
        ])))

    closing(prs)

    out = "/nvme/home/rincug/qhz/docs/衡文云审-问题修复与论文发表调研-2026-10-11.pptx"
    prs.core_properties.title = "衡文云审：问题修复 · 格式解析 · 论文发表调研"
    prs.core_properties.author = "衡文云审"
    prs.save(out)
    print("saved:", out)


if __name__ == "__main__":
    main()
