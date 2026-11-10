# -*- coding: utf-8 -*-
"""Build the Experiment 2 report DOCX from the Markdown source.

Run with the bundled Python:
  python lab2/report/build_report.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).with_name("实验2_报告.md")
OUT = Path(__file__).with_name("实验2_报告.docx")

BODY_FONT = "宋体"
HEAD_FONT = "黑体"
LATIN_FONT = "Times New Roman"
MONO_FONT = "Consolas"
INK = RGBColor(0x1B, 0x24, 0x30)
BRAND = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x6B, 0x77, 0x85)
LIGHT = RGBColor(0x9A, 0xA5, 0xB1)


def set_run_font(run, name=BODY_FONT, size=None, bold=None, color=None,
                 latin=LATIN_FONT):
    run.font.name = latin
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), latin)
    rFonts.set(qn("w:hAnsi"), latin)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def add_inline(par, text, size=10.5, bold=False, color=INK, font=BODY_FONT):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            run = par.add_run(piece[2:-2])
            set_run_font(run, font, size, True, color)
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            run = par.add_run(piece[1:-1])
            set_run_font(run, BODY_FONT, size - 0.5, bold, RGBColor(0x9C, 0x27, 0x00), MONO_FONT)
        else:
            run = par.add_run(piece)
            set_run_font(run, font, size, bold, color)


def add_field(par, instr, placeholder=""):
    run = par.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text_el = OxmlElement("w:t")
    text_el.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr_el)
    run._r.append(separate)
    run._r.append(text_el)
    run._r.append(end)
    return run


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def add_bottom_border(par, color="1F3A5F", size=6):
    pPr = par._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    pPr.append(borders)


def setup_document():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.3)
    sec.right_margin = Cm(2.3)
    sec.different_first_page_header_footer = True

    normal = doc.styles["Normal"]
    normal.font.name = LATIN_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    pf = normal.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.first_line_indent = Pt(21)

    for level, size in ((1, 16), (2, 14), (3, 12), (4, 11)):
        st = doc.styles[f"Heading {level}"]
        st.font.name = HEAD_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = BRAND
        st.element.rPr.rFonts.set(qn("w:eastAsia"), HEAD_FONT)
        st.paragraph_format.space_before = Pt({1: 6, 2: 14, 3: 10, 4: 8}[level])
        st.paragraph_format.space_after = Pt({1: 12, 2: 6, 3: 4, 4: 3}[level])
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.first_line_indent = Pt(0)
        if level == 1:
            st.paragraph_format.page_break_before = True

    # header
    header = sec.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("软件工程实验二 · 酒店预订系统设计与实现")
    set_run_font(hr, BODY_FONT, 9, False, MUTED)
    add_bottom_border(hp, "E3E8EF", 4)

    # footer with PAGE / NUMPAGES
    footer = sec.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("第 ")
    set_run_font(r, BODY_FONT, 9, False, MUTED)
    add_field(fp, " PAGE ", "1")
    r = fp.add_run(" 页 / 共 ")
    set_run_font(r, BODY_FONT, 9, False, MUTED)
    add_field(fp, " NUMPAGES ", "1")
    r = fp.add_run(" 页")
    set_run_font(r, BODY_FONT, 9, False, MUTED)

    # ask Word/LibreOffice to refresh TOC and page fields
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    return doc


def add_section(doc, landscape):
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width = Cm(29.7)
        sec.page_height = Cm(21.0)
    else:
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.3)
    sec.right_margin = Cm(2.3)
    sec.different_first_page_header_footer = False
    sec.header.is_linked_to_previous = True
    sec.footer.is_linked_to_previous = True
    return sec


def add_cover(doc):
    # top label band
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Cm(16.4)
    shade_cell(cell, "1F3A5F")
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("软件工程 · 实验二")
    set_run_font(r, HEAD_FONT, 12, True, RGBColor(0xFF, 0xFF, 0xFF))

    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run("酒店预订系统")
    set_run_font(r, HEAD_FONT, 30, True, BRAND)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run("面向对象设计与 UI 设计")
    set_run_font(r, HEAD_FONT, 17, True, RGBColor(0x2C, 0x52, 0x82))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run("—— 基于 51 条需求、7 张 UML 与 14 屏 UI 的设计报告")
    set_run_font(r, BODY_FONT, 11, False, MUTED)
    add_bottom_border(p, "C9A227", 8)

    for _ in range(3):
        doc.add_paragraph()

    info = [
        ("课程名称", "软件工程"),
        ("实验名称", "实验二  面向对象设计与 UI 设计"),
        ("学    号", "241220053"),
        ("姓    名", "黄若希"),
        ("完成日期", "2026 年 11 月 10 日"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in info:
        cells = t.add_row().cells
        cells[0].width = Cm(3.6)
        cells[1].width = Cm(9.0)
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r0 = p0.add_run(k)
        set_run_font(r0, BODY_FONT, 11, False, MUTED)
        p1 = cells[1].paragraphs[0]
        p1.paragraph_format.left_indent = Pt(12)
        r1 = p1.add_run(v)
        set_run_font(r1, BODY_FONT, 12, True, INK)

    for _ in range(5):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run("仓库：github.com/Ash-Klein/hotel-booking-system　|　分支：lab2")
    set_run_font(r, BODY_FONT, 9, False, MUTED)

    doc.add_page_break()


def add_bookmark(par, name, bid):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bid))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bid))
    par._p.insert(1, start)
    par._p.append(end)


def add_toc(doc, entries):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("目　录")
    set_run_font(r, HEAD_FONT, 18, True, BRAND)

    for level, title, bm in entries:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Cm(0 if level == 1 else 0.8)
        p.paragraph_format.space_before = Pt(5 if level == 1 else 1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(16.2), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        r = p.add_run(title)
        set_run_font(r, BODY_FONT, 10.5 if level == 2 else 11, level == 1, INK)
        p.add_run("\t")
        add_field(p, f" PAGEREF {bm} \\h ", "0")
        for run in p.runs:
            if not run.text:
                set_run_font(run, BODY_FONT, 10.5, False, INK)


def add_table(doc, rows):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=ncol)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_cell_margins(table)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        if i == 0:
            trPr = table.rows[0]._tr.get_or_add_trPr()
            tblHeader = OxmlElement("w:tblHeader")
            tblHeader.set(qn("w:val"), "true")
            trPr.append(tblHeader)
        for j in range(ncol):
            text = row[j] if j < len(row) else ""
            cell = cells[j]
            if i == 0:
                shade_cell(cell, "DCE6F2")
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.line_spacing = 1.1
            add_inline(p, text, 8.5, i == 0, INK)
    for idx, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.insert(0, cant)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, BODY_FONT, 9, True, MUTED)


def add_image(doc, caption, rel_path, width_cm):
    path = ROOT / rel_path
    if not path.exists():
        raise FileNotFoundError(path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))

    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.first_line_indent = Pt(0)
        c.paragraph_format.space_after = Pt(10)
        r = c.add_run(caption)
        set_run_font(r, BODY_FONT, 9, False, MUTED)


IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)(?:\{width=([\d.]+)cm\})?\s*$")
TABLE_CAP_RE = re.compile(r"^表\d+-\d+\s")
FIG_CAP_RE = re.compile(r"^图\d+-\d+\s")


def collect_toc(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            if title == "目 录":
                continue
            out.append((1, title, f"_Toc{9000 + len(out)}"))
        elif s.startswith("## "):
            out.append((2, s[3:].strip(), f"_Toc{9000 + len(out)}"))
    return out


def parse_markdown(doc, text, toc_entries):
    lines = text.split("\n")
    i = 0
    n = len(lines)
    ti = 0
    while i < n:
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue

        if line == "[[TOC]]":
            add_toc(doc, toc_entries)
            i += 1
            continue
        if line == "[[PAGEBREAK]]":
            doc.add_page_break()
            i += 1
            continue
        if line == "[[LANDSCAPE]]":
            add_section(doc, True)
            i += 1
            continue
        if line == "[[PORTRAIT]]":
            add_section(doc, False)
            i += 1
            continue

        m = IMG_RE.match(line)
        if m:
            add_image(doc, m.group(1), m.group(2), float(m.group(3) or 14))
            i += 1
            continue

        if line.startswith("```"):
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.left_indent = Pt(12)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.1
            r = p.add_run("\n".join(block))
            set_run_font(r, BODY_FONT, 8.5, False, RGBColor(0x33, 0x33, 0x33), MONO_FONT)
            i += 1
            continue

        if line.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.fullmatch(r"\|[\s:\-\|]+\|", row):
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
            continue

        if line.startswith("# "):
            title = line[2:].strip()
            if title == "目 录":
                i += 1
                continue
            p = doc.add_paragraph(style="Heading 1")
            if title.startswith("第一章"):
                p.paragraph_format.page_break_before = False
            if ti < len(toc_entries):
                add_bookmark(p, toc_entries[ti][2], 1000 + ti)
                ti += 1
            add_inline(p, title, 16, True, BRAND, HEAD_FONT)
            i += 1
            continue
        if line.startswith("## "):
            p = doc.add_paragraph(style="Heading 2")
            if ti < len(toc_entries):
                add_bookmark(p, toc_entries[ti][2], 1000 + ti)
                ti += 1
            add_inline(p, line[3:].strip(), 14, True, BRAND, HEAD_FONT)
            i += 1
            continue
        if line.startswith("### "):
            p = doc.add_paragraph(style="Heading 3")
            add_inline(p, line[4:].strip(), 12, True, BRAND, HEAD_FONT)
            i += 1
            continue
        if line.startswith("#### "):
            p = doc.add_paragraph(style="Heading 4")
            add_inline(p, line[5:].strip(), 11, True, BRAND, HEAD_FONT)
            i += 1
            continue

        if TABLE_CAP_RE.match(line.strip("*").strip()):
            add_caption(doc, line.strip("*").strip())
            i += 1
            continue

        if line.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(12)
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            add_inline(p, line.lstrip("> ").strip(), 9.5, False, MUTED)
            i += 1
            continue

        m = re.match(r"^([-*])\s+(.*)$", line)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, m.group(2), 10.5)
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(21)
            p.paragraph_format.first_line_indent = Pt(-21)
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, f"{m.group(1)}. {m.group(2)}", 10.5)
            i += 1
            continue

        # paragraph: merge soft-wrapped lines
        buf = [line]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("#", "|", "```", ">", "- ", "* ", "[[", "!["))
                    or re.match(r"^\d+\.\s", nxt) or TABLE_CAP_RE.match(nxt)):
                break
            buf.append(nxt)
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(21)
        p.paragraph_format.space_after = Pt(3)
        add_inline(p, " ".join(buf), 10.5)


def main():
    text = SRC.read_text(encoding="utf-8")
    entries = collect_toc(text)
    doc = setup_document()
    add_cover(doc)
    parse_markdown(doc, text, entries)
    doc.save(OUT)
    print(f"saved {OUT} ({len(entries)} TOC entries)")


if __name__ == "__main__":
    sys.exit(main())
