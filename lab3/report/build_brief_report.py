"""Generate the short experiment-three report.

The report is intentionally plain: black text, 宋体 body, 黑体 headings,
Table Grid tables, no colours or cover graphics.

Usage:
    python report/build_brief_report.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "report" / "screenshots"
UML = ROOT / "UML"
OUTPUT = ROOT / "report" / "实验3_简要报告.docx"

BODY_FONT = "宋体"
HEAD_FONT = "黑体"
CODE_FONT = "Consolas"


def set_run_font(run, latin: str, east: str, size: float, bold: bool = False) -> None:
    """Set latin and East Asian fonts on one run."""
    run.font.name = latin
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), east)


def add_body(doc, text: str, *, size: float = 10.5, bold: bool = False):
    """Add one normal paragraph."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = 1.35
    set_run_font(paragraph.add_run(text), BODY_FONT, BODY_FONT, size, bold)
    return paragraph


def add_heading(doc, text: str, level: int = 1) -> None:
    """Add a black 黑体 heading."""
    paragraph = doc.add_heading(level=level)
    paragraph.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    paragraph.paragraph_format.space_after = Pt(4)
    set_run_font(paragraph.add_run(text), HEAD_FONT, HEAD_FONT, 14 if level == 1 else 12, True)


def add_bullets(doc, items: list[str]) -> None:
    """Add a compact bullet list."""
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.3
        set_run_font(paragraph.add_run(item), BODY_FONT, BODY_FONT, 10.5)


def add_code(doc, text: str) -> None:
    """Add a plain monospace block, one paragraph per line."""
    for line in text.splitlines():
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.left_indent = Cm(0.5)
        set_run_font(paragraph.add_run(line if line else " "), CODE_FONT, BODY_FONT, 8.5)


def add_table(doc, headers: list[str], rows: list[list[str]], widths: list[float]):
    """Add a simple grid table with a bold header row."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, head in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.width = Cm(widths[index])
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        set_run_font(paragraph.add_run(head), BODY_FONT, BODY_FONT, 9, True)
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].width = Cm(widths[index])
            cells[index].text = ""
            paragraph = cells[index].paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.15
            set_run_font(paragraph.add_run(value), BODY_FONT, BODY_FONT, 9)
    for row in table.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_picture(doc, path: Path, width_cm: float, caption: str) -> None:
    """Insert a centred picture with a small caption kept on the same page."""
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(path), width=Cm(width_cm))
    caption_paragraph = doc.add_paragraph()
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_paragraph.paragraph_format.space_after = Pt(8)
    set_run_font(caption_paragraph.add_run(caption), BODY_FONT, BODY_FONT, 9)


def build() -> Document:
    """Build the whole document in memory."""
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.3)
    section.bottom_margin = Cm(2.3)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), BODY_FONT)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(2)
    set_run_font(title.add_run("实验三 简要报告"), HEAD_FONT, HEAD_FONT, 20, True)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(8)
    set_run_font(
        subtitle.add_run("从 UML 设计到可运行代码：实现过程、源代码规模、大模型辅助与 Git 管理"),
        BODY_FONT, BODY_FONT, 10.5,
    )
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.paragraph_format.space_after = Pt(10)
    set_run_font(
        info.add_run("学号：241220053    姓名：黄若希    完成日期：2026-11-25"),
        BODY_FONT, BODY_FONT, 10,
    )

    # 1
    add_heading(doc, "一、实现概述")
    add_body(
        doc,
        "本次实验把实验二的 UML 设计实现为可运行系统：客人端是 390×844 竖屏 Tk 程序，"
        "员工端（门店 + 集团）是 1360×860 桌面 Tk 程序，两个程序独立启动、共享同一个 "
        "SQLite 数据库和服务层。客人端覆盖“选店—选房型—房型详情—填单锁房—支付—订单改退”"
        "六屏主流程，员工端覆盖工作台、订单入住、库存房价、退款审批、报表和权限审计。",
    )
    add_body(doc, "代码按实验二组件图分层，目录结构如下：")
    add_code(
        doc,
        """lab3/
