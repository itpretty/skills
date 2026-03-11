#!/usr/bin/env python3
"""
Convert research proposal Markdown to professional PDF with:
- Cover page
- Clickable Table of Contents with internal PDF links
- Full content with embedded images, bookmarks
- Publication-quality typography with full Unicode support
"""

import re
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Image, PageBreak, NextPageTemplate,
    Table, TableStyle, Flowable
)
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_W, PAGE_H = A4
MARGIN_L, MARGIN_R = 2.5*cm, 2.5*cm
MARGIN_T, MARGIN_B = 2.8*cm, 2.5*cm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

PRIMARY = HexColor('#1565C0')
DARK = HexColor('#212121')
MUTED = HexColor('#616161')
RULE_COLOR = HexColor('#BDBDBD')
LINK_COLOR = HexColor('#1565C0')

# ============================================================
# Font registration — STIX Two (scientific/technical publishing font)
# ============================================================
# STIX Two Text: designed for scientific publishing, covers subscripts (₀-₉),
#   Greek letters (α, β, π, σ…), superscripts (¹²³), degree (°), em/en dashes.
# STIX Two Math: full Unicode math coverage including arrows (→←↔),
#   comparisons (≤≥≈≠), and all mathematical operators.
# Bundled TTF files live alongside this script in the fonts/ directory.
FONT = 'STIXText'
FONT_BOLD = 'STIXText-Bold'
FONT_ITALIC = 'STIXText-Italic'
FONT_BOLD_ITALIC = 'STIXText-BoldItalic'
FONT_MATH = 'STIXMath'
FONT_MONO = 'Courier'

# Characters that STIX Two Text lacks but STIX Two Math covers
_MATH_FALLBACK_CHARS = set(
    '\u2192\u2190\u2194\u21D2\u21D0\u21D4'  # arrows: → ← ↔ ⇒ ⇐ ⇔
    '\u2248\u2264\u2265\u2260\u226A\u226B'  # comparisons: ≈ ≤ ≥ ≠ ≪ ≫
    '\u2261\u2262\u221D\u221E\u2205'        # ≡ ≢ ∝ ∞ ∅
    '\u222B\u2211\u220F\u221A\u2202'        # ∫ ∑ ∏ √ ∂
    '\u2207\u2208\u2209\u2229\u222A'        # ∇ ∈ ∉ ∩ ∪
    '\u2227\u2228\u00AC'                    # ∧ ∨ ¬
)

_fonts_registered = False

def _register_fonts():
    """Register STIX Two fonts. Falls back to Helvetica if unavailable."""
    global _fonts_registered, FONT, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC, FONT_MATH
    if _fonts_registered:
        return
    _fonts_registered = True

    from reportlab.lib.fonts import addMapping

    # Font directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(script_dir, 'fonts')

    font_files = {
        FONT:            os.path.join(font_dir, 'STIXTwoText-Regular.ttf'),
        FONT_BOLD:       os.path.join(font_dir, 'STIXTwoText-Bold.ttf'),
        FONT_ITALIC:     os.path.join(font_dir, 'STIXTwoText-Italic.ttf'),
        FONT_BOLD_ITALIC: os.path.join(font_dir, 'STIXTwoText-BoldItalic.ttf'),
        FONT_MATH:       os.path.join(font_dir, 'STIXTwoMath-Regular.ttf'),
    }

    # Check that at least the regular font exists
    if not os.path.exists(font_files[FONT]):
        FONT = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'
        FONT_ITALIC = 'Helvetica-Oblique'
        FONT_BOLD_ITALIC = 'Helvetica-BoldOblique'
        FONT_MATH = 'Helvetica'
        print(f"Warning: STIX Two fonts not found in {font_dir}, "
              "falling back to Helvetica (limited Unicode)")
        return

    try:
        for name, path in font_files.items():
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
            elif name == FONT_MATH:
                FONT_MATH = FONT  # math fallback to text font
            else:
                # Missing styled variant — fall back to regular
                pdfmetrics.registerFont(TTFont(name, font_files[FONT]))

        # Map as a font family so <b>/<i> tags in Paragraph work
        addMapping('STIXText', 0, 0, FONT)
        addMapping('STIXText', 1, 0, FONT_BOLD)
        addMapping('STIXText', 0, 1, FONT_ITALIC)
        addMapping('STIXText', 1, 1, FONT_BOLD_ITALIC)

    except Exception as e:
        FONT = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'
        FONT_ITALIC = 'Helvetica-Oblique'
        FONT_BOLD_ITALIC = 'Helvetica-BoldOblique'
        FONT_MATH = 'Helvetica'
        print(f"Warning: Font registration failed ({e}), falling back to Helvetica")


