"""Export reviewer-facing PDFs. Optional tooling: reportlab and pypdf."""
import argparse
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def markup(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.replace('**', '').replace('`', '')
    return escape(text)


def export(source, filename, title, font, compact=False):
    text = source.read_text(encoding='utf-8')
    if compact:
        # The Git evidence appendix remains in Markdown; the PDF is the reflection body.
        text = text.split('## 4.')[0]
    body = ParagraphStyle('body', fontName=font, fontSize=10.5, leading=16,
                          textColor=colors.HexColor('#243d35'), wordWrap='CJK', spaceAfter=8)
    heading = ParagraphStyle('heading', parent=body, fontSize=12, leading=19, spaceBefore=9,
                             textColor=colors.HexColor('#245b49'), keepWithNext=True)
    quote = ParagraphStyle('quote', parent=body, leftIndent=12, rightIndent=9,
                           borderColor=colors.HexColor('#d4ded7'), borderWidth=0.5,
                           borderPadding=8, spaceBefore=4, spaceAfter=12)
    title_style = ParagraphStyle('title', parent=body, fontSize=20, leading=28, spaceAfter=12)
    story = [Paragraph(title, title_style)]
    for block in re.split(r'\n\s*\n', text):
        block = block.strip()
        if not block or block.startswith('# '):
            continue
        if block.startswith('## '):
            story.append(Paragraph(markup(block[3:]), heading))
        elif block.startswith('> '):
            story.append(Paragraph(markup(block[2:]), quote))
        else:
            story.append(Paragraph(markup(block).replace('\n', '<br/>'), body))

    if not compact:
        grouped, section = [story[0]], []
        for paragraph in story[1:]:
            if paragraph.style.name == 'heading' and section:
                grouped.append(KeepTogether(section))
                section = []
            section.append(paragraph)
        if section:
            grouped.append(KeepTogether(section))
        story = grouped

    def furniture(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor('#708277'))
        canvas.drawString(44, A4[1] - 28, 'AI PANEL STUDIO  /  DEVELOPMENT RECORD')
        canvas.drawString(44, 25, 'Codex 辅助开发 · 2026-11-18')
        canvas.drawRightString(A4[0] - 44, 25, str(doc.page))
        canvas.restoreState()

    destination = ROOT / 'output' / 'pdf' / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=44, rightMargin=44,
                      topMargin=48, bottomMargin=43, title=title, author='AI Panel Studio',
                      allowSplitting=1).build(story, onFirstPage=furniture, onLaterPages=furniture)
    reader = PdfReader(destination)
    if compact and len(reader.pages) != 1:
        raise ValueError('复盘必须排成一页；请检查正文与字号，不能交付超出要求的文件')
    if not all(page.extract_text().strip() for page in reader.pages):
        raise ValueError('PDF contains an empty page')
    print(f'{destination.relative_to(ROOT)}: {len(reader.pages)} page(s)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', default='C:/Windows/Fonts/simsun.ttc', help='Chinese TrueType font path')
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('PanelChinese', args.font, subfontIndex=0))
    export(ROOT / 'docs/workflow.md', 'workflow.pdf', '开发过程与工作流复盘', 'PanelChinese', compact=True)
    export(ROOT / 'docs/development-prompts.md', 'development-prompts.pdf', '核心开发 Prompt 与执行记录', 'PanelChinese')