├── run_guest.py              客人端入口（390×844）
├── run.py                    员工端入口（1360×860）
├── hotel_booking/
│   ├── domain/               实体、枚举、金额、领域异常
│   ├── infrastructure/       数据库、建表、种子数据、密码散列
│   ├── repositories/         SQL 持久化与行到对象的映射
│   ├── services/             认证、查询报价、预订、履约、库存、退款、报表
│   └── ui/                   客人端 6 屏 + 门店端 + 集团端 + 登录
├── tests/test_booking.py     32 项单元测试
├── tools/                    代码风格检查、界面截图脚本
├── UML/UML实现类图.puml      实验三实现类图
└── report/                   报告、截图与生成脚本""",
    )
    add_body(
        doc,
        "依赖方向是单向的：ui 只调用 services，services 只调用 repositories，"
        "domain 不引用任何 UI 或 SQL。数据库为单文件 SQLite，开启 WAL、外键和 "
        "BEGIN IMMEDIATE 事务。",
    )

    # 2
    add_heading(doc, "二、如何把 UML 图转换为代码")
    add_body(doc, "转换按“类图定结构、状态图定规则、时序图定事务、组件图定分层”的顺序进行：")
    add_bullets(
        doc,
        [
            "类图 → 领域模型：每个类写成一个 dataclass(slots=True)，类属性对应字段，"
            "类方法写成领域方法（如 DailyInventory.reserve/release/confirm、Order.confirm/cancel）。",
            "状态图 → 状态机：7 个订单状态写成 OrderStatus 枚举，允许的跳转集中在 "
            "ORDER_TRANSITIONS 白名单，transition_to() 拒绝非法跳转并抛 StateTransitionError。",
            "时序图 / 活动图 → 事务与分支：一个用例对应一个服务方法，方法体内一个事务；"
            "失败分支对应 ValidationError、ConflictError、PermissionDenied 等异常。",
            "组件图 / 部署图 → 分层与部署：domain、infrastructure、repositories、services、ui "
            "五个包，两个独立入口共用 data/hotel.db。",
            "用例图 → 角色与权限：六类角色在 Role 枚举中定义，AuthService 与 permissions.py "
            "按角色和门店范围校验。",
        ],
    )
    add_body(doc, "主要的 UML 元素与代码位置对应如下：")
    add_table(
        doc,
        ["UML 元素", "代码位置", "落地方式"],
        [
            ["类图：Hotel、RoomType、DailyInventory", "domain/models.py",
             "dataclass；available = total - sold - locked - group_locked"],
            ["类图：Order、OrderItem、Payment、Refund", "domain/models.py、order_repository.py",
             "订单聚合根 + 子表；金额 Decimal，库里存两位小数 TEXT"],
            ["状态图：订单 7 状态", "domain/enums.py",
             "ORDER_TRANSITIONS 白名单；非法转换抛异常并留痕"],
            ["时序图：创建订单", "booking_service.py 的 create_order()",
             "一个事务内重新报价→逐晚条件锁房→写订单→写审计"],
            ["时序图：支付与超时", "pay_order、cancel_expired",
             "预付 15 分钟、现付 30 分钟；先提交事务，再在事务外抛业务异常"],
            ["活动图：取消与退款分支", "cancel_order、refund_service.py",
             "普通/部分/特殊日期取消；超过 500 元进入店长审批"],
            ["组件图：分层", "hotel_booking/ 五个包", "ui → services → repositories → domain/infrastructure"],
            ["部署图：单机部署", "data/hotel.db、run.py、run_guest.py",
             "SQLite 单文件，无服务端；两个 Tk 进程共享数据库"],
            ["用例图：六类角色", "auth_service.py、permissions.py",
             "角色 + 门店范围校验；城市经理只读"],
        ],
        widths=[4.4, 5.3, 6.3],
    )
    add_body(
        doc,
        "完整实现类图见 lab3/UML/UML实现类图.puml 与同名 PNG；报告只列 UML 元素到代码的映射关系，"
        "避免缩略后的类图不可读。",
    )
    add_body(
        doc,
        "状态机的写法是关键：所有状态转换集中在 ORDER_TRANSITIONS 一张表里，"
        "服务层不写 if/else 判断状态，而是调用 order.transition_to(target)。"
        "当前允许的转换是：待支付→已确认待入住/已取消；已确认待入住→已入住/已取消/"
        "客人未到店/异常订单；已入住→正常离店/异常订单；异常订单→已取消/正常离店。"
        "其余组合一律拒绝，并写入操作日志。",
    )
    add_body(
        doc,
        "库存与资金的安全由数据库层兜底：锁房使用条件 UPDATE，只有 "
        "total - sold - locked - group_locked >= qty 时才更新成功，"
        "因此两个人同时抢最后一间时只会有一单成功；下单、支付、取消、改单都在 "
        "BEGIN IMMEDIATE 事务中完成，任何异常整体回滚。",
    )

    # 3
    add_heading(doc, "三、软件源代码规模")
    add_body(
        doc,
        "按非空、非注释行统计，交付代码（不含实验二设计脚本与第三方库）规模如下：",
    )
    add_table(
        doc,
        ["分层 / 目录", "文件数", "有效行"],
        [
            ["domain 领域层", "5", "851"],
            ["infrastructure 基础设施", "5", "687"],
            ["repositories 仓储", "8", "1,895"],
            ["services 应用服务", "11", "2,458"],
            ["ui 表现层（客人端 + 员工端）", "11", "6,032"],
            ["tests 单元测试", "1", "547"],
            ["入口与根模块", "5", "96"],
            ["tools 开发脚本", "2", "231"],
            ["合计", "48", "12,797"],
        ],
        widths=[7.0, 3.0, 3.0],
    )
    add_body(
        doc,
        "项目自带检查脚本的统计口径（不含 tools、含测试）为 46 个 Python 文件、"
        "12,566 行有效代码；含 tools 共 12,797 行。界面层约 6,032 行，其中客人端 "
        "mobile_guest.py、guest_canvas.py、guest_theme.py 合计 2,425 行，"
        "单文件最大的是 mobile_guest.py（1,678 行）。单元测试 32 项，覆盖库存并发、"
        "状态机、取消退款、改单、履约、权限、审计与报表。",
    )

    # 4
    add_heading(doc, "四、大模型辅助代码实现的方式")
    add_body(
        doc,
        "使用 DeepSeek Harness 中的 DeepSeek-V4-Flash，时间集中在 2026-11-25。"
        "基本定位是：模型负责给出候选实现、测试和文案，人负责读每一行、跑检查、"
        "决定业务口径。工作流如下：",
    )
    add_code(
        doc,
        """需求条目（REQ-xxx）
  → 提取实体、状态、约束
