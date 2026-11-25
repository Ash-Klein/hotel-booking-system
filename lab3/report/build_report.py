"""Build the experiment-three report as a DOCX file.

Run with the bundled Python that provides python-docx:
    <python> lab3/report/build_report.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SCREEN = ROOT / "report" / "screenshots"
UML = ROOT / "UML"
OUTPUT = ROOT / "report" / "实验3_报告.docx"

NAVY = RGBColor(0x12, 0x26, 0x3A)
BLUE = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x6B, 0x7C, 0x8F)
GOLD = RGBColor(0xC9, 0xA2, 0x27)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x1B, 0x27, 0x33)


def set_font(run, name: str = "宋体", size: float = 10.5, bold: bool = False,
             color: RGBColor | None = None) -> None:
    """Set Western and East-Asian fonts on one run."""
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)


def body(doc: Document, text: str, *, indent: bool = True, size: float = 10.5,
         after: int = 5, before: int = 0) -> None:
    """Append a justified Chinese body paragraph."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.line_spacing = 1.45
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.space_before = Pt(before)
    if indent:
        paragraph.paragraph_format.first_line_indent = Pt(21)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = paragraph.add_run(text)
    set_font(run, "宋体", size, False, BLACK)


def lead(doc: Document, prefix: str, text: str) -> None:
    """Paragraph with a bold lead-in label."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.line_spacing = 1.45
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.first_line_indent = Pt(21)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    first = paragraph.add_run(prefix)
    set_font(first, "宋体", 10.5, True, NAVY)
    second = paragraph.add_run(text)
    set_font(second, "宋体", 10.5, False, BLACK)


def bullet(doc: Document, text: str, level: int = 0) -> None:
    """Append a bullet item without relying on template numbering."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Pt(21 + 18 * level)
    paragraph.paragraph_format.first_line_indent = Pt(-10)
    paragraph.paragraph_format.line_spacing = 1.35
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run("• " if level == 0 else "– ")
    set_font(run, "宋体", 10.5, True, BLUE)
    run = paragraph.add_run(text)
    set_font(run, "宋体", 10.5, False, BLACK)


def heading(doc: Document, text: str, level: int,
            new_page: bool = False) -> None:
    """Add a styled heading and keep it with the next paragraph."""
    paragraph = doc.add_heading(level=level)
    paragraph.paragraph_format.keep_with_next = True
    if level == 1 or new_page:
        paragraph.paragraph_format.page_break_before = True
    paragraph.paragraph_format.space_before = Pt(14 if level <= 2 else 8)
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(text)
    size = {1: 18, 2: 14, 3: 11.5}.get(level, 11)
    set_font(run, "微软雅黑", size, True, NAVY)


