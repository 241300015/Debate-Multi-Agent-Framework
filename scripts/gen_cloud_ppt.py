"""生成《睿文智评：AIGC 检测优化 · 云服务器部署计划》工作汇报 PPT。

复用紫金配色版式（#6F1E77 主色、浅紫圆角卡片 #F6F4FA、白底标题栏、页脚页码）。
覆盖两天工作：AIGC 检测的改动 + 租用云服务器的计划。
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
    add_text(slide, 1.10, 1.70, 11.10, 1.00, [("睿文智评", 64, True, WHITE)])
    add_text(slide, 1.10, 2.70, 11.10, 0.60,
             [("基于多智能体辩论的毕业论文智能评审系统", 26, False, "EDDFF2")])
    add_text(slide, 1.10, 3.50, 11.10, 0.50,
             [(subtitle, 18, False, "D9C2E2")])
    add_text(slide, 1.10, 5.50, 11.10, 0.90,
             [(date_text, 14, False, "EDDFF2")])


def header(slide, title, subtitle, page):
    add_rect(slide, 0, 0, SLIDE_W, 1.02, fill=WHITE)
    add_rect(slide, 0.55, 0.33, 0.14, 0.46, fill=PURPLE)
    add_text(slide, 0.90, 0.22, 11.40, 0.60, [(title, 25, True, PURPLE)])
    add_text(slide, 0.92, 0.66, 11.40, 0.35, [(subtitle, 12, False, TEXT_GRAY)])
    add_rect(slide, 0.55, 1.02, 12.23, 0.02, fill=LINE_COLOR)
    add_rect(slide, 0.55, 7.00, 12.23, 0.01, fill=LINE_COLOR)
    add_text(slide, 0.60, 7.06, 12.10, 0.32,
             [(f"睿文智评 · 评审系统研发简报 | {page}", 10, False, TEXT_GRAY)])


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
             [("睿文智评 · 评审系统研发简报 | 2", 10, False, TEXT_GRAY)])


def closing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=PURPLE)
    add_rect(slide, 0, 4.95, SLIDE_W, 0.06)
    add_text(slide, 1.10, 2.30, 11.10, 1.00, [("谢谢", 64, True, WHITE)], align=PP_ALIGN.CENTER)
    add_text(slide, 1.10, 3.60, 11.10, 0.50,
             [("讨论：AIGC 检测优化 · 云服务器部署计划", 18, False, "D9C2E2")], align=PP_ALIGN.CENTER)


def main():
    prs = Presentation()
    prs.slide_width = Emu(12191695)
    prs.slide_height = Emu(6858000)

    cover(prs, "—— AIGC 检测优化 · 云服务器部署计划 ——",
          "汇报人：____________        汇报日期：2026 年 10 月 31 日")

    toc(prs, [
        "01  AIGC 检测：指标与报告导出优化",
        "02  AIGC 检测：中高风险原文 · 时区修复",
        "03  云服务器计划：资源需求评估",
        "04  云服务器计划：部署路线与成本",
    ])

    # ---- P3 AIGC 指标优化 ----
    content(prs, "01 AIGC 检测：新增“疑似AI占比”与报告导出", "对齐知网口径 · 支持 PDF 导出", 3, lambda s: (
        card(s, 0.90, 1.50, 5.50, 3.40, [
            ("① 新增“疑似AI占比”指标", 15, True, PURPLE),
            ("· 按可配置阈值计算 token 占比", 13, False, TEXT_DARK),
            ("· 对齐知网「疑似片段占比」口径", 13, False, TEXT_DARK),
            ("· 阈值可调（DEBATE_AIGC_SUSPICIOUS_THRESHOLD）", 12.5, False, TEXT_DARK),
            ("· 从 0.3 调到 0.1，占比升至 50%+", 13, True, GREEN),
        ]),
        card(s, 6.70, 1.50, 5.70, 3.40, [
            ("② 报告 PDF 导出", 15, True, PURPLE),
            ("· 复用 qinhaozhe 环图样式", 13, False, TEXT_DARK),
            ("· fpdf2 + matplotlib + 思源黑体", 13, False, TEXT_DARK),
            ("· 封面(环图+统计) / 章节表 / 风险评估", 13, False, TEXT_DARK),
            ("· 前端加“导出 PDF 报告”按钮", 13, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 5.15, 11.50, 0.60, [("技术要点：", 15, True, PURPLE)]),
        card(s, 0.90, 5.75, 11.50, 0.90, [
            ("纯 CPU 生成 PDF（无需 GPU）；中文字体用思源黑体，绕开系统无字体的痛点。", 14, False, TEXT_DARK),
        ])))

    # ---- P4 AIGC 报告内容 ----
    content(prs, "02 AIGC 报告：中高风险原文 + 时区修复", "定位复核 · 时间准确", 4, lambda s: (
        card(s, 0.90, 1.50, 5.50, 3.60, [
            ("① 报告中高风险原文片段", 16, True, PURPLE),
            ("· 报告追加「中高风险原文片段」页", 13, False, TEXT_DARK),
            ("· 逐条列出 [风险等级] 章节 · 疑似概率", 13, False, TEXT_DARK),
            ("· 附该窗口原文片段供人工复核", 13, False, TEXT_DARK),
            ("· 无中高风险则不追加空白页", 13, False, TEXT_DARK),
        ]),
        card(s, 6.70, 1.50, 5.70, 3.60, [
            ("② 报告时间时区修复", 16, True, PURPLE),
            ("· 原：datetime.now() 用系统 UTC 时区", 13, False, TEXT_DARK),
            ("· 16:02 生成显示成 8:02（差 8 小时）", 13, False, TEXT_DARK),
            ("· 修复：改用 Asia/Shanghai（北京时间 UTC+8）", 13, True, GREEN),
            ("· 用标准库 zoneinfo，不依赖服务器时区", 13, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 5.40, 11.50, 0.60, [("验证：", 15, True, PURPLE)]),
        card(s, 0.90, 6.00, 11.50, 0.75, [
            ("· 报告 3 页（封面/章节/风险）、中高风险原文页正常生成；测试 4 项全过。", 14, False, TEXT_DARK),
        ])))

    # ---- P5 资源需求 ----
    content(prs, "03 云服务器计划：资源需求评估", "关键在于 CPU 而非 GPU", 5, lambda s: (
        card(s, 0.90, 1.50, 5.50, 3.90, [
            ("各模块资源需求", 16, True, PURPLE),
            ("· 后端 + 评审工作流：CPU, 走云端API", 13, False, TEXT_DARK),
            ("· 向量库 Chroma + RAG：内存 2~4GB", 13, False, TEXT_DARK),
            ("· 论文解析：走 MinerU 云 API, 很轻", 13, False, TEXT_DARK),
            ("· 报告PDF：纯 CPU", 13, False, TEXT_DARK),
        ]),
        card(s, 6.70, 1.50, 5.70, 3.90, [
            ("AIGC 检测 GPU 需求（实测）", 16, True, PURPLE),
            ("· 模型 = BERT 二分类，仅 102M 参数", 13, False, TEXT_DARK),
            ("· FP32 权重 ~390MB，FP16 推理 ~395MB 显存", 13, True, GREEN),
            ("· 完全不需要大 GPU，核显/T4 都过剩", 13, False, TEXT_DARK),
            ("· 评审主流程不需 GPU（走云 API）", 13, False, TEXT_DARK),
        ]),
        add_text(s, 0.90, 5.65, 11.50, 0.60,
                 [("核心结论：资源需求很小，4核CPU+8~16G内存足够；GPU 可选（小容量即可）。", 15, True, GREEN)]),
    ))

    # ---- P6 部署路线 ----
    content(prs, "04 云服务器计划：部署路线与成本", "纯CPU起步 · GPU按量补充", 6, lambda s: (
        add_text(s, 0.90, 1.50, 11.50, 0.55, [("两条部署路线：", 15, True, PURPLE)]),
        card(s, 0.90, 2.10, 5.50, 2.30, [
            ("路线A 纯CPU（推荐起步）", 16, True, PURPLE),
            ("· 4核8GB 轻量云服务器", 13, False, TEXT_DARK),
            ("· 评审/RAG/解析/PDF 全能跑", 13, False, TEXT_DARK),
            ("· AIGC 用 CPU 慢跑或暂缓", 13, False, TEXT_DARK),
            ("· 月费约 ¥150~250", 13, True, GREEN),
        ]),
        card(s, 6.70, 2.10, 5.70, 2.30, [
            ("路线B CPU + 小GPU", 16, True, PURPLE),
            ("· 4核 + 一张 8~16GB 显存 GPU(如T4)", 13, False, TEXT_DARK),
            ("· 完整保留 AIGC 高并发", 13, False, TEXT_DARK),
            ("· 月费约 ¥1500~2500", 13, False, TEXT_DARK),
            ("· GPU 用按量/抢占式更省钱", 13, True, GREEN),
        ]),
        add_text(s, 0.90, 4.70, 11.50, 0.55, [("部署前必改配置：", 15, True, PURPLE)]),
        card(s, 0.90, 5.30, 11.50, 1.35, [
            ("· AIGC 设备从 cuda:5 改 auto；确认 LOCAL_FILES_ONLY 与模型权重上传", 13, False, TEXT_DARK),
            ("· 国内公网需 ICP 备案（1~2周）；海外 VPS 免备案但延迟略高", 13, False, TEXT_DARK),
            ("· 安全：改默认管理员密码、防火墙只开 80/443/22、密钥用环境变量", 13, False, TEXT_DARK),
            ("· 迁移数据：debate.db、RAG索引、offline/aigc_detector_zhv3、tectonic", 13, False, TEXT_DARK),
        ])))

    # ---- P7 推荐组合 ----
    content(prs, "04 云服务器计划：我的推荐", "低成本起步 · 按需扩容", 7, lambda s: (
        card(s, 0.90, 1.50, 5.50, 3.30, [
            ("推荐组合", 17, True, PURPLE),
            ("1. 起步：纯CPU 4C8G，¥150~250/月", 14, True, TEXT_DARK),
            ("   先跑通公网评审核心流程", 13, False, TEXT_DARK),
            ("2. AIGC 用 CPU 后台慢跑", 13, False, TEXT_DARK),
            ("3. 确有高并发 → 按量 GPU 补充", 13, False, TEXT_DARK),
            ("   (T4 按小时 ¥2~3，批跑完即停)", 12.5, False, TEXT_DARK),
        ]),
        card(s, 6.70, 1.50, 5.70, 3.30, [
            ("为什么这么选", 17, True, PURPLE),
            ("· AIGC 模型小，GPU 需求极低", 13, False, TEXT_DARK),
            ("· 评审主流程走云端 API，不吃本机算力", 13, False, TEXT_DARK),
            ("· CPU 是主要需求，GPU 是锦上添花", 13, False, TEXT_DARK),
            ("· 按量 GPU 比包月省 80%+", 13, True, GREEN),
        ]),
        add_text(s, 0.90, 5.15, 11.50, 0.60, [("待办 / 下一步：", 15, True, PURPLE)]),
        card(s, 0.90, 5.75, 11.50, 0.90, [
            ("· 云机部署预检：纯 CPU / 小 GPU 下跑通评审 + AIGC", 13, False, TEXT_DARK),
            ("· 生成云机部署脚本 + 环境检查清单 + 上传文件清单", 13, False, TEXT_DARK),
        ])))

    closing(prs)

    out = "/nvme/home/rincug/qhz/docs/睿文智评-AIGC检测优化与云服务器计划-2026-10-31.pptx"
    prs.core_properties.title = "睿文智评：AIGC检测优化 · 云服务器部署计划"
    prs.core_properties.author = "睿文智评"
    prs.save(out)
    print("saved:", out)


if __name__ == "__main__":
    main()