UML 类图 / 状态图
  → 先让模型写“接口存根 + 规约”，不直接写完整实现
人工确认签名与验收条件
  → 小步生成实现
每步运行 compileall / unittest / check_style
  → 人工审查 diff
发现错误后把现象与期望反馈给模型
  → 修正并补回归测试""",
    )
    add_body(doc, "几条实际使用的提示词策略：")
    add_bullets(
        doc,
        [
            "限定范围：只做“列实体、列不变式、指出冲突”，明确禁止写代码、禁止补充需求里没有的业务。",
            "先存根后实现：要求只生成类与方法存根、类型标注和 docstring，先审查接口职责，再逐个补方法体。",
            "让模型写测试：例如“两个客人同时抢最后一间房”的线程 + Barrier 测试；"
            "人工再补独立手机号、异常捕获范围、SQLite busy_timeout 等细节。",
            "让模型挑错而不是重写：审查 cancel_order 时只要求输出问题、证据行号和最小修复建议，"
            "避免整段重写掩盖真正的缺陷。",
        ],
    )
    add_body(
        doc,
        "本次客人端按设计稿重做时，模型读取了实验二的界面源码与截图，先生成设计 token "
        "（颜色、字号、间距）和 Canvas 绘制组件，再逐屏重写页面；每轮都用实机截图与设计稿并排比对，"
        "由人指出坐标偏差、遮挡和交互问题后再改。",
    )

    # 5
    add_heading(doc, "五、大模型具体承担的工作")
    add_bullets(
        doc,
        [
            "领域模型与建表 SQL 初稿：实体字段、外键、CHECK 约束、库存不变式。",
            "仓储层 SQL 与事务封装：条件 UPDATE 防超卖、WAL、BEGIN IMMEDIATE、行到对象映射。",
            "服务层用例：下单、支付、超时取消、部分取消、改单、退款审批、报表聚合。",
            "单元测试骨架：并发抢房、超时支付、部分取消、特殊日期、退款审批线。",
            "Tkinter 界面：客人端 6 屏与 Canvas 组件、员工端工作台/库存/退款/报表页面。",
            "文档与工程材料：README、UML 文本、报告初稿、Git 提交信息。",
            "代码审查：按“挑错”提示词找事务、退款金额、状态转换方面的问题。",
        ],
    )
    add_body(doc, "模型输出并不是全部采纳，典型取舍如下：")
    add_table(
        doc,
        ["模型输出", "处理", "人工修改"],
        [
            ["SQLite 单文件保存数据", "采纳", "补 WAL、外键、条件 UPDATE、事务封装"],
            ["status 用字符串", "否决", "改为 OrderStatus 枚举 + 白名单转换表"],
            ["金额用 float", "否决", "改为 Decimal，SQLite 存两位小数 TEXT"],
            ["退款 = 实付 - 首晚均价", "否决", "改为首晚成交价快照，并区分部分取消"],
            ["取消时先 raise 再释放库存", "否决", "先完成释放/取消/审计事务，事务外再抛异常"],
            ["线程测试共享一个连接", "否决", "每个操作独立连接，事务内 BEGIN IMMEDIATE"],
            ["页面直接拼 SQL", "否决", "页面只调用 services / 仓储的只读查询"],
        ],
        widths=[4.6, 2.0, 9.4],
    )

    # 6
    add_heading(doc, "六、生成内容不符合预期时的处理")
    add_body(
        doc,
        "处理步骤固定为：复现问题 → 缩到最小用例 → 把“现象 + 期望 + 反例”反馈给模型 → "
        "只让它改一处或给建议 → 人工改代码 → 跑编译、测试、风格检查 → 把缺陷写进文档。"
        "几个真实例子：",
    )
    add_table(
        doc,
        ["缺陷", "现象", "处理"],
        [
            ["D-01 超时取消被回滚",
             "pay_order 在超时分支释放库存后 raise，异常导致事务回滚，订单仍是待支付",
             "事务内标记 expired，提交后再在事务外抛业务异常"],
            ["D-02 取消后返回旧状态",
             "事务内用新连接重查订单，读到未提交的旧数据",
             "返回已变更的订单聚合对象，提交后由上层刷新"],
            ["D-03 首晚房价口径错误",
             "把整段住宿的单间总价当首晚价，500 元审批线判错",
             "OrderItem 增加 first_night_price 快照，退款只用该字段"],
            ["D-04 批量插 docstring 破坏签名",
             "docstring 插到 def 与参数之间，出现语法错误",
             "改为插在右括号与返回类型之后，每次 compileall 验证"],
            ["D-05 报表浮点误差",
             "SQL 里 SUM(CAST(amount AS REAL)) 导致金额尾差",
             "查询明细后在 Python 用 Decimal 聚合"],
            ["D-06 环境限制",
             "临时目录不可写、无法 pip 安装 pylint",
             "测试库放 lab3/data；自写 tools/check_style.py 做风格检查"],
        ],
        widths=[3.2, 6.4, 6.4],
    )
    add_body(
        doc,
        "以上缺陷都补了回归测试：test_expired_payment_cancels_atomically（超时取消）、"
        "test_partial_cancel_keeps_remaining_room（部分取消）、"
        "test_refund_over_500_needs_approval（退款审批）、"
        "test_report_totals_are_consistent（报表金额）。",
    )
    add_body(
        doc,
        "本轮客人端改版也有一个典型例子：第一版弹层为了做“变暗”效果，在整屏画布上铺了深色网点遮罩，"
        "结果把原页面完全盖住，看起来像跳到了另一个奇怪页面。原因是 Tk 画布没有透明度。"
        "改为只在底部升起面板、原页面保持可见后，问题消失；这说明界面类问题必须靠截图复核，不能只看代码。",
    )

    # 7
    add_heading(doc, "七、代码的编译与运行结果")
    add_body(
        doc,
        "运行环境：Windows 11，Python 3.12.6，Tk 8.6，SQLite 为 Python 标准库；"
        "运行时不依赖任何第三方包。",
    )
    add_body(doc, "（1）编译检查：")
    add_code(doc, "> python -m compileall -q hotel_booking tests run.py run_guest.py\nCOMPILE_OK（退出码 0）")
    add_body(doc, "（2）单元测试：")
    add_code(doc, "> python -m unittest discover -s tests\n................................................\nRan 32 tests in 7.006s\nOK")
    add_body(doc, "（3）代码风格与规模：")
    add_code(
        doc,
        """> python tools/check_style.py