def _apply_math_fallback(text):
    """Wrap characters needing STIX Two Math in <font> tags for reportlab."""
    if FONT_MATH == FONT:
        return text  # no separate math font available
    result = []
    math_buf = []
    for ch in text:
        if ch in _MATH_FALLBACK_CHARS:
            math_buf.append(ch)
        else:
            if math_buf:
                result.append(f'<font face="{FONT_MATH}">{"".join(math_buf)}</font>')
                math_buf = []
            result.append(ch)
    if math_buf:
        result.append(f'<font face="{FONT_MATH}">{"".join(math_buf)}</font>')
    return ''.join(result)


# ============================================================
# Flowables
# ============================================================
class HRFlowable(Flowable):
    def __init__(self, width, color=RULE_COLOR, thickness=1):
        super().__init__()
        self._width = width
        self._color = color
        self._thickness = thickness
        self.width = width
        self.height = thickness + 2*mm

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self._color)
        self.canv.setLineWidth(self._thickness)
        y = self.height / 2
        self.canv.line(0, y, self._width, y)
        self.canv.restoreState()

    def wrap(self, availWidth, availHeight):
        self.width = min(self._width, availWidth)
        return (self.width, self.height)


class BookmarkAnchor(Flowable):
    """Invisible flowable that creates a named destination + outline entry."""
    def __init__(self, name, level=0, title=''):
        super().__init__()
        self._name = name
        self._level = level
        self._title = title
        self.width = 0
        self.height = 0

    def draw(self):
        self.canv.bookmarkHorizontal(self._name, 0, 15*mm)
        if self._title:
            self.canv.addOutlineEntry(self._title, self._name, level=self._level)

    def wrap(self, availWidth, availHeight):
        return (0, 0)


# ============================================================
# Page templates with headers/footers
# ============================================================
def _cover_page(canvas, doc):
    """No header/footer on cover page."""
    pass

def _toc_page(canvas, doc):
    """Page number only on TOC pages."""
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(PAGE_W / 2, 1.3*cm, f"— {canvas.getPageNumber()} —")
    canvas.restoreState()

_running_header_text = 'Research Proposal'

def _content_page(canvas, doc):
    """Page number + running header on content pages."""
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(PAGE_W / 2, 1.3*cm, f"— {canvas.getPageNumber()} —")
    # Running header
    canvas.setStrokeColor(RULE_COLOR)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_L, PAGE_H - 2.0*cm, PAGE_W - MARGIN_R, PAGE_H - 2.0*cm)
    header = _running_header_text
    header_max_w = PAGE_W - MARGIN_L - MARGIN_R
    header_size = 6.5
    # Auto-scale font to fit available width without truncating
    while header_size > 4:
        canvas.setFont(FONT_ITALIC, header_size)
        if canvas.stringWidth(header, FONT_ITALIC, header_size) <= header_max_w:
            break
        header_size -= 0.5
    canvas.drawString(MARGIN_L, PAGE_H - 1.85*cm, header)
    canvas.restoreState()