def code_block(doc: Document, text: str) -> None:
    """Monospace shaded code block."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.5)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.line_spacing = 1.0
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), "F2F5F9")
    paragraph._p.get_or_add_pPr().append(shading)
    run = paragraph.add_run(text)
    set_font(run, "Consolas", 8.5, False, RGBColor(0x1F, 0x3A, 0x5F))


def caption(doc: Document, text: str) -> None:
    """Figure/table caption."""
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(text)
    set_font(run, "宋体", 9, False, MUTED)


def picture(doc: Document, path: Path, width: float, cap: str) -> None:
    """Insert a centred image with a caption."""
    if not path.exists():
        body(doc, f"[缺失图片：{path.name}]")
        return
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.add_run().add_picture(str(path), width=Inches(width))
    caption(doc, cap)


def shade_cell(cell, color: str = "DCE6F2") -> None:
    """Fill a table cell."""
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    properties.append(shading)


def table(doc: Document, headers: list[str], rows: list[list[str]],
          widths: list[float] | None = None, font_size: float = 8.6) -> None:
    """Create a compact, shaded table."""
    obj = doc.add_table(rows=1, cols=len(headers))
    obj.style = "Table Grid"
    obj.alignment = WD_TABLE_ALIGNMENT.CENTER
    obj.autofit = True
    header_cells = obj.rows[0].cells
    for index, header in enumerate(headers):
        header_cells[index].text = ""
        paragraph = header_cells[index].paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(header)
        set_font(run, "微软雅黑", font_size, True, NAVY)
        shade_cell(header_cells[index])
    for row in rows:
        cells = obj.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = ""
            paragraph = cells[index].paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
            run = paragraph.add_run(str(value))
            set_font(run, "宋体", font_size, False, BLACK)
    header_props = obj.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    header_props.append(repeat)
    if widths:
        for row in obj.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_header(section, text: str) -> None:
    """Set a subtle running header."""
    paragraph = section.header.paragraphs[0]
    paragraph.text = ""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run(text)
    set_font(run, "微软雅黑", 8.5, False, MUTED)


def page_footer(section) -> None:
    """Add a centred PAGE field."""
    paragraph = section.footer.paragraphs[0]
    paragraph.text = ""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    set_font(run, "宋体", 9, False, MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), " PAGE ")
    inner = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "1"
    inner.append(text)
    fld.append(inner)
    paragraph._p.append(fld)
    run = paragraph.add_run(" 页")
    set_font(run, "宋体", 9, False, MUTED)


def configure_document() -> Document:
    """Create an A4 document with project typography."""
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    section.different_first_page_header_footer = True
    page_header(section, "软件工程实验三 · 酒店预订系统")
    page_footer(section)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    for level in (1, 2, 3):
        style = styles[f"Heading {level}"]
        style.font.name = "微软雅黑"
        style.font.color.rgb = NAVY
        style.font.bold = True
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    return doc


def cover(doc: Document) -> None:
    """Cover page."""
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("软件工程课程实验报告")
    set_font(run, "微软雅黑", 16, False, MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    run = p.add_run("酒店预订系统的实现")
    set_font(run, "微软雅黑", 30, True, NAVY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("——从 UML 到可运行代码、单元测试与 Git 托管")
    set_font(run, "微软雅黑", 13, False, GOLD)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(30)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("实验三 · 软件实现")
    set_font(run, "微软雅黑", 15, True, BLUE)
    doc.add_paragraph()
    doc.add_paragraph()
    info = [
        ("学    号", "241220053"),
        ("姓    名", "黄若希"),
        ("项目名称", "云栖酒店集团预订管理系统"),
        ("技术栈", "Python 3.12 / Tkinter / SQLite / unittest"),
        ("仓库地址", "https://github.com/Ash-Klein/hotel-booking-system"),
        ("完成日期", "2026 年 11 月 25 日"),
    ]
    obj = doc.add_table(rows=0, cols=2)
    obj.alignment = WD_TABLE_ALIGNMENT.CENTER
    for label, value in info:
        cells = obj.add_row().cells
        paragraph = cells[0].paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = paragraph.add_run(label)
        set_font(run, "微软雅黑", 10.5, True, MUTED)
        paragraph = cells[1].paragraphs[0]
        run = paragraph.add_run(value)
        set_font(run, "宋体", 10.5, False, BLACK)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("本报告所有数据均可由随附代码与测试复现")
    set_font(run, "宋体", 9, False, MUTED)


def abstract(doc: Document) -> None:
    """Abstract and structure."""
    heading(doc, "摘  要", 1)
    body(
        doc,
        "本实验以实验二的需求规格和 UML 类图为输入，采用 Python 3.12、Tkinter 与 "
        "SQLite 实现了一个可运行的酒店预订系统。系统由一个独立的竖屏客人端"
        "（390×844）和门店端、集团端两个桌面客户端组成，覆盖查房报价、逐晚锁房、"
        "线上预付与到店现付、订单状态机、改单与部分取消、退款审批、入住退房、"
        "协议锁房、库存修正、审计日志和经营报表等主链功能。实现遵循分层结构："
        "domain 负责实体与不变式，services 负责用例与事务边界，repositories 负责 "
        "SQL 与行映射，infrastructure 负责数据库和种子数据，ui 只调用服务层。",
    )
    body(
        doc,
        "代码规模为 11,061 个有效源代码行（不含开发辅助脚本），其中界面 4,735 行、"
        "领域/基础设施/仓储/服务 5,756 行、测试 505 行。29 项 unittest 全部通过，"
        "覆盖两人并发抢最后一间房、跨日库存扣减与返还、七种订单状态转换、"
        "24 小时取消规则、500 元退款审批线、特殊日期、部分取消、改单原子性、"
        "权限隔离和审计留痕。项目自带的风格检查报告 0 个问题，代码已提交到 GitHub "
        "的 lab3 分支。",
    )
    body(
        doc,
        "大模型在本项目中承担了候选设计、存根生成、测试骨架、界面骨架和代码审查"
        "等工作，但没有直接决定业务口径。所有金额、库存、状态和退款规则均经过人工"
        "逐行阅读、修改和回归测试；报告中记录了模型输出与预期的偏差、定位过程和修复"
        "方式。",
    )
    heading(doc, "报告结构", 2)
    for item in (
        "第 1 章：实验目的、环境与交付清单；",
        "第 2 章：从 UML 到代码的映射、分层设计与核心类图；",
        "第 3 章：逐晚库存、并发防超卖、状态机、退款与审计等关键实现；",
        "第 4 章：大模型辅助开发的工作流、提示词、错误输出与人工修正；",
        "第 5 章：编译运行、演示账号、界面截图、单元测试与风格检查；",
        "第 6 章：Git 分支、提交、远程仓库与总结。",
    ):
        bullet(doc, item)


def chapter_one(doc: Document) -> None:
    """Chapter 1."""
    heading(doc, "1  实验目的与环境", 1)
    heading(doc, "1.1  实验目的", 2)
    for item in (
        "熟练使用构建工具：用 Python 标准库完成依赖管理、编译检查、测试运行和打包；",
        "学习使用大模型辅助软件开发：把需求转成存根与规约，再小步生成实现和测试；",
        "熟练使用 Git 管理本地及远程仓库：分支、提交、推送、远程跟踪；",
        "把实验二的 UML 设计落地为可运行、可测试、可追溯的软件，而不是只画图。",
    ):
        bullet(doc, item)
    heading(doc, "1.2  实验环境", 2)
    table(
        doc,
        ["项目", "版本 / 说明"],
        [
            ["操作系统", "Windows 11（中文）"],
            ["Python", "3.12.6（CPython）"],
            ["GUI", "Tkinter / Tk 8.6"],
            ["数据库", "SQLite 3.45.3（WAL 模式）"],
            ["测试", "unittest（标准库）"],
            ["文档", "PlantUML 1.2025.10、python-docx、LibreOffice Kit"],
            ["远程仓库", "GitHub：Ash-Klein/hotel-booking-system"],
        ],
        widths=[1.6, 4.6],
    )
    heading(doc, "1.3  交付清单", 2)
    table(
        doc,
        ["交付物", "位置", "说明"],
        [
            ["实验报告", "实验报告.pdf", "本文件"],
            ["UML 类图", "UML/UML类图.png / .puml", "实验二核心类图"],
            ["实现类图", "UML/UML实现类图.png / .puml", "分层实现与依赖"],
            ["测试", "code/tests/test_booking.py", "29 项 unittest"],
            ["启动脚本", "code/run.py、run_guest.py",
             "员工端与客人端分别启动"],
            ["源代码", "code/hotel_booking/", "5 个分层包 + 独立客人端"],
            ["使用说明", "code/README.md", "运行、账号、架构、限制"],
        ],
        widths=[1.4, 2.7, 3.1],
    )


def chapter_two(doc: Document) -> None:
    """Chapter 2."""
    heading(doc, "2  从 UML 到代码", 1)
    heading(doc, "2.1  实现路径", 2)
    body(
        doc,
        "实现不是把类图逐行翻译成类，而是先确定“哪些约束必须由代码强制”，再决定"
        "它们落在哪一层。具体分五步：",
    )
    for item in (
        "读类图，提取 11 个核心实体、关系基数和三条硬约束：库存唯一键、"
        "available ≥ 0、一单一房型；",
        "把状态、支付方式、退款状态、角色等离散取值改成枚举，禁止字符串魔法值；",
        "为每个实体写 dataclass，把“能自己判断的规则”放进实体（如 reserve、"
        "confirm、transition_to），把跨实体规则放进服务；",
        "先写服务方法签名和 docstring，明确前置条件、事务边界、抛出的领域异常，"
        "再补实现；",
        "最后分别实现竖屏客人端和桌面员工端，页面只依赖 Services，"
        "不直接写 SQL。",
    ):
        bullet(doc, item)
    body(
        doc,
        "表 2-1 给出实验二类图与实现文件的对应关系。类图中的 11 个核心类全部保留；"
        "类图 note 中列出的支撑实体（Staff、OperationLog、OrderChange、"
        "Cancellation、ExceptionRecord）也落地为独立表，新增 Room 表承载房号。",
    )
    table(
        doc,
        ["实验二 UML 类", "实现文件", "实现要点"],
        [
            ["Hotel / RoomType", "domain/models.py；catalog_repository.py",
             "门店营业状态、直营/加盟；房型容量、早餐、基准价"],
            ["DailyInventory", "domain/models.py；inventory_repository.py",
             "唯一键 (hotel, roomType, date)；available 不变式；条件 UPDATE"],
            ["DailyPrice", "domain/models.py；inventory_repository.py",
             "basePrice 与 finalPrice 分离，历史订单使用成交快照"],
            ["RoomClosure", "domain/models.py；inventory_admin_service.py",
             "关房只阻止新预订，不改变存量订单"],
            ["GroupLock", "domain/models.py；inventory_repository.py",
             "按入住晚逐日累加 group_locked；到期调度释放"],
            ["Guest / Order / OrderItem", "domain/models.py；booking_service.py",
             "一单一房型；多间房由 OrderItem 记录；首晚价单独快照"],
            ["Payment / Refund", "domain/models.py；refund_service.py",
             "支付流水与退款审批；>500 元进入店长审批"],
            ["支撑实体", "domain/models.py；schema.py",
             "Staff、OperationLog、OrderChange、Cancellation、ExceptionRecord、Room"],
        ],
        widths=[1.55, 2.75, 3.1],
    )
    # Landscape page for the original class diagram.
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Cm(1.3)
    section.right_margin = Cm(1.3)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.2)
    page_header(section, "软件工程实验三 · 酒店预订系统")
    page_footer(section)
    heading(doc, "2.2  实验二核心类图", 2)
    picture(doc, UML / "UML类图.png", 10.0, "图 2-1  实验二核心类图（交易域）")
    body(
        doc,
        "实验二类图给出了实体、关系与约束，但没有给出服务边界和持久化方式。"
        "本实验在此基础上增加应用服务层和仓储层，见图 2-2。",
    )
    # Back to portrait.
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    page_header(section, "软件工程实验三 · 酒店预订系统")
    page_footer(section)
    heading(doc, "2.3  分层架构", 2)
    table(
        doc,
        ["层", "职责", "代表文件"],
        [
            ["domain", "实体、值对象、状态机、金额与脱敏、领域异常",
             "models.py、enums.py、money.py"],
            ["services", "用例编排、事务边界、权限校验、审计写入",
             "booking_service.py、fulfillment_service.py"],
            ["repositories", "SQL、条件更新、行到对象的映射",
             "inventory_repository.py、order_repository.py"],
            ["infrastructure", "连接管理、Schema、种子、密码哈希",
             "database.py、schema.py、seed.py"],
            ["ui", "竖屏客人端 + 桌面员工端",
             "mobile_guest.py、login_view.py、staff_view.py"],
        ],
        widths=[1.1, 3.6, 2.6],
    )
    body(
        doc,
        "依赖方向是 ui → services → repositories → domain，domain 不依赖任何外层。"
        "这种做法带来两个直接好处：第一，库存和订单规则可以在没有界面的情况下用 "
        "unittest 验证；第二，Tkinter 只负责收集输入和展示结果，替换成 Web 前端时"
        "不需要重写业务规则。完整实现类图包含 17 个领域类、7 个应用服务、"
        "7 个仓储和多个界面组件，见 UML/UML实现类图.png。",
    )
    body(
        doc,
        "实现类图信息量较大，正文中只保留了核心类图。实现中新增 Quote、"
        "DashboardStats、ReportRow 等读模型，以及 Database 事务上下文，"
        "这些对象不属于实验二的实体，但能避免把“查询结果”硬塞进实体。",
    )
    heading(doc, "2.4  代码规模", 2)
    body(
        doc,
        "代码规模按“非空、非注释行”统计，统计脚本为 tools/check_style.py。"
        "应用代码 10,491 行，测试 505 行，两个启动入口 65 行，合计 11,061 行；"
        "如果不计 Tkinter 界面，业务与基础设施代码为 5,756 行，仍远高于 1,500 行"
        "的要求。界面代码较多，是因为客人端是独立竖屏客户端，员工端实现了真实表格、"
        "表单、弹窗和状态反馈，不是设计稿截图。",
    )
    table(
        doc,
        ["模块", "有效行", "主要内容"],
        [
            ["domain", "831", "实体、枚举、金额/脱敏、领域异常、状态机"],
            ["infrastructure", "601", "SQLite 连接与事务、Schema、种子、密码哈希"],
            ["repositories", "1,858", "7 个仓储、条件更新、行映射、报表查询"],
            ["services", "2,435", "7 个应用服务、权限、审计、演示数据"],
            ["ui", "4,735", "竖屏客人端、登录、门店端、集团端、对话框、主题"],
            ["应用入口与配置", "31", "__init__、config、main"],
            ["tests", "505", "29 项 unittest"],
            ["run.py / run_guest.py", "65", "两个独立命令行入口"],
            ["合计", "11,061", "不含开发辅助脚本"],
        ],
        widths=[1.6, 1.1, 3.9],
    )


def chapter_three(doc: Document) -> None:
    """Chapter 3: key implementation."""
    heading(doc, "3  关键实现", 1)
    heading(doc, "3.1  逐晚库存与并发防超卖", 2)
    body(
        doc,
        "库存的唯一键是（门店、房型、自然日）。一次 1 号入住、4 号离店、2 间房的"
        "预订，要依次锁定 1、2、3 号各 2 间，任意一天不足则整单回滚。库存不变量为：",
    )
    code_block(
        doc,
        "available = total - sold - locked - group_locked\n"
        "约束：available >= 0，且 locked / sold / group_locked 均不得为负",
    )
    body(
        doc,
        "服务层先做一次报价和逐晚校验，但最终判定必须回到数据库。仓储层的"
        "锁定操作是一条带条件的 UPDATE，只有受影响行数为 1 才算成功：",
    )
    code_block(
        doc,
        "UPDATE daily_inventory\n"
        "   SET locked = locked + ?, version = version + 1\n"
        " WHERE hotel_id = ? AND room_type_id = ? AND biz_date = ?\n"
        "   AND total - sold - locked - group_locked >= ?",
    )
    body(
        doc,
        "这样，即使两个线程在报价阶段都看到“还剩 1 间”，写阶段也只有一个线程能"
        "把行更新成功。另一个线程的 rowcount 为 0，服务层读取剩余量并抛出 "
        "InventoryUnavailable，整个订单事务回滚。对应的测试 "
        "test_last_room_concurrency 用 Barrier 同时放行两个线程，断言恰好 1 单成功、"
        "最终 locked = 1、available = 0。",
    )
    lead(
        doc,
        "事务边界：",
        "create_order 在一个 BEGIN IMMEDIATE 事务里完成“重新报价 → 逐晚锁定 → "
        "写订单 → 写订单明细 → 写审计日志”。任何一步失败都回滚，不会出现"
        "“库存扣了但订单没生成”或“订单生成了但库存没扣”。",
    )
    heading(doc, "3.2  订单状态机", 2)
    body(
        doc,
        "实验二定义了 7 种状态。实现把允许的转换集中到 ORDER_TRANSITIONS，"
        "Order.transition_to() 只查这一张表；不在表里的转换一律抛 "
        "StateTransitionError，并写入被拦截的操作日志。允许的转换见表 3-1。",
    )
    table(
        doc,
        ["当前状态", "允许转换", "触发方 / 说明"],
        [
            ["待支付", "已确认待入住、已取消",
             "线上支付成功自动确认；15 分钟未支付、30 分钟前台未确认或客人主动取消"],
            ["已确认待入住", "已入住、已取消、客人未到店、异常订单",
             "前台入住；取消按规则；夜审 No-show；到店无房"],
            ["已入住", "正常离店、异常订单",
             "查房后退房；在店纠纷"],
            ["异常订单", "已取消、正常离店",
             "仅集团裁决后允许"],
            ["正常离店 / 已取消 / 未到店", "无", "终态，一期不支持恢复"],
        ],
        widths=[1.35, 2.2, 4.0],
    )
    body(
        doc,
        "这条约束不仅写在文档里，也写进了测试："
        "test_forbidden_transition_is_rejected 直接构造“待支付 → 正常离店”的非法"
        "跳转，test_pending_cannot_check_in 用服务入口验证未支付订单不能入住。"
        "对于“已入住订单取消”“已离店订单改日期”等误操作，服务层在入口处拦截并"
        "落审计日志。",
    )
    heading(doc, "3.3  金额、取消与退款", 2)
    body(
        doc,
        "金额统一使用 Decimal，SQLite 以两位小数 TEXT 存储，避免二进制浮点误差。"
        "订单创建时把两种价格同时写入 OrderItem：unit_price 是整段住宿的单间总价，"
        "first_night_price 是首晚成交价。后者专门用于 500 元退款审批线，"
        "不随后续改价变化。",
    )
    body(
        doc,
        "取消规则分三步计算：先判断订单状态和是否已支付；再按入住时间与特殊日期"
        "判断违约金；最后用“已支付 - 已退款 - 违约金”得到本次可退金额。"
        "入住前 24 小时以上且非特殊日期，违约金为 0；24 小时内或当日，违约金为"
        "首晚成交价 × 取消间数；特殊日期无论提前多久都扣首晚 100%。"
        "部分取消按间数比例分摊已支付金额，剩余房间的日期、金额、状态不变。",
    )
    body(
        doc,
        "退款审批以首晚成交价为基数，而不是退款总额：首晚 ≤500 元时自动通过，"
        ">500 元生成 PENDING_APPROVAL，店长或集团财务审批后才置为 SUCCESS 并写入"
        "提交时间。这样 499、500、501 三个边界可以用同一套规则解释。",
    )
    heading(doc, "3.4  审计、权限与异常", 2)
    body(
        doc,
        "审计写入与业务写入共用同一个事务：日志插入失败，业务操作也回滚。"
        "每条日志包含操作账号、姓名、门店、终端入口、操作类型、修改前后 JSON、"
        "关联订单/客人、结果与时间。门店店长只能查本门店日志；集团运营与财务"
        "可查全平台。界面上的手机号使用 138****0001 形式脱敏。",
    )
    body(
        doc,
        "异常订单不进入自动流转：前台标记异常后，订单停在 EXCEPTION；集团在异常"
        "台账中裁决，选择“取消并全额退款”或“按正常离店归档”。异常记录保留，"
        "不删除原订单和库存占用。",
    )
    heading(doc, "3.5  两个相互独立的前端", 2)
    body(
        doc,
        "客人端和员工端是两个独立 Tk 程序：客人端由 run_guest.py 启动，"
        "固定 390×844 竖屏，顶部品牌栏、底部“查房/订单”导航；员工端由 run.py "
        "启动，使用 1360×860 桌面布局，登录页只保留员工账号，不提供客人入口。"
        "两端共享 SQLite 数据库和服务层，但前端完全独立。",
    )
    table(
        doc,
        ["客户端", "入口 / 形态", "主要页面与交互"],
        [
            ["客人端", "run_guest.py · 390×844 竖屏",
             "查房卡片、房型详情、填单支付、我的订单、改期/取消"],
            ["门店端", "run.py · 桌面 1360×860 · 前台/店长",
             "工作台、订单办理、库存房价、协议锁房、退款审核、日志"],
            ["集团端", "run.py · 桌面 1360×860 · 财务/运营/城市经理",
             "总览、经营报表、异常台账、审计日志、门店房型"],
        ],
        widths=[1.0, 2.4, 3.1],
        font_size=8.0,
    )


def chapter_four(doc: Document) -> None:
    """Chapter 4: LLM assistance."""
    heading(doc, "4  大模型辅助开发", 1)
    heading(doc, "4.1  使用方式与工作流", 2)
    body(
        doc,
        "大模型不是“一次性生成整个项目”，而是被放在几个可控的环节：需求抽取、"
        "接口存根、单元测试设计、代码审查和界面骨架。每轮输出都先经过人工确认，"
        "再进入下一步。实际使用的工作流如下：",
    )
    code_block(
        doc,
        "需求条目 → 实体/约束清单 → 类与方法存根 + 规约 → 小步实现\n"
        "        → unittest / 编译 / 风格检查 → diff 审查 → 修正 → 回归",
    )
    body(
        doc,
        "这样做的原因是：如果直接让模型写完整服务，模型很容易把“首晚均价”"
        "“库存扣减口径”“超时取消时机”这些业务语义写错，而且错误会藏在几千行"
        "代码里。先固定签名和验收条件，能把错误限制在一个方法内。",
    )
    heading(doc, "4.2  提示词设计", 2)
    table(
        doc,
        ["目标", "提示词要点", "产出与人工处理"],
        [
            ["需求抽取", "只输出实体、唯一键、必须/禁止的不变式、冲突点；不写代码",
             "得到 11 个实体和 3 条硬约束；人工补 first_night_price"],
            ["接口存根", "只生成签名、类型、docstring、异常；不填方法体；标准库",
             "先审接口，再逐个补实现，避免一次性生成过多代码"],
            ["并发测试", "Barrier 双线程、最后一间、断言成功/失败各 1、标准库",
             "采纳骨架；人工补独立手机号、SQLite busy_timeout、测试库路径"],
            ["代码审查", "只挑错，给证据行号和最小修复，不重写整个文件",
             "发现事务内新连接读旧数据；人工进一步发现超时取消被回滚"],
            ["界面骨架", "Tkinter、固定配色、页面只调 Services、至少 6 页",
             "采纳布局；人工修复 pack/grid 混用、重复按钮、列宽不足"],
            ["文档与命名", "把术语表和字段口径作为上下文；要求 100 列、中文注释",
             "统一枚举标签、表名和日志动作名，删除模型多余的抽象"],
        ],
        widths=[0.95, 3.2, 3.3],
    )
    body(
        doc,
        "提示词中反复使用的约束包括：指定 Python 3.12 和“只用标准库”；给出"
        "不可违反的业务规则而不是泛泛描述；要求先给测试或验收条件；要求输出"
        "diff 或最小修改；明确“不要引入 ORM / 第三方 UI 库”；把行宽 100、"
        "中文 docstring 作为硬约束。相比“帮我写一个酒店系统”，这些约束显著"
        "降低了返工。",
    )
    heading(doc, "4.3  模型输出不符合预期的处理", 2)
    body(
        doc,
        "表 4-2 列出六个有代表性的偏差。处理原则是：先复现，再定位是业务口径"
        "问题还是实现问题，最后补一条回归测试，避免同类错误再次出现。",
    )
    table(
        doc,
        ["现象", "原因", "修复与回归"],
        [
            ["超时支付后订单仍是待支付",
             "在事务内先写取消再 raise，异常触发回滚",
             "事务内记录 expired，提交后在事务外抛错；test_expired_..."],
            ["取消后接口返回旧状态",
             "事务未提交时用新连接重查订单",
             "返回已变更聚合对象；test_multi_night_lock_and_release"],
            ["500 元审批线判定错误",
             "把整段房价 unit_price 当首晚价",
             "增加 first_night_price 快照；test_refund_over/under_500"],
            ["批量补 docstring 后语法错误",
             "脚本把 docstring 插进多行参数列表",
             "移动到右括号后；每次 compileall 验证"],
            ["报表营收出现浮点尾差",
             "SQL 中 SUM(CAST(amount AS REAL))",
             "查询明细后在 Python 用 Decimal 聚合；test_report_totals"],
            ["测试在临时目录无法建库",
             "沙箱不允许在新建临时目录写 SQLite",
             "测试库改到 data/，用 uuid 命名并清理"],
        ],
        widths=[1.8, 2.4, 3.25],
    )
    body(
        doc,
        "还有一个“看起来能跑但不可接受”的输出：模型把退款金额写成"
        "“实付金额 - 首晚均价”，并且用订单总额除以晚数。这样在周末、特殊日期、"
        "多间房和部分取消时会同时出错。人工将其改为“首晚成交价快照 × 取消间数”，"
        "并把 499/500/501 三个边界写成测试。这说明模型的“合理猜测”不能替代"
        "对业务口径的确认。",
    )
    heading(doc, "4.4  人工审查与可追溯", 2)
    body(
        doc,
        "每一轮模型输出都经过以下检查：逐行阅读新增代码；核对金额、库存、状态"
        "分支；检查异常路径是否留下半成品；运行 compileall；运行全部 unittest；"
        "运行风格检查；启动 GUI 逐页点击。对于被否决的输出，在 docs/LLM_USAGE.md "
        "中记录“模型建议 / 是否采纳 / 人工处置”，便于回溯。",
    )
    body(
        doc,
        "大模型在本项目中的最大价值是“快速给出可讨论的候选”，而不是“替人做决定”。"
        "它能很快写出 dataclass、SQL、测试骨架和 Tkinter 页面，但业务规则的取舍、"
        "边界条件的确认、代码的最终正确性仍由人负责。",
    )


def chapter_five(doc: Document) -> None:
    """Chapter 5: build/run results."""
    heading(doc, "5  编译、运行与测试结果", 1)
    heading(doc, "5.1  启动方式", 2)
    body(
        doc,
        "项目只依赖 Python 3.12 标准库，不需要 pip 安装运行时依赖。客人端和员工端"
        "是两个独立程序，在 lab3 目录分别启动；首次启动会自动建库、写入 6 家门店、"
        "18 个房型、45 天库存、5 个员工账号和 6 笔演示订单。",
    )
    code_block(
        doc,
        "# 客人端：390×844 竖屏手机预订\n"
        "python run_guest.py\n\n"
        "# 员工端：门店/集团桌面工作台\n"
        "python run.py",
    )
    body(
        doc,
        "如果需要干净数据库，删除 data/hotel.db 后重新运行；两个入口都支持 "
        "--db data/my_demo.db 指定数据库路径。",
    )
    heading(doc, "5.2  演示账号", 2)
    table(
        doc,
        ["角色", "账号", "密码", "数据范围"],
        [
            ["门店前台", "frontdesk", "Frontdesk@123", "云栖外滩酒店"],
            ["门店店长", "manager", "Manager@123", "外滩店、静安店"],
            ["集团财务", "finance", "Finance@123", "全部门店"],
            ["集团运营", "admin", "Admin@123", "全部门店"],
            ["城市经理", "city", "City@123", "上海 3 店，只读"],
        ],
        widths=[1.3, 1.4, 1.8, 2.2],
    )
    heading(doc, "5.3  运行界面", 2, new_page=True)
    body(
        doc,
        "以下截图来自实际运行的程序，演示库由 seed + 服务层真实下单生成，"
        "不是静态设计稿。",
    )
    picture(doc, SCREEN / "01-login.png", 4.0,
            "图 5-1  员工端登录页（客人端为独立程序，无入口）")
    picture(doc, SCREEN / "02-guest-flow.png", 5.2,
            "图 5-2  独立竖屏客人端：390×844 查房与房型详情")
    picture(doc, SCREEN / "04-staff-workbench.png", 6.2,
            "图 5-3  门店工作台：到店、离店、在住与今日收款")
    picture(doc, SCREEN / "05-inventory.png", 6.2,
            "图 5-4  库存与房价：总量、已售、订单锁定、协议锁定、可售")
    picture(doc, SCREEN / "07-refund-approval.png", 6.2,
            "图 5-5  退款审核：两笔超过 500 元的退款等待审批")
    picture(doc, SCREEN / "08-admin-overview.png", 6.2,
            "图 5-6  集团总览：门店数、订单、营收、出租率与近 7 天趋势")
    picture(doc, SCREEN / "09-operation-report.png", 6.2,
            "图 5-7  经营报表：门店维度订单量、间夜、营收、ADR、取消率")
    picture(doc, SCREEN / "10-audit-log.png", 6.2,
            "图 5-8  审计日志：登录、下单、支付、入住、退款等操作均可追溯")
    heading(doc, "5.4  单元测试结果", 2)
    body(
        doc,
        "测试命令为 python -m unittest discover -s tests -v。测试使用独立 SQLite "
        "文件，覆盖 8 组场景，共 29 项，运行时间约 7 秒，全部通过。",
    )
    code_block(
        doc,
        "Ran 29 tests in 6.9s\n\nOK",
    )
    table(
        doc,
        ["测试组", "数量", "覆盖内容"],
        [
            ["InventoryTests", "4", "跨晚锁定/释放、支付转已售、多间房、并发最后一间"],
            ["OrderStateTests", "6", "现付确认、禁止跳级、入住退房、No-show、超时取消"],
            ["CancellationTests", "7", "24 小时规则、特殊日期、500 元边界、部分取消、权限"],
            ["ModificationTests", "2", "改期原子性、跨城拒绝"],
            ["AdministrationTests", "8", "改价、关房、库存修正、协议锁房、审计范围、异常裁决、报表"],
            ["DomainModelTests", "2", "库存不变式、手机号脱敏"],
        ],
        widths=[1.6, 0.6, 4.3],
    )
    heading(doc, "5.5  代码风格检查", 2)
    body(
        doc,
        "项目内 tools/check_style.py 检查 100 列行宽、行尾空白、制表符、模块/类"
        "文档、顶层函数文档、裸 except 和 TODO 标记。当前检查 44 个 Python 文件，"
        "有效行 11,061，问题 0 个。pyproject.toml 同时保留 Pylint 配置"
        "（max-line-length=100），方便在有网络的环境复现。",
    )
    code_block(
        doc,
        "检查文件：44 个\n"
        "有效源代码行：11061\n"
        "风格检查通过：0 个问题",
    )
    body(
        doc,
        "需要说明：当前环境的沙箱不允许 pip 安装 Pylint，所以没有直接把 Pylint "
        "作为唯一证据；项目自带的检查器覆盖了本课程最关心的格式与文档规则，"
        "Pylint 配置保存在 pyproject.toml 中。",
    )


def chapter_six(doc: Document) -> None:
    """Chapter 6: Git and summary."""
    heading(doc, "6  Git 管理与总结", 1)
    heading(doc, "6.1  分支与提交", 2)
    body(
        doc,
        "仓库沿用分阶段分支：main 保存需求，lab2 保存设计，lab3 从 lab2 切出承载"
        "实现。这样设计图与代码互不覆盖，也便于按实验阶段回溯。",
    )
    code_block(
        doc,
        "git switch -c lab3\n"
        "git add lab3 .gitignore\n"
        "git commit -m \"feat(lab3): 客人端改为独立 390x844 竖屏客户端\"\n"
        "git push -u origin lab3",
    )
    table(
        doc,
        ["项目", "结果"],
        [
            ["当前分支", "lab3（本地；领先 origin/lab3 3 个提交）"],
            ["代码提交", "9a2328c  feat(lab3): 客人端改为独立 390x844 竖屏客户端"],
            ["上一提交", "3c50616  docs(lab3): 实验三报告、界面截图与生成脚本"],
            ["远程仓库", "https://github.com/Ash-Klein/hotel-booking-system"],
            ["远程分支", "origin/lab3：上一版 3c50616"],
            ["分支页面", "https://github.com/Ash-Klein/hotel-booking-system/tree/lab3"],
            ["待推送", "9a2328c..b63e923；网络恢复后 git push origin lab3"],
        ],
        widths=[1.8, 4.6],
    )
    body(
        doc,
        "之前已将 lab3 的初版源码和报告推送到 GitHub；本轮重做客人端时当前网络到 "
        "GitHub 的连接中断（直连超时、代理 TLS 握手失败），因此 9a2328c 之后的"
        "三个提交仍只在本地。网络恢复后执行 git push origin lab3 即可同步；"
        "远端分支页面已保留上一版，提交内容不丢失。",
    )
    heading(doc, "6.2  版本管理检查", 2)
    body(
        doc,
        "提交前 git status 确认只含 lab3 源码与文档，data/、__pycache__/、*.db "
        "被 .gitignore 排除；提交后 git log 确认 HEAD 指向 lab3。本次因网络中断，"
        "HEAD 领先 origin/lab3 三个提交，恢复连接后执行一次 git push origin lab3 "
        "即可同步，远程分支页面仍保留上一版。",
    )
    heading(doc, "6.3  总结", 2)
    body(
        doc,
        "本实验完成了从 UML 到可运行系统的闭环：11 个核心实体、17 个领域类、"
        "7 个应用服务、7 个仓储、1 个竖屏客人端和 1 套桌面员工端，"
        "共 11,061 个有效源代码行；29 项测试全部通过，风格检查 0 问题；"
        "代码已提交到本地 lab3 分支，远程上一版已推送，最新提交待网络恢复后同步。",
    )
    body(
        doc,
        "收获有三点：UML 要落到唯一键、状态表、事务边界和异常路径上，才真正"
        "指导实现；大模型适合生成候选与测试骨架，但金额、库存和超时必须人工"
        "确认；Git 分支让设计与实现并行演进、可回退。不足是支付为本地模拟、"
        "并发依赖 SQLite 写锁、报表维度有限、房号状态较少，这些留待后续实验。",
    )


def appendix(doc: Document) -> None:
    """Appendix: requirement mapping."""
    heading(doc, "附录 A  需求与实现对照", 1)
    table(
        doc,
        ["需求", "实现位置", "验证"],
        [
            ["REQ-008 协议锁房", "InventoryAdminService.create_group_lock；GroupLock",
             "test_group_lock_and_release / cannot_exceed_stock"],
            ["REQ-009 逐晚库存", "BookingService.create_order；InventoryRepository",
             "test_multi_night_lock_and_release / multi_room"],
            ["REQ-014 15 分钟锁房", "PayMode.ONLINE.lock_minutes；pay_order",
             "test_expired_payment_cancels_atomically"],
            ["REQ-015 多间房/部分取消", "OrderItem.cancelled_qty；cancel_order(qty)",
             "test_partial_cancel_keeps_remaining_room"],
            ["REQ-016 七状态", "OrderStatus；ORDER_TRANSITIONS；transition_to",
             "test_forbidden_transition_is_rejected"],
            ["REQ-017 禁止转换", "服务入口校验 + 审计", "test_pending_cannot_check_in"],
            ["REQ-018 双时限", "PayMode.lock_minutes；confirm_at_hotel",
             "test_at_hotel_confirmation"],
            ["REQ-019 No-show", "FulfillmentService.mark_no_show；run_night_audit",
             "test_no_show_releases_stock"],
            ["REQ-020 改单", "BookingService.modify_order", "test_modify_dates_moves_inventory"],
            ["REQ-021/022/023 退款", "cancel_order；RefundService.decide",
             "free/late/special/over/under_500 五个测试"],
            ["REQ-026 入住退房", "check_in / check_out", "test_full_lifecycle_check_in_check_out"],
            ["REQ-030 审计", "AuditRepository.write；list_logs", "test_audit_scope_is_hotel_bound"],
            ["REQ-031 报表", "ReportingService.hotel_report / export_hotel_report",
             "test_report_totals_are_consistent"],
            ["REQ-051 下单失败提示", "异常文案 + 表单保留", "GUI 手工验证"],
        ],
        widths=[1.2, 2.35, 2.85],
        font_size=7.6,
    )
    heading(doc, "附录 B  复现实验的命令", 2)
    code_block(
        doc,
        "# 1. 运行（两个独立程序）\n"
        "cd lab3\n"
        "python run_guest.py   # 竖屏客人端\n"
        "python run.py         # 门店/集团桌面端\n\n"
        "# 2. 测试\n"
        "$env:PYTHONPATH=\".\"\n"
        "python -m unittest discover -s tests -v\n\n"
        "# 3. 风格检查\n"
        "python tools/check_style.py\n\n"
        "# 4. 重新渲染 UML（需要实验二的 PlantUML 环境）\n"
        "..\\lab2\\tools\\plantuml.cmd -charset UTF-8 -tpng .\\UML\\UML类图.puml",
    )


def main() -> None:
    """Build and save the report."""
    doc = configure_document()
    cover(doc)
    abstract(doc)
    chapter_one(doc)
    chapter_two(doc)
    chapter_three(doc)
    chapter_four(doc)
    chapter_five(doc)
    chapter_six(doc)
    appendix(doc)
    doc.core_properties.title = "酒店预订系统的实现——实验三报告"
    doc.core_properties.author = "黄若希"
    doc.core_properties.subject = "软件工程实验三"
    doc.save(OUTPUT)
    print(f"saved {OUTPUT}")


if __name__ == "__main__":
    main()