检查文件：46 个
有效源代码行：12566
风格检查通过：0 个问题（行宽 ≤100、无行尾空白、无制表符、文档完整）""",
    )
    add_body(doc, "（4）运行：")
    add_code(
        doc,
        """cd lab3
python run_guest.py        # 客人端：390×844 竖屏
python run.py              # 员工端：1360×860 桌面工作台""",
    )
    add_body(
        doc,
        "首次运行自动创建 data/hotel.db，写入 6 家门店、18 个房型、45 天库存与价格、"
        "5 个员工账号和 6 笔演示订单。两个程序共用同一数据库，但窗口、入口、导航完全独立；"
        "旧版本数据库启动时会自动补列并回填主数据，无需删库。运行结果如下：",
    )
    add_picture(
        doc,
        SHOTS / "11-clients-overview.png",
        15.5,
        "图 1  客人端（左，390×844）与门店端今日工作台（右，1360×860）",
    )

    # 8
    add_heading(doc, "八、Git 远程代码管理")
    add_body(doc, "代码托管在 GitHub，按实验分支管理，UML、源代码、测试、报告脚本同仓提交。")
    add_table(
        doc,
        ["项目", "内容"],
        [
            ["远程仓库", "https://github.com/Ash-Klein/hotel-booking-system.git（origin）"],
            ["当前分支", "lab3（跟踪 origin/lab3）"],
            ["分支用途", "main：需求与文档；lab2：UML 与界面设计；lab3：实验三实现与报告"],
            ["提交总数", "lab3 分支共 19 个提交"],
            ["提交规范", "feat / fix / docs 前缀，一次提交只做一件事"],
            ["忽略策略", "data/*.db、*.docx、缓存与设计工具二进制不入库，源代码、测试、截图入库"],
            ["当前状态", "本地领先 origin/lab3 四个提交；本次客人端 UI 改版改动尚未提交"],
        ],
        widths=[3.0, 13.0],
    )
    add_body(doc, "远程与提交记录（实际命令输出）：")
    add_code(
        doc,
        """> git remote -v
origin  https://github.com/Ash-Klein/hotel-booking-system.git (fetch)
origin  https://github.com/Ash-Klein/hotel-booking-system.git (push)

> git branch -vv
* lab3 6f57357 [origin/lab3: ahead 4] docs(lab3): 记录独立客人端的 Git 推送状态
  lab2 6b4c300 [origin/lab2: ahead 2] docs(lab2): 增加实验二报告源文与 UML 裁白边
  main 0ce2905 [origin/main] 第二轮跟进沟通 INT-02：需求定稿 51 条

> git log --oneline -6
6f57357 docs(lab3): 记录独立客人端的 Git 推送状态
b63e923 docs(lab3): 同步实现类图说明中的界面组件描述
c679516 docs(lab3): 按独立竖屏客人端更新报告与截图
9a2328c feat(lab3): 客人端改为独立 390x844 竖屏客户端
3c50616 docs(lab3): 实验三报告、界面截图与生成脚本
ec3a928 feat(lab3): 实现酒店预订系统三端桌面应用""",
    )
    add_body(
        doc,
        "日常流程是：改代码前先 pull 对应分支；完成一个小功能后跑单元测试与风格检查，"
        "通过后 git add/commit，提交信息写明范围和动作；阶段性成果 push 到 origin 同名分支，"
        "报告截图由 tools/capture_screens.py 重新生成后随提交更新。",
    )

    # 9
    add_heading(doc, "九、小结")
    add_bullets(
        doc,
        [
            "UML 到代码的核心是“结构、规则、事务、分层”四件事：类图给结构，状态图给规则，"
            "时序图给事务边界，组件/部署图给分层与部署方式。",
            "交付代码约 1.26 万有效行（46 个文件、32 项测试），客人端与员工端是两个独立程序，"
            "共用服务层与 SQLite。",
            "大模型显著加快了骨架搭建、测试编写和界面重做，但金额、库存、退款和状态机等口径必须人工把关；"
            "模型输出先小范围试用，再用编译、测试、风格检查和截图逐项验收。",
        ],
    )

    return doc


def main() -> None:
    """Build and save the report, then verify the paragraph and table counts."""
    doc = build()
    doc.save(OUTPUT)
    check = Document(OUTPUT)
    print(f"saved {OUTPUT}")
    print(f"paragraphs: {len(check.paragraphs)}, tables: {len(check.tables)}, "
          f"images: {len(check.inline_shapes)}")


if __name__ == "__main__":
    main()