# ============================================================
# Markdown parsing
# ============================================================
def parse_md(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    elements = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')

        if not line.strip():
            i += 1
            continue

        # Skip <a id="..."> anchor tags
        if line.strip().startswith('<a id='):
            i += 1
            continue

        # Handle standalone HTML break lines like <br/>, <br>, <br/><br/> → spacer
        if re.match(r'^(<br\s*/?>)+$', line.strip(), re.IGNORECASE):
            # Count the number of <br> tags to determine spacing
            br_count = len(re.findall(r'<br\s*/?>', line.strip(), re.IGNORECASE))
            elements.append({'type': 'spacer', 'lines': br_count})
            i += 1
            continue

        if line.strip() in ('---', '***', '___'):
            elements.append({'type': 'hr'})
            i += 1
            continue

        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            elements.append({'type': 'heading', 'level': level, 'text': title})
            i += 1
            continue

        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', line)
        if m:
            elements.append({'type': 'image', 'alt': m.group(1), 'src': m.group(2)})
            i += 1
            continue

        if line.startswith('>'):
            bq_lines = []
            while i < len(lines) and lines[i].rstrip('\n').startswith('>'):
                bq_lines.append(lines[i].rstrip('\n').lstrip('>').strip())
                i += 1
            elements.append({'type': 'blockquote', 'text': '\n'.join(bq_lines)})
            continue

        if line.startswith('|'):
            tbl_lines = []
            while i < len(lines) and lines[i].rstrip('\n').startswith('|'):
                tbl_lines.append(lines[i].rstrip('\n'))
                i += 1
            elements.append({'type': 'table', 'lines': tbl_lines})
            continue

        # TOC lines (- [text](#anchor)) — skip
        if re.match(r'^\s*-\s+\[', line):
            i += 1
            continue

        # **List of Figures** — skip
        if re.match(r'^\*\*List of Figures\*\*$', line.strip()):
            i += 1
            continue

        # Unordered list
        um = re.match(r'^[-*+]\s+(.*)', line)
        if um:
            items = []
            while i < len(lines):
                um2 = re.match(r'^[-*+]\s+(.*)', lines[i].rstrip('\n'))
                if um2:
                    items.append(um2.group(1).strip())
                    i += 1
                else:
                    break
            elements.append({'type': 'ulist', 'items': items})
            continue

        # Ordered list
        lm = re.match(r'^(\d+)\.\s+(.*)', line)
        if lm:
            items = []
            while i < len(lines):
                lm2 = re.match(r'^(\d+)\.\s+(.*)', lines[i].rstrip('\n'))
                if lm2:
                    items.append(lm2.group(2).strip())
                    i += 1
                else:
                    break
            elements.append({'type': 'olist', 'items': items})
            continue

        # Paragraph
        para_lines = []
        while i < len(lines):
            l = lines[i].rstrip('\n')
            if (not l.strip() or l.startswith('#') or l.startswith('>') or
                l.startswith('|') or l.startswith('![') or
                l.strip() in ('---','***','___') or
                l.strip().startswith('<a id=') or
                re.match(r'^(<br\s*/?>)+$', l.strip(), re.IGNORECASE) or
                re.match(r'^\s*-\s+\[', l) or
                re.match(r'^\*\*List of Figures\*\*$', l.strip())):
                break
            para_lines.append(l)
            i += 1
        if para_lines:
            elements.append({'type': 'paragraph', 'text': ' '.join(para_lines)})

    return elements


_SAFE_TAG_RE = re.compile(
    r'<('
    r'/?(?:b|i|u|sub|sup|strike|span|font|a|para)\b[^>]*'  # opening/closing tags
    r'|br\s*/?'                                              # self-closing <br/> or <br>
    r')>',
    re.IGNORECASE
)


def md_inline(text):
    """Convert markdown inline formatting to reportlab XML.

    Unicode characters (₂, α, π, etc.) are rendered natively by STIX Two Text.
    Characters outside its coverage (→, ≤, ≈, etc.) are automatically wrapped
    in <font face="STIXMath"> tags using the STIX Two Math fallback font.
    In-text citations (Author, Year) are linked to their references.
    """
    # Link in-text citations to reference anchors (before XML escaping)
    text = _link_citations(text)
    # Apply math-font fallback for characters STIX Two Text doesn't cover.
    # Must happen BEFORE XML escaping so the <font>/<a> tags survive.
    text = _apply_math_fallback(text)

    # XML-escape & < > but preserve tags that reportlab understands.
    safe_tags = []
    def _save_tag(m):
        safe_tags.append(m.group(0))
        return f'\x00TAG{len(safe_tags)-1}\x00'
    text = _SAFE_TAG_RE.sub(_save_tag, text)
    # Now XML-escape everything else
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    # Restore safe tags
    for idx, tag in enumerate(safe_tags):
        text = text.replace(f'\x00TAG{idx}\x00', tag)

    # Markdown formatting
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'`([^`]+)`', lambda m: f'<font face="{FONT_MONO}" size="7.5">{m.group(1)}</font>', text)
    return text


def make_anchor(text):
    """Generate GFM-style anchor from heading text."""
    s = text.lower()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s


# ============================================================
# Citation linking: in-text (Author, Year) → clickable [N] links
# ============================================================
_citation_map = {}  # "Author, Year" -> ref number

def _build_citation_map(parsed):
    """Build a mapping from 'Author, Year' strings to reference numbers.

    Handles single-author, two-author (&), and multi-author (et al.) forms.
    For a reference by "Tojo, G., & Fernández, M. (2006)", generates keys:
      "Tojo, 2006", "Tojo & Fernández, 2006", "Tojo et al., 2006"
    """
    global _citation_map
    _citation_map = {}

    in_refs = False
    ref_num = 0
    for el in parsed:
        if el['type'] == 'heading' and el['level'] == 2:
            clean = re.sub(r'^\d+(\.\d+)*\.?\s*', '', el['text'])
            in_refs = clean.lower().strip() == 'references'
            continue
        if in_refs and el['type'] == 'paragraph':
            ref_num += 1
            text = el['text']
            # Extract first author last name (Unicode-aware)
            m = re.match(r'^(\w[\w\-\']+)', text, re.UNICODE)
            m_year = re.search(r'\((\d{4})\)', text)
            if not (m and m_year):
                continue
            first_author = m.group(1)
            year = m_year.group(1)
            pre_year = text[:m_year.start()]

            # Extract second author last name if present (after &)
            second_author = None
            amp_match = re.search(r'&\s+(\w[\w\-\']+)', pre_year, re.UNICODE)
            if amp_match:
                second_author = amp_match.group(1)

            # Count total authors
            has_multiple = '&' in pre_year or pre_year.count(',') > 2

            # Register all citation forms, first match wins
            def _add(key):
                if key not in _citation_map:
                    _citation_map[key] = ref_num

            _add(f'{first_author}, {year}')
            if second_author:
                _add(f'{first_author} & {second_author}, {year}')
            if has_multiple:
                _add(f'{first_author} et al., {year}')


# Regex for a single citation entry within parentheses:
#   "Author, Year"  |  "Author et al., Year"  |  "Author & Author, Year"
_CITE_RE = (
    r'(\w[\w\-\']+(?:\s\w[\w\-\']+)*'   # first author (possibly multi-word)
    r'(?:\s&\s\w[\w\-\']+)*'             # optional "& SecondAuthor"
    r'(?:\set\sal\.)?'                    # optional "et al."
    r',\s*\d{4})'                         # ", Year"
)

# Full citation group: (cite1; cite2; ...)
_CITE_GROUP_RE = re.compile(
    r'\((' + _CITE_RE + r'(?:;\s*' + _CITE_RE + r')*)\)',
    re.UNICODE
)


def _link_citations(text):
    """Replace in-text citations (Author, Year) with clickable links to references."""
    if not _citation_map:
        return text

    def _replace_citation_group(m):
        full = m.group(1)
        # Split by semicolons for multiple citations
        parts = re.split(r';\s*', full)
        linked_parts = []
        for part in parts:
            part = part.strip()
            if part in _citation_map:
                ref_num = _citation_map[part]
                linked_parts.append(
                    f'<a href="#ref-{ref_num}" color="#1565C0">{part}</a>')
            else:
                linked_parts.append(part)
        return '(' + '; '.join(linked_parts) + ')'

    text = _CITE_GROUP_RE.sub(_replace_citation_group, text)
    return text


# ============================================================
# Build PDF
# ============================================================
def build_pdf(md_file, out_pdf=None):
    """Convert a research proposal Markdown file to a professional PDF.

    Args:
        md_file: Path to the input Markdown file.
        out_pdf: Path for the output PDF. Defaults to same name as md_file with .pdf extension.
    """
    _register_fonts()

    md_file = os.path.abspath(md_file)
    base_dir = os.path.dirname(md_file)
    if out_pdf is None:
        out_pdf = os.path.splitext(md_file)[0] + '.pdf'

    parsed = parse_md(md_file)
    _build_citation_map(parsed)

    # Extract document title from the first H1 heading
    doc_title = 'Research Proposal'
    for el in parsed:
        if el['type'] == 'heading' and el['level'] == 1:
            doc_title = el['text']
            break

    # Set running header for content pages
    global _running_header_text
    _running_header_text = f'{doc_title} — Research Proposal'

    # Create document with multiple page templates
    frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B,
                  id='normal')

    doc = BaseDocTemplate(
        out_pdf, pagesize=A4,
        title=doc_title,
        author='Research Proposal',
    )
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[frame], onPage=_cover_page),
        PageTemplate(id='toc', frames=[frame], onPage=_toc_page),
        PageTemplate(id='content', frames=[frame], onPage=_content_page),
    ])

    styles = getSampleStyleSheet()

    s_title = ParagraphStyle('PT', parent=styles['Title'],
        fontSize=18, leading=23, textColor=PRIMARY, alignment=TA_CENTER,
        spaceAfter=5*mm, fontName=FONT_BOLD)

    s_subtitle = ParagraphStyle('PSub', parent=styles['Normal'],
        fontSize=9.5, leading=13, textColor=MUTED, alignment=TA_CENTER,
        spaceAfter=2.5*mm, fontName=FONT)

    s_h2 = ParagraphStyle('H2', fontName=FONT_BOLD,
        fontSize=12, leading=16, textColor=DARK,
        spaceBefore=5*mm, spaceAfter=2*mm)

    s_h3 = ParagraphStyle('H3', fontName=FONT_BOLD,
        fontSize=10.5, leading=14, textColor=HexColor('#424242'),
        spaceBefore=3.5*mm, spaceAfter=1.5*mm)

    s_body = ParagraphStyle('Body', fontName=FONT,
        fontSize=9, leading=13, textColor=DARK,
        alignment=TA_JUSTIFY, spaceBefore=1*mm, spaceAfter=1.5*mm)

    s_bq = ParagraphStyle('BQ', fontName=FONT_ITALIC,
        fontSize=8, leading=11.5, textColor=MUTED,
        spaceBefore=1*mm, spaceAfter=1*mm)

    s_olist = ParagraphStyle('OL', fontName=FONT,
        fontSize=9, leading=13, textColor=DARK,
        alignment=TA_JUSTIFY, leftIndent=5*mm, bulletIndent=0,
        spaceBefore=1*mm, spaceAfter=1*mm)

    s_ulist = ParagraphStyle('UL', fontName=FONT,
        fontSize=9, leading=13, textColor=DARK,
        alignment=TA_JUSTIFY, leftIndent=5*mm, bulletIndent=0,
        spaceBefore=1*mm, spaceAfter=1*mm)

    s_caption = ParagraphStyle('Cap', fontName=FONT_ITALIC,
        fontSize=7.5, leading=10, textColor=MUTED,
        alignment=TA_CENTER, spaceBefore=1*mm, spaceAfter=3*mm)

    s_toc_title = ParagraphStyle('TOCT', fontName=FONT_BOLD,
        fontSize=15, leading=20, textColor=PRIMARY, alignment=TA_CENTER,
        spaceAfter=3.5*mm)

    s_toc_link1 = ParagraphStyle('TOCL1', fontName=FONT_BOLD,
        fontSize=9.5, leading=15, textColor=LINK_COLOR, leftIndent=0, spaceBefore=1.5*mm)

    s_toc_link2 = ParagraphStyle('TOCL2', fontName=FONT,
        fontSize=9, leading=13.5, textColor=LINK_COLOR, leftIndent=8*mm, spaceBefore=0.3*mm)

    s_fig_entry = ParagraphStyle('FigE', fontName=FONT,
        fontSize=8.5, leading=13.5, textColor=LINK_COLOR, leftIndent=4*mm, spaceBefore=0.5*mm)

    # ---- First pass: collect TOC entries and figure anchors ----
    toc_entries = []
    fig_entries = []
    sec_num = [0, 0, 0]
    skipped_h1 = False

    for el in parsed:
        if el['type'] == 'heading':
            level = el['level']
            title = el['text']
            if 'Table of Contents' in title:
                continue
            if level == 1:
                if not skipped_h1:
                    skipped_h1 = True
                    continue
            elif level == 2:
                anchor = make_anchor(title)
                clean = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
                sec_num[0] += 1; sec_num[1] = 0; sec_num[2] = 0
                display = f"{sec_num[0]}. {clean}"
                toc_entries.append({'level': 1, 'text': clean, 'anchor': anchor, 'display': display})
            elif level == 3:
                anchor = make_anchor(title)
                clean = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
                sec_num[1] += 1; sec_num[2] = 0
                display = f"{sec_num[0]}.{sec_num[1]} {clean}"
                toc_entries.append({'level': 2, 'text': clean, 'anchor': anchor, 'display': display})

        elif el['type'] == 'image':
            alt = el.get('alt', '')
            if alt.startswith('Figure'):
                fig_anchor = make_anchor(alt)
                fig_entries.append({'text': alt, 'anchor': fig_anchor})

    story = []

    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 55*mm))
    story.append(HRFlowable(CONTENT_W, PRIMARY, 2.5))
    story.append(Spacer(1, 6*mm))
    cover_title = md_inline(doc_title)
    story.append(Paragraph(cover_title, s_title))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('Research Proposal', s_subtitle))
    story.append(Paragraph('PhD Programme in Chemistry / Bioinorganic Catalysis', s_subtitle))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph('March 2026', s_subtitle))
    story.append(Spacer(1, 30*mm))
    story.append(HRFlowable(CONTENT_W, PRIMARY, 2.5))
    story.append(NextPageTemplate('toc'))
    story.append(PageBreak())

    # ==================== TABLE OF CONTENTS ====================
    story.append(BookmarkAnchor('toc', 0, 'Table of Contents'))
    story.append(Paragraph('Table of Contents', s_toc_title))
    story.append(HRFlowable(CONTENT_W, RULE_COLOR, 0.5))
    story.append(Spacer(1, 4*mm))

    for entry in toc_entries:
        link_text = f'<a href="#{entry["anchor"]}" color="#1565C0">{md_inline(entry["display"])}</a>'
        style = s_toc_link1 if entry['level'] == 1 else s_toc_link2
        story.append(Paragraph(link_text, style))

    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(CONTENT_W, RULE_COLOR, 0.5))
    story.append(Spacer(1, 3*mm))

    # List of Figures
    story.append(Paragraph(
        '<b>List of Figures</b>',
        ParagraphStyle('FigHead', fontName=FONT_BOLD, fontSize=11,
                       textColor=PRIMARY, spaceBefore=2*mm, spaceAfter=2*mm)))

    for fig in fig_entries:
        link_text = f'<a href="#{fig["anchor"]}" color="#1565C0">{fig["text"]}</a>'
        story.append(Paragraph(link_text, s_fig_entry))

    story.append(NextPageTemplate('content'))
    story.append(PageBreak())

    # ==================== MAIN CONTENT ====================
    s_ref = ParagraphStyle('Ref', fontName=FONT,
        fontSize=7, leading=10, textColor=DARK,
        alignment=TA_LEFT, spaceBefore=0.5*mm, spaceAfter=1*mm)

    sec_num = [0, 0, 0]
    skipped_h1 = False
    in_references = False
    ref_counter = 0

    for el in parsed:
        if el['type'] == 'heading':
            level = el['level']
            title = el['text']

            if 'Table of Contents' in title:
                continue

            if level == 1:
                if not skipped_h1:
                    skipped_h1 = True
                    continue

            elif level == 2:
                anchor = make_anchor(title)
                clean = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
                in_references = clean.lower().strip() == 'references'
                sec_num[0] += 1; sec_num[1] = 0; sec_num[2] = 0
                numbered = f"{sec_num[0]}. {clean}"
                story.append(BookmarkAnchor(anchor, 0, numbered))
                story.append(Spacer(1, 2*mm))
                story.append(Paragraph(f'<a name="{anchor}"/>{md_inline(numbered)}', s_h2))

            elif level == 3:
                anchor = make_anchor(title)
                clean = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
                sec_num[1] += 1; sec_num[2] = 0
                numbered = f"{sec_num[0]}.{sec_num[1]} {clean}"
                story.append(BookmarkAnchor(anchor, 1, numbered))
                story.append(Paragraph(f'<a name="{anchor}"/>{md_inline(numbered)}', s_h3))

        elif el['type'] == 'paragraph':
            if in_references:
                ref_counter += 1
                story.append(Paragraph(
                    f'<a name="ref-{ref_counter}"/>[{ref_counter}] {md_inline(el["text"])}',
                    s_ref))
            else:
                story.append(Paragraph(md_inline(el['text']), s_body))

        elif el['type'] == 'image':
            src = el['src']
            if src.startswith('./'):
                src = src[2:]
            img_path = os.path.join(base_dir, src)
            alt = el.get('alt', '')

            if os.path.exists(img_path):
                if alt.startswith('Figure'):
                    fig_anchor = make_anchor(alt)
                    story.append(BookmarkAnchor(fig_anchor, 1, alt))

                ir = ImageReader(img_path)
                iw, ih = ir.getSize()
                max_w = CONTENT_W
                max_h = 170*mm
                scale = min(max_w / iw, max_h / ih)
                w, h = iw * scale, ih * scale

                story.append(Spacer(1, 4*mm))
                story.append(Image(img_path, width=w, height=h))
                if alt:
                    story.append(Spacer(1, 1*mm))
                    if alt.startswith('Figure'):
                        fig_anchor = make_anchor(alt)
                        story.append(Paragraph(f'<a name="{fig_anchor}"/>{md_inline(alt)}', s_caption))
                    else:
                        story.append(Paragraph(md_inline(alt), s_caption))
                story.append(Spacer(1, 3*mm))

        elif el['type'] == 'blockquote':
            bq_text = el['text'].replace('\n', '<br/>')
            bq_text = md_inline(bq_text)
            bq_para = Paragraph(bq_text, s_bq)
            bq_table = Table([[bq_para]], colWidths=[CONTENT_W])
            bq_table.setStyle(TableStyle([
                ('LEFTPADDING', (0,0), (-1,-1), 3*mm),
                ('RIGHTPADDING', (0,0), (-1,-1), 3*mm),
                ('TOPPADDING', (0,0), (-1,-1), 3*mm),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3*mm),
                ('BACKGROUND', (0,0), (-1,-1), HexColor('#F8F9FA')),
            ]))
            story.append(Spacer(1, 2*mm))
            story.append(bq_table)
            story.append(Spacer(1, 2*mm))

        elif el['type'] == 'olist':
            for idx, item in enumerate(el['items'], 1):
                story.append(Paragraph(f"<b>{idx}.</b>  {md_inline(item)}", s_olist))

        elif el['type'] == 'ulist':
            for item in el['items']:
                story.append(Paragraph(f"\u2022  {md_inline(item)}", s_ulist))

        elif el['type'] == 'table':
            tbl_lines = el['lines']
            rows = []
            for j, tl in enumerate(tbl_lines):
                cells = [c.strip() for c in tl.strip('|').split('|')]
                if j == 1 and all(set(c.strip()) <= set('-|: ') for c in cells):
                    continue
                rows.append(cells)

            if rows:
                num_cols = len(rows[0])
                col_w = CONTENT_W / num_cols
                last_row = len(rows) - 1

                tbl_data = []
                for j, row in enumerate(rows):
                    styled_row = []
                    for cell in row:
                        cell_clean = md_inline(cell)
                        if j == 0:
                            styled_row.append(Paragraph(cell_clean,
                                ParagraphStyle('TH', fontName=FONT_BOLD,
                                    fontSize=8, leading=11, textColor=DARK, alignment=TA_LEFT)))
                        else:
                            styled_row.append(Paragraph(cell_clean,
                                ParagraphStyle('TD', fontName=FONT,
                                    fontSize=7.5, leading=11, textColor=DARK, alignment=TA_LEFT)))
                    tbl_data.append(styled_row)

                tbl = Table(tbl_data, colWidths=[col_w]*num_cols)
                tbl.setStyle(TableStyle([
                    # Booktabs style with light row separators
                    ('LINEABOVE', (0,0), (-1,0), 1, DARK),        # top rule
                    ('LINEBELOW', (0,0), (-1,0), 0.5, DARK),      # below header
                    ('LINEBELOW', (0,1), (-1,-2), 0.25, DARK),  # row borders
                    ('LINEBELOW', (0,last_row), (-1,last_row), 1, black),  # bottom rule
                    ('TOPPADDING', (0,0), (-1,-1), 2*mm),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
                    ('LEFTPADDING', (0,0), (-1,-1), 3*mm),
                    ('RIGHTPADDING', (0,0), (-1,-1), 3*mm),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                story.append(Spacer(1, 3*mm))
                story.append(tbl)
                story.append(Spacer(1, 3*mm))

        elif el['type'] == 'spacer':
            story.append(Spacer(1, el.get('lines', 1) * 4*mm))

        elif el['type'] == 'hr':
            story.append(Spacer(1, 2*mm))
            story.append(HRFlowable(CONTENT_W, RULE_COLOR, 0.5))
            story.append(Spacer(1, 2*mm))

    doc.build(story)
    print(f"PDF saved: {out_pdf}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.md> [output.pdf]")
        sys.exit(1)
    md_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None
    build_pdf(md_path, pdf_path)
