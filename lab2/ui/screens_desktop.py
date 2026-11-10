# -*- coding: utf-8 -*-
"""门店端 3 屏 + 集团端 3 屏（1440×900，1.5x）。"""

from theme import C
from widgets import Canvas

S = 1.5


# ---------------- 通用外壳 ----------------
def sidebar(c, brand, sub, items, active, accent="门店后台", user=None, initial=None):
    c.gradient(0, 0, 220, 900, "#12263F", "#1B3350")
    c.text(24, 26, brand, 16, "#FFFFFF", True)
    c.text(24, 50, sub, 10, "#8FA6C4")
    c.line(20, 78, 200, 78, "#2A4463", 1)
    c.text(24, 94, accent, 9, "#6F88A8")
    yy = 118
    for i, (name, icon) in enumerate(items):
        on = i == active
        if on:
            c.rrect(12, yy - 6, 196, 40, 8, "#1E3A5F")
            c.rect(12, yy + 4, 3, 20, C["gold"])
        col = "#FFFFFF" if on else "#A9BCD4"
        icon_fn = {
            "home": c.icon_home, "list": c.icon_chart, "calendar": c.icon_calendar,
            "chart": c.icon_chart, "user": c.icon_user, "settings": c.icon_sliders,
        }[icon]
        icon_fn(26, yy, 17, col)
        c.text(54, yy + 9, name, 12, col, on, "lm")
        yy += 46
    # 底部账号
    c.line(20, 790, 200, 790, "#2A4463", 1)
    if accent == "门店后台":
        who, ini = f"外滩店 · {user or '前台小林'}", initial or "林"
    else:
        who, ini = "集团运营 · 张敏", "张"
    c.avatar(22, 808, 34, ini, "#24405F", "#FFFFFF")
    c.text(66, 812, who, 10, "#D6E2F0", True)
    c.text(66, 830, "工号 10023 · 在线", 9, "#7F98B6")


def topbar(c, title, subtitle="", user="前台小林", store="外滩店", initial="林"):
    c.rect(220, 0, 1220, 64, "#FFFFFF")
    c.line(220, 64, 1440, 64, C["border"], 1)
    c.text(244, 22, title, 19, C["text"], True)
    if subtitle:
        c.text(244, 46, subtitle, 10, C["muted"])
    c.rrect(900, 16, 240, 32, 16, "#F4F6FA", outline=C["border"])
    c.icon_search(916, 23, 15, C["faint"])
    c.text(940, 32, "搜索订单 / 客人", 10, C["faint"], False, "lm")
    c.icon_bell(1160, 22, 18, C["muted"])
    c.circle(1172, 20, 3.5, fill=C["red"])
    c.avatar(1204, 14, 34, initial, C["blue_bg"], C["primary"])
    c.text(1248, 22, user, 10, C["text"], True)
    c.text(1248, 38, store, 9, C["muted"])


def shell_store(c, active, title, subtitle="", user="前台小林", initial="林"):
    sidebar(c, "云栖酒店", "YUNQI · 门店后台",
            [("今日工作台", "home"), ("订单管理", "list"), ("库存与房价", "calendar"),
             ("经营报表", "chart"), ("门店设置", "settings")], active,
            user=user, initial=initial)
    topbar(c, title, subtitle, user, "外滩店", initial)


def shell_group(c, active, title, subtitle=""):
    sidebar(c, "云栖酒店集团", "YUNQI · 集团后台",
            [("门店与房型", "home"), ("经营报表", "chart"), ("权限与审计", "user"),
             ("系统设置", "settings")], active, accent="集团后台")
    topbar(c, title, subtitle, "集团运营 张敏", "集团总部", "张")


def kpi(c, x, y, w, label, value, sub="", color=None, icon="chart"):
    c.rrect(x, y, w, 96, 14, C["card"], shadow=True)
    c.text(x + 20, y + 18, label, 10, C["muted"])
    c.text(x + 20, y + 38, value, 26, color or C["text"], True)
    if sub:
        c.text(x + 20, y + 74, sub, 9, C["faint"])
    c.circle(x + w - 34, y + 34, 18, fill=C["blue_bg"])
    if icon == "chart":
        c.icon_chart(x + w - 43, y + 25, 18, C["primary"])
    elif icon == "user":
        c.icon_user(x + w - 43, y + 25, 18, C["primary"])
    elif icon == "bell":
        c.icon_bell(x + w - 43, y + 25, 18, C["primary"])


def table_head(c, x, y, w, cols, h=38):
    c.rect(x, y, w, h, "#F7F9FC")
    c.line(x, y + h, x + w, y + h, C["border"], 1)
    cx = x + 16
    for item in cols:
        label, cw = item[0], item[1]
        align = item[2] if len(item) > 2 else "left"
        if align == "right":
            c.text(cx + cw - 16, y + h / 2, label, 9, C["faint"], False, "rm")
        elif align == "center":
            c.text(cx + cw / 2, y + h / 2, label, 9, C["faint"], False, "mm")
        else:
            c.text(cx, y + h / 2, label, 9, C["faint"], False, "lm")
        cx += cw


def status_pill(c, x, y, text, kind="green"):
    m = {"green": (C["green"], C["green_bg"]), "amber": (C["amber"], C["amber_bg"]),
         "red": (C["red"], C["red_bg"]), "blue": (C["primary"], C["blue_bg"]),
         "gray": (C["muted"], "#F0F2F6")}
    fg, bg = m[kind]
    c.pill(x, y, text, 9, fg, bg, 8, 22)


def mini(c, x, y, text):
    c.text(x, y, text, 9, C["faint"])


def field(c, x, y, w, value, h=38, chevron=False):
    c.rrect(x, y, w, h, 8, "#FFFFFF", outline=C["border"])
    c.text(x + 14, y + h / 2, value, 10, C["text"], False, "lm")
    if chevron:
        c.chevron_down(x + w - 22, y + h / 2 - 3, 8, C["muted"])


# ---------------- 门店端 ----------------
def screen06(path):
    c = Canvas(1440, 900, S)
    shell_store(c, 0, "今日工作台", "2026年11月10日 周二 · 外滩店")

    c.rrect(244, 88, 280, 96, 14, C["card"], shadow=True)
    c.text(264, 106, "今日到店", 10, C["muted"])
    c.text(264, 126, "12", 26, C["text"], True)
    c.text(264, 162, "已办理 4 · 待办理 8", 9, C["faint"])
    c.circle(480, 122, 18, fill=C["blue_bg"])
    c.icon_calendar(471, 113, 18, C["primary"])

    kpi(c, 539, 88, 280, "待退房", "8", "12:00 前退房 6 间", C["text"], "chart")
    kpi(c, 834, 88, 280, "在住", "26", "含今日续住 3 间", C["text"], "user")
    kpi(c, 1129, 88, 287, "待处理异常", "2", "需门店处置 1 · 协助核实 1", C["red"], "bell")

    # 到店/离店
    c.rrect(244, 204, 770, 560, 14, C["card"], shadow=True)
    c.text(264, 222, "今日到店", 15, C["text"], True)
    c.pill(344, 220, "12", 9, C["primary"], C["blue_bg"], 7, 20)
    c.text(410, 226, "今日离店 8", 10, C["muted"])
    c.text(986, 226, "全部 >", 9, C["muted"], False, "ra")

    cols = [("客人", 140), ("房型", 170), ("房号", 80), ("到店", 100), ("状态", 100), ("操作", 120)]
    table_head(c, 264, 256, 730, cols)
    rows = [
        ("张伟", "高级大床房 · 2 晚", "待分配", "14:00", "待入住", "办理入住", "green"),
        ("李娜", "行政套房 · 1 晚", "待分配", "15:30", "待入住", "办理入住", "green"),
        ("王强", "高级双床房 · 3 晚", "待分配", "16:00", "待入住", "办理入住", "green"),
        ("陈静", "高级大床房 · 2 晚", "待分配", "18:00", "已确认", "查看", "blue"),
        ("刘洋", "商务大床房 · 1 晚", "待分配", "20:30", "已确认", "查看", "blue"),
    ]
    yy = 300
    for i, (name, room, no, eta, st, op, kind) in enumerate(rows):
        if i % 2 == 1:
            c.rect(264, yy, 730, 56, "#FAFBFD")
        c.avatar(280, yy + 14, 28, name[0])
        c.text(320, yy + 16, name, 11, C["text"], True)
        c.text(320, yy + 34, "138****" + str(1000 + i), 8, C["faint"])
        c.text(460, yy + 24, room, 10, C["text"])
        c.text(630, yy + 24, no, 10, C["muted"])
        c.text(710, yy + 24, eta, 10, C["muted"])
        status_pill(c, 810, yy + 17, st, kind)
        c.button(910, yy + 14, 78, 28, op, 9, C["primary"] if op == "办理入住" else "#FFFFFF",
                 "#FFFFFF" if op == "办理入住" else C["primary"], 7,
                 outline=None if op == "办理入住" else C["border"])
        yy += 56
    c.text(264, 740, "显示 1–5 条，共 12 条", 9, C["faint"])
    c.text(986, 740, "1  2  3  ›", 9, C["muted"], False, "ra")

    # 异常
    c.rrect(1030, 204, 386, 260, 14, C["card"], shadow=True)
    c.text(1050, 222, "待处理异常", 14, C["text"], True)
    c.pill(1140, 220, "2", 9, C["red"], C["red_bg"], 6, 20)
    items = [("到店无房", "周敏 · 行政套房 · 15:30", "red", "需门店处置", "处理 >"),
             ("支付异常", "订单 YQ202611090032 · 财务处理中", "amber", "协助核实", "核实 >")]
    yy = 258
    for title, desc, kind, owner, action in items:
        c.rrect(1050, yy, 346, 82, 10, C["red_bg"] if kind == "red" else C["amber_bg"])
        c.text(1066, yy + 14, title, 11, C["red"] if kind == "red" else C["amber"], True)
        c.pill(1300, yy + 12, owner, 8, C["red"] if kind == "red" else C["amber"],
               "#FFFFFF", 5, 18)
        c.text(1066, yy + 34, desc, 9, C["muted"], maxw=300)
        c.text(1380, yy + 58, action, 9, C["primary"], False, "ra")
        yy += 94

    # 快捷操作
    c.rrect(1030, 480, 386, 284, 14, C["card"], shadow=True)
    c.text(1050, 498, "快捷操作", 14, C["text"], True)
    ops = [("办理入住", "green"), ("办理退房", "blue"), ("关房 / 停售", "amber"), ("调整价格", "blue")]
    for i, (label, kind) in enumerate(ops):
        x = 1050 + (i % 2) * 176
        y = 532 + (i // 2) * 96
        c.rrect(x, y, 166, 80, 10, "#F7F9FC", outline=C["border"])
        c.circle(x + 28, y + 26, 14, fill=C["blue_bg"])
        c.text(x + 28, y + 26, label[0], 10, C["primary"], True, "mm")
        c.text(x + 50, y + 20, label, 11, C["text"], True)
        c.text(x + 16, y + 56, "常用操作", 8, C["faint"])
    c.save(path)


def screen06a(path):
    c = Canvas(1440, 900, S)
    shell_store(c, 1, "异常处置", "外滩店 · 到店无房 / 在店纠纷")

    x = 244
    for label, active in [("待处置 3", True), ("到店无房 2", False),
                          ("在店纠纷 1", False), ("处置记录 4", False)]:
        w = c.text_w(label, 10, active) + 34
        c.rrect(x, 84, w, 32, 16, C["primary"] if active else "#FFFFFF",
                outline=None if active else C["border"])
        c.text(x + w / 2, 100, label, 10, "#FFFFFF" if active else C["muted"], active, "mm")
        x += w + 10

    # 左：异常工单
    c.rrect(244, 132, 650, 680, 14, C["card"], shadow=True)
    c.text(264, 150, "异常工单", 15, C["text"], True)
    c.pill(350, 148, "3", 9, C["red"], C["red_bg"], 7, 20)
    c.text(874, 154, "按等待时长排序", 9, C["faint"], False, "ra")

    c.text(264, 184, "待处置", 10, C["text"], True)
    c.pill(302, 181, "3", 8, C["red"], C["red_bg"], 6, 18)
    cols = [("类型", 90), ("订单 / 客人", 210), ("房型", 140), ("到店 / 发生", 100), ("等待", 60)]
    table_head(c, 264, 204, 610, cols)

    rows = [
        ("到店无房", "YQ202611100041", "周敏", "行政套房", "15:30", "25 分钟", "red", True),
        ("到店无房", "YQ202611100047", "孙悦", "高级双床房", "16:00", "12 分钟", "red", False),
        ("在店纠纷", "YQ202611100028", "赵敏", "家庭房", "11-13 起", "2 小时", "amber", False),
    ]
    yy = 242
    for typ, no, name, room, eta, wait, kind, on in rows:
        if on:
            c.rect(264, yy, 610, 72, "#EEF4FC")
            c.rect(264, yy, 3, 72, C["primary"])
        c.line(264, yy + 72, 874, yy + 72, C["line"], 1)
        status_pill(c, 280, yy + 12, typ, kind)
        c.text(370, yy + 10, no, 9, C["muted"])
        c.text(370, yy + 30, name, 11, C["text"], True)
        c.text(580, yy + 24, room, 10, C["text"])
        c.text(720, yy + 24, eta, 10, C["muted"])
        c.text(820, yy + 24, wait, 10, C["red"] if on else C["muted"], on)
        yy += 72

    c.line(264, 476, 874, 476, C["line"], 1)
    c.text(264, 492, "最近处置记录", 10, C["text"], True)
    c.pill(386, 489, "4", 8, C["primary"], C["blue_bg"], 6, 18)
    c.text(874, 498, "查看全部 >", 9, C["muted"], False, "ra")

    subs = [
        ("YQ202611100035", "吴磊", "到店无房", "已转静安店", "13:40", "green"),
        ("YQ202611100038", "何静", "在店纠纷", "待集团审核", "12:10", "amber"),
        ("YQ202611100029", "郑爽", "到店无房", "已退款", "11:05", "gray"),
        ("YQ202611100022", "王芳", "在店纠纷", "已和解离店", "10:30", "gray"),
    ]
    yy = 522
    for no, name, typ, result, tm, kind in subs:
        c.text(280, yy + 8, no, 8, C["muted"])
        c.text(280, yy + 25, f"{name} · {typ}", 10, C["text"], True)
        status_pill(c, 640, yy + 14, result, kind)
        c.text(800, yy + 25, tm, 9, C["faint"])
        c.line(280, yy + 51, 860, yy + 51, C["line"], 1)
        yy += 52

    c.text(264, 758, "最近 4 条 · 审核结果回写台账与报表", 9, C["faint"])

    # 右：到店无房处置
    c.rrect(910, 132, 506, 680, 14, C["card"], shadow=True)
    c.text(934, 150, "到店无房处置", 15, C["text"], True)
    c.pill(1312, 148, "待提交", 9, C["amber"], C["amber_bg"], 7, 20)

    c.rrect(934, 184, 458, 96, 12, "#F7F9FC")
    c.avatar(950, 198, 40, "周")
    c.text(1002, 196, "周敏", 13, C["text"], True)
    c.text(1002, 218, "138****6620 · 订单 YQ202611100041", 9, C["muted"])
    c.text(1002, 238, "行政套房 · 11-14 → 11-16 · 1 间 · ¥1796", 9, C["muted"])
    status_pill(c, 1296, 196, "已确认待入住", "green")

    mini(c, 934, 300, "异常原因")
    field(c, 934, 316, 458, "原房间空调故障，无法入住")

    mini(c, 934, 368, "同城安置（优先同城其他门店）")
    field(c, 934, 384, 458, "云栖酒店 · 静安店", chevron=True)
    field(c, 934, 432, 286, "行政套房")
    field(c, 1232, 432, 160, "1 间")
    field(c, 934, 480, 458, "11-14 → 11-16（2 晚）")

    mini(c, 934, 532, "费用与通知")
    field(c, 934, 548, 220, "赔付 ¥200")
    field(c, 1172, 548, 220, "安置费 ¥898")
    field(c, 934, 596, 458, "14:05 电话联系，客人同意转店")

    c.text(934, 646, "提交后订单转「异常订单（待审核）」，库存保留", 9, C["amber"])
    c.text(934, 664, "集团审核前不得退款、取消或改期", 9, C["muted"])

    c.button(934, 700, 150, 44, "暂存", 11, "#FFFFFF", C["primary"], 8, outline=C["border"])
    c.button(1096, 700, 296, 44, "标记异常并提交集团审核", 12, C["primary"], "#FFFFFF", 8)
    c.text(934, 762, "操作写入日志（REQ-030），集团审核结果回写本页", 8, C["faint"])
    c.save(path)


def screen06b(path):
    c = Canvas(1440, 900, S)
    shell_store(c, 0, "停业与支付异常", "外滩店 · 门店临时停业 / 支付异常协助", "店长王敏", "王")

    # 左：门店停业
    c.rrect(244, 84, 656, 728, 14, C["card"], shadow=True)
    c.text(264, 104, "门店停业处置", 15, C["text"], True)
    c.text(474, 106, "当前状态", 9, C["faint"])
    c.pill(534, 101, "临时停业", 9, C["red"], C["red_bg"], 7, 22)
    c.button(740, 96, 140, 34, "恢复营业", 10, "#FFFFFF", C["primary"], 8, outline=C["border"])
    c.line(264, 140, 880, 140, C["line"], 1)

    c.text(264, 158, "受影响订单处置", 11, C["text"], True)
    c.text(264, 176, "仅列出已支付的有效订单，退款或改期后自动移出", 9, C["muted"])
    field(c, 264, 196, 300, "11-14 00:00 → 11-15 12:00")
    c.text(580, 214, "调整", 9, C["primary"])
    c.text(264, 250, "受影响订单 12 单 · 已通知 8 · 待通知 4", 10, C["text"])

    cols = [("订单号", 130), ("客人", 70), ("房型", 130),
            ("入住 - 离店", 110), ("金额", 70), ("通知", 70)]
    table_head(c, 264, 276, 616, cols)
    rows = [
        ("YQ202611100041", "周敏", "行政套房", "11-14 → 11-16", "¥1796", "已通知", "green"),
        ("YQ202611100047", "孙悦", "高级双床房", "11-14 → 11-16", "¥1056", "待通知", "amber"),
        ("YQ202611100015", "陈静", "高级大床房", "11-14 → 11-15", "¥568", "已通知", "green"),
        ("YQ202611100016", "王强", "高级双床房", "11-14 → 11-17", "¥1584", "待通知", "amber"),
        ("YQ202611100017", "李娜", "行政套房", "11-14 → 11-15", "¥898", "已通知", "green"),
        ("YQ202611100018", "张伟", "高级大床房", "11-14 → 11-16", "¥2272", "待通知", "amber"),
    ]
    yy = 314
    for i, (no, name, room, dates, amount, notice, kind) in enumerate(rows):
        if i % 2 == 1:
            c.rect(264, yy, 616, 54, "#FAFBFD")
        c.text(280, yy + 20, no, 9, C["text"])
        c.text(410, yy + 20, name, 10, C["text"], True)
        c.text(480, yy + 20, room, 9, C["text"])
        c.text(610, yy + 20, dates, 9, C["muted"])
        c.text(720, yy + 20, amount, 9, C["text"])
        status_pill(c, 790, yy + 16, notice, kind)
        yy += 54

    c.text(264, 660, "停业期间退款不受 24 小时与 ¥500 上限限制（REQ-028）", 9, C["amber"])
    c.button(264, 700, 180, 40, "批量通知（4）", 10, "#FFFFFF", C["primary"], 8, outline=C["border"])
    c.button(456, 700, 200, 40, "批量全额退款", 10, C["primary"], "#FFFFFF", 8)
    c.text(264, 754, "退款后订单转已取消，库存按 REQ-009 释放；通知结果逐单留痕", 9, C["faint"])

    # 右：支付异常协助核实
    c.rrect(916, 84, 500, 728, 14, C["card"], shadow=True)
    c.text(936, 104, "支付异常 · 协助核实", 15, C["text"], True)
    c.pill(1320, 102, "财务处理中", 9, C["amber"], C["amber_bg"], 7, 20)

    c.rrect(936, 140, 460, 104, 12, "#F7F9FC")
    c.avatar(952, 154, 40, "刘")
    c.text(1002, 152, "刘洋", 13, C["text"], True)
    c.text(1002, 174, "135****2277 · 订单 YQ202611090032", 9, C["muted"])
    c.text(1002, 194, "商务大床房 · 11-13 → 11-14 · ¥568", 9, C["muted"])
    status_pill(c, 1300, 152, "异常", "red")

    mini(c, 936, 264, "异常类型")
    field(c, 936, 280, 460, "退款失败（渠道超时）")
    c.text(936, 330, "退款单号 R20261109001 · 微信支付", 9, C["muted"])

    c.text(936, 366, "门店核实", 10, C["text"], True)
    c.text(936, 390, "客人是否已离店", 9, C["faint"])
    c.pill(1080, 384, "是", 9, "#FFFFFF", C["primary"], 8, 22)
    c.pill(1128, 384, "否", 9, C["muted"], "#FFFFFF", 8, 22, outline=C["border"])

    c.text(936, 426, "支付凭证", 9, C["faint"])
    field(c, 936, 442, 220, "已核对")
    c.text(1172, 426, "联系结果", 9, C["faint"])
    field(c, 1172, 442, 224, "已告知延迟")

    mini(c, 936, 490, "备注")
    field(c, 936, 506, 460, "客人已离店，退款到账后电话通知", h=56)

    c.text(936, 590, "处理进度", 10, C["text"], True)
    steps = [("10:12", "系统识别退款失败"), ("10:15", "推送门店 / 财务"), ("14:20", "门店核实完成")]
    yy = 610
    for tm, desc in steps:
        c.circle(940, yy + 6, 4, fill=C["primary"])
        c.text(954, yy, tm, 9, C["muted"])
        c.text(1000, yy, desc, 9, C["text"])
        yy += 26

    c.text(936, 692, "门店只做核实，不补录订单、不发起退款", 9, C["amber"])
    c.button(936, 714, 460, 42, "提交运营核实", 12, C["primary"], "#FFFFFF", 8)
    c.text(936, 770, "提交后由财务跟进，处理结果回写异常台账", 8, C["faint"])
    c.save(path)


def screen07(path):
    c = Canvas(1440, 900, S)
    shell_store(c, 2, "库存与房价", "外滩店 · 高级大床房 · 2026年11月")

    # 工具栏
    c.rrect(244, 84, 210, 34, 8, "#FFFFFF", outline=C["border"])
    c.text(260, 101, "高级大床房", 10, C["text"], False, "lm")
    c.chevron_down(430, 97, 8, C["muted"])
    c.rrect(466, 84, 150, 34, 8, "#FFFFFF", outline=C["border"])
    c.text(482, 101, "2026年11月", 10, C["text"], False, "lm")
    c.chevron_down(596, 97, 8, C["muted"])
    for i, (label, prim) in enumerate([("批量调价", False), ("关房", False), ("协议锁房", True)]):
        x = 1030 + i * 128
        c.button(x, 84, 116, 34, label, 10,
                 C["primary"] if prim else "#FFFFFF",
                 "#FFFFFF" if prim else C["primary"], 8,
                 outline=None if prim else C["border"])

    # 概览
    stats = [("可售", "128", C["green"]), ("已售", "96", C["text"]),
             ("协议锁定", "12", C["purple"]), ("关房", "4", C["muted"])]
    for i, (k, v, col) in enumerate(stats):
        x = 244 + i * 296
        c.rrect(x, 134, 280, 52, 10, C["card"], shadow=True)
        c.text(x + 16, 150, k, 9, C["muted"])
        c.text(x + 16, 162, v, 16, col, True)

    # 日历
    c.rrect(244, 202, 1172, 566, 14, C["card"], shadow=True)
    c.text(264, 220, "房价与库存日历", 14, C["text"], True)
    c.text(1396, 226, "单位：元 / 间夜", 9, C["faint"], False, "ra")
    days = [("11/10", "周一"), ("11/11", "周二"), ("11/12", "周三"), ("11/13", "周四"),
            ("11/14", "周五"), ("11/15", "周六"), ("11/16", "周日")]
    x0, y0 = 264, 256
    first_w = 150
    cell_w = (1172 - 32 - first_w) / 7
    c.rect(x0, y0, 1172 - 32, 44, "#F7F9FC")
    c.text(x0 + 14, y0 + 22, "房型 / 日期", 9, C["faint"], False, "lm")
    for i, (d, wd) in enumerate(days):
        cx = x0 + first_w + i * cell_w
        c.text(cx + cell_w / 2, y0 + 14, d, 9, C["text"], True, "ma")
        c.text(cx + cell_w / 2, y0 + 32, wd, 8, C["faint"], False, "ma")

    rooms = [("高级大床房", "20", ["568|3", "568|5", "598|2", "598|0", "658|1", "698|2", "568|6"]),
             ("高级双床房", "18", ["528|6", "528|4", "528|2", "558|0", "598|1", "658|0", "528|4"]),
             ("行政套房", "8", ["898|2", "898|1", "898|0", "898|0", "998|0", "1098|1", "898|2"]),
             ("商务大床房", "12", ["488|5", "488|3", "488|2", "488|1", "528|0", "568|0", "488|3"]),
             ("家庭房", "6", ["668|1", "668|1", "668|0", "668|0", "728|0", "768|0", "668|1"])]
    yy = y0 + 44
    for ri, (name, total, cells) in enumerate(rooms):
        if ri % 2 == 1:
            c.rect(x0, yy, 1172 - 32, 84, "#FAFBFD")
        c.text(x0 + 14, yy + 24, name, 10, C["text"], True)
        c.text(x0 + 14, yy + 44, "总量 " + total + " 间", 8, C["faint"])
        for ci, cell in enumerate(cells):
            price, left = cell.split("|")
            left = int(left)
            cx = x0 + first_w + ci * cell_w
            if left == 0:
                bg, fg, tag = "#FDECEA", C["red"], "满房"
            elif left <= 2:
                bg, fg, tag = C["amber_bg"], C["amber"], "紧张"
            else:
                bg, fg, tag = C["green_bg"], C["green"], "可售"
            c.rrect(cx + 3, yy + 6, cell_w - 6, 70, 6, bg)
            c.text(cx + cell_w / 2, yy + 22, "¥" + price, 11, C["text"], True, "ma")
            c.text(cx + cell_w / 2, yy + 42, f"余 {left}", 9, fg, False, "ma")
            c.text(cx + cell_w / 2, yy + 58, tag, 8, fg, False, "ma")
        yy += 84

    # 图例
    c.text(264, 786, "图例", 9, C["faint"])
    for i, (label, color) in enumerate([("可售充足", C["green_bg"]), ("≤2 间", C["amber_bg"]),
                                        ("满房", C["red_bg"]), ("协议锁定", "#D9C9F2")]):
        x = 304 + i * 120
        c.rrect(x, 780, 12, 12, 3, color)
        c.text(x + 18, 786, label, 9, C["muted"])
    c.text(1396, 786, "点击单元格可调价 / 关房 / 锁房", 9, C["faint"], False, "ra")
    c.save(path)


def screen08(path):
    c = Canvas(1440, 900, S)
    shell_store(c, 1, "订单管理", "外滩店 · 订单检索与入住办理")

    c.rrect(244, 84, 520, 36, 18, "#FFFFFF", outline=C["border"])
    c.icon_search(260, 92, 16, C["faint"])
    c.text(284, 102, "订单号 / 手机号 / 姓名", 10, C["faint"], False, "lm")
    c.button(776, 84, 80, 36, "检索", 10, C["primary"], "#FFFFFF", 8)
    for i, label in enumerate(["今日到店", "待入住", "已入住", "异常", "全部"]):
        x = 244 + i * 100
        on = i == 0
        c.text(x + 32, 144, label, 10, C["primary"] if on else C["muted"], on, "mm")
        if on:
            c.rect(x + 20, 160, 52, 2, C["primary"])

    c.rrect(244, 180, 780, 600, 14, C["card"], shadow=True)
    cols = [("订单号", 150), ("客人", 90), ("手机号", 110), ("房型", 130), ("入住 - 离店", 140), ("状态", 80)]
    table_head(c, 260, 196, 748, cols)
    rows = [
        ("YQ202611100018", "张伟", "138****1024", "高级大床房", "11-14 → 11-16", "待入住", "green"),
        ("YQ202611100017", "李娜", "139****8842", "行政套房", "11-14 → 11-15", "待入住", "green"),
        ("YQ202611100016", "王强", "137****5610", "高级双床房", "11-14 → 11-17", "待入住", "green"),
        ("YQ202611100015", "陈静", "136****9033", "高级大床房", "11-14 → 11-16", "已确认", "blue"),
        ("YQ202611090032", "刘洋", "135****2277", "商务大床房", "11-13 → 11-14", "异常", "red"),
        ("YQ202611090028", "赵敏", "188****6612", "家庭房", "11-13 → 11-15", "已入住", "gray"),
    ]
    yy = 240
    for i, (no, name, phone, room, dates, st, kind) in enumerate(rows):
        if i % 2 == 1:
            c.rect(260, yy, 748, 64, "#FAFBFD")
        if i == 0:
            c.rect(260, yy, 748, 64, "#EEF4FC")
        c.text(276, yy + 24, no, 9, C["text"])
        c.text(410, yy + 24, name, 10, C["text"], True)
        c.text(500, yy + 24, phone, 9, C["muted"])
        c.text(610, yy + 24, room, 9, C["text"])
        c.text(740, yy + 24, dates, 9, C["muted"])
        status_pill(c, 880, yy + 21, st, kind)
        if st == "异常":
            c.text(960, yy + 24, "处置 >", 9, C["primary"])
        yy += 64
    c.text(260, 740, "共 6 条订单 · 仅显示本门店", 9, C["faint"])

    # 入住抽屉
    c.shadow(1040, 64, 400, 836, 0, 18, 38, 0)
    c.rect(1040, 64, 400, 836, "#FFFFFF")
    c.text(1064, 88, "入住办理", 16, C["text"], True)
    c.text(1416, 94, "关闭 ×", 10, C["muted"], False, "ra")
    c.text(1064, 116, "订单 YQ202611100018", 9, C["muted"])

    c.rrect(1064, 146, 352, 84, 12, "#F7F9FC")
    c.avatar(1080, 162, 44, "张")
    c.text(1136, 162, "张伟", 14, C["text"], True)
    c.text(1136, 184, "138****1024 · 高级会员", 9, C["muted"])
    c.text(1136, 202, "入住 11-14 → 离店 11-16 · 2 间", 9, C["muted"])

    c.text(1064, 256, "证件核验", 10, C["text"], True)
    c.rrect(1064, 274, 352, 40, 8, "#FFFFFF", outline=C["border"])
    c.text(1080, 292, "身份证 3101**********1024", 9, C["muted"], False, "lm")
    c.text(1400, 292, "已核验", 9, C["green"], False, "rm")

    c.text(1064, 334, "分配房号", 10, C["text"], True)
    c.rrect(1064, 352, 168, 40, 8, "#FFFFFF", outline=C["border"])
    c.text(1080, 370, "1208", 11, C["text"], True, "lm")
    c.chevron_down(1214, 366, 8, C["muted"])
    c.rrect(1248, 352, 168, 40, 8, "#FFFFFF", outline=C["border"])
    c.text(1264, 370, "押金 ¥300", 10, C["text"], False, "lm")

    c.text(1064, 412, "入住人", 10, C["text"], True)
    c.text(1064, 432, "张伟 · 1 人 · 预计 14:00 到店", 9, C["muted"])
    c.line(1064, 460, 1416, 460, C["line"], 1)

    c.text(1064, 478, "订单金额", 10, C["muted"])
    c.text(1416, 476, "¥2272", 18, C["red"], True, "ra")
    c.text(1064, 504, "已支付 · 微信支付", 9, C["green"])
    c.line(1064, 532, 1416, 532, C["line"], 1)

    c.text(1064, 550, "操作备注", 10, C["text"], True)
    c.rrect(1064, 568, 352, 90, 8, "#FFFFFF", outline=C["border"])
    c.text(1078, 582, "客人要求高楼层，已安排 12 层。", 9, C["muted"])

    c.button(1064, 690, 352, 46, "确认入住并制卡", 13, C["primary"], "#FFFFFF", 10)
    c.text(1240, 754, "确认后将写入房号并通知客人", 8, C["faint"], False, "mm")
    c.save(path)


# ---------------- 集团端 ----------------
def screen09(path):
    c = Canvas(1440, 900, S)
    shell_group(c, 0, "门店与房型", "集团统一维护 · 门店只读")

    c.button(1200, 84, 100, 34, "新增门店", 10, C["primary"], "#FFFFFF", 8)
    c.button(1308, 84, 80, 34, "导出", 10, "#FFFFFF", C["primary"], 8, outline=C["border"])

    for i, label in enumerate(["门店档案", "房型标准"]):
        on = i == 0
        c.text(244 + i * 100, 142, label, 11, C["primary"] if on else C["muted"], on, "lm")
        if on:
            c.rect(244 + i * 100, 158, 56, 2, C["primary"])

    c.rrect(244, 176, 760, 600, 14, C["card"], shadow=True)
    cols = [("门店", 230), ("城市", 100), ("类型", 90), ("房型数", 90), ("状态", 90), ("操作", 120)]
    table_head(c, 260, 194, 728, cols)
    rows = [
        ("云栖酒店 · 外滩店", "上海", "直营", "6", "营业", "编辑"),
        ("云栖酒店 · 人民广场店", "上海", "直营", "5", "营业", "编辑"),
        ("云栖酒店 · 西湖店", "杭州", "加盟", "4", "营业", "编辑"),
        ("云栖酒店 · 新街口店", "南京", "加盟", "4", "营业", "编辑"),
        ("云栖酒店 · 天府广场店", "成都", "直营", "5", "筹备", "编辑"),
        ("云栖酒店 · 光谷店", "武汉", "加盟", "3", "停业", "编辑"),
    ]
    yy = 236
    for i, (name, city, typ, cnt, st, op) in enumerate(rows):
        if i % 2 == 1:
            c.rect(260, yy, 728, 64, "#FAFBFD")
        c.text(276, yy + 24, name, 10, C["text"], True, maxw=210)
        c.text(506, yy + 24, city, 9, C["muted"])
        c.pill(606, yy + 21, typ, 8, C["primary"] if typ == "直营" else C["purple"],
               C["blue_bg"] if typ == "直营" else C["purple_bg"], 6, 20)
        c.text(696, yy + 24, cnt, 9, C["text"])
        status_pill(c, 786, yy + 21, st, "green" if st == "营业" else ("amber" if st == "筹备" else "gray"))
        c.text(886, yy + 24, op, 9, C["primary"])
        yy += 64
    c.text(260, 744, "共 46 家门店 · 直营 18 / 加盟 28", 9, C["faint"])

    # 详情
    c.rrect(1024, 176, 392, 600, 14, C["card"], shadow=True)
    c.text(1044, 194, "门店详情", 14, C["text"], True)
    c.text(1396, 200, "外滩店", 9, C["muted"], False, "ra")
    c.gradient(1044, 220, 352, 96, "#8FA9C9", "#D9E4F2", 10)
    c.text(1060, 286, "云栖酒店 · 外滩店", 13, "#FFFFFF", True)

    info = [("城市 / 商圈", "上海 · 外滩"), ("地址", "黄浦区中山东一路 18 号"),
            ("门店类型", "直营"), ("开业时间", "2019 年 6 月")]
    yy = 336
    for k, v in info:
        c.text(1044, yy, k, 9, C["faint"])
        c.text(1044, yy + 16, v, 10, C["text"])
        yy += 42

    c.line(1044, 510, 1396, 510, C["line"], 1)
    c.text(1044, 526, "房型参数（集团统一）", 11, C["text"], True)
    rooms = [("高级大床房", "1.8m 大床 · 28㎡ · 含早 · 2 人"),
             ("高级双床房", "1.2m 双床 · 30㎡ · 含早 · 2 人"),
             ("行政套房", "1.8m 大床 · 46㎡ · 含双早 · 3 人")]
    yy = 552
    for name, desc in rooms:
        c.text(1044, yy, name, 10, C["text"], True)
        c.text(1044, yy + 16, desc, 8, C["muted"])
        yy += 40
    c.rrect(1044, 690, 352, 62, 8, C["amber_bg"])
    c.text(1058, 702, "门店无房型编辑权限", 9, C["amber"], True)
    c.text(1058, 720, "新增 / 修改房型参数需由集团运营操作（REQ-003）", 8, "#8A6A12")
    c.save(path)


def screen10(path):
    c = Canvas(1440, 900, S)
    shell_group(c, 1, "经营报表", "2026年11月 · 全集团")

    c.rrect(244, 84, 130, 34, 8, "#FFFFFF", outline=C["border"])
    c.text(260, 101, "全部城市", 9, C["text"], False, "lm")
    c.chevron_down(350, 97, 8, C["muted"])
    c.rrect(386, 84, 130, 34, 8, "#FFFFFF", outline=C["border"])
    c.text(402, 101, "2026-11", 9, C["text"], False, "lm")
    c.chevron_down(492, 97, 8, C["muted"])
    c.rrect(528, 84, 130, 34, 8, "#FFFFFF", outline=C["border"])
    c.text(544, 101, "直营 + 加盟", 9, C["text"], False, "lm")
    c.chevron_down(634, 97, 8, C["muted"])
    c.button(1308, 84, 76, 34, "导出", 10, "#FFFFFF", C["primary"], 8, outline=C["border"])

    kpi(c, 244, 134, 280, "出租率", "78.4%", "较上月 +2.1pt", C["green"], "chart")
    kpi(c, 539, 134, 280, "RevPAR", "¥412", "纯房费口径", C["text"], "chart")
    kpi(c, 834, 134, 280, "订单量", "1,286", "取消率 4.2%", C["text"], "user")
    kpi(c, 1129, 134, 287, "平均房价", "¥526", "含早房型占比 62%", C["text"], "chart")

    # 图表
    c.rrect(244, 250, 760, 330, 14, C["card"], shadow=True)
    c.text(264, 268, "近 10 日出租率", 14, C["text"], True)
    c.text(984, 274, "目标 75%", 9, C["faint"], False, "ra")
    vals = [72, 74, 71, 76, 79, 82, 80, 78, 81, 84]
    labels = [f"{i+1}" for i in range(10)]
    c.bar_chart(284, 310, 690, 210, vals, labels, C["primary"], maxv=100, fmt="{:.0f}%")

    # 城市排行
    c.rrect(1024, 250, 392, 330, 14, C["card"], shadow=True)
    c.text(1044, 268, "城市出租率", 14, C["text"], True)
    c.text(1396, 274, "按城市", 9, C["faint"], False, "ra")
    cities = [("上海", "82.1%", 0.82), ("杭州", "79.3%", 0.79), ("南京", "77.6%", 0.78),
              ("成都", "74.2%", 0.74), ("武汉", "71.8%", 0.72), ("苏州", "69.4%", 0.69)]
    yy = 300
    for name, pct, ratio in cities:
        c.text(1044, yy, name, 9, C["muted"])
        c.rrect(1084, yy + 2, 220, 8, 4, "#EEF2F7")
        c.rrect(1084, yy + 2, 220 * ratio, 8, 4, C["primary"] if name == "上海" else "#9DB4D2")
        c.text(1396, yy, pct, 9, C["text"], True, "ra")
        yy += 42

    # 明细
    c.rrect(244, 600, 1172, 270, 14, C["card"], shadow=True)
    c.text(264, 618, "门店明细", 14, C["text"], True)
    c.text(1396, 624, "T+1 更新 · 数据截至 11-09", 9, C["faint"], False, "ra")
    cols = [("门店", 300), ("城市", 100), ("出租率", 120), ("RevPAR", 120), ("订单量", 120), ("取消率", 100), ("趋势", 100)]
    table_head(c, 260, 648, 1140, cols)
    rows = [("外滩店", "上海", "86.2%", "¥486", "312", "3.1%", "↑"),
            ("人民广场店", "上海", "81.4%", "¥438", "286", "4.0%", "↑"),
            ("西湖店", "杭州", "79.3%", "¥412", "244", "4.6%", "→"),
            ("新街口店", "南京", "75.1%", "¥386", "198", "5.2%", "↓")]
    yy = 690
    for i, row in enumerate(rows):
        if i % 2 == 1:
            c.rect(260, yy, 1140, 42, "#FAFBFD")
        for j, val in enumerate(row):
            cw = cols[j][1]
            xx = 260 + sum(cols[k][1] for k in range(j))
            c.text(xx + 4 if j == 0 else xx + cw / 2, yy + 21, val, 9,
                   C["green"] if val == "↑" else (C["red"] if val == "↓" else C["text"]),
                   j == 0, "lm" if j == 0 else "mm")
        yy += 42
    c.save(path)


def screen11(path):
    c = Canvas(1440, 900, S)
    shell_group(c, 2, "权限与审计", "角色权限矩阵 · 操作日志")

    for i, label in enumerate(["角色权限", "操作日志"]):
        on = i == 0
        c.text(244 + i * 100, 100, label, 11, C["primary"] if on else C["muted"], on, "lm")
        if on:
            c.rect(244 + i * 100, 116, 56, 2, C["primary"])

    c.rrect(244, 134, 760, 520, 14, C["card"], shadow=True)
    c.text(264, 152, "角色权限矩阵", 14, C["text"], True)
    c.text(984, 158, "仅集团运营可配置", 9, C["faint"], False, "ra")

    roles = ["顾客", "前台", "店长", "财务", "运营", "城市经理"]
    perms = ["查看报表", "修改价格", "关房/停售", "退款审批", "配置权限", "查看日志"]
    x0, y0 = 264, 188
    first_w, col_w = 170, (728 - 170) / 6
    c.rect(x0, y0, 728, 42, "#F7F9FC")
    c.text(x0 + 12, y0 + 21, "权限 / 角色", 9, C["faint"], False, "lm")
    for i, r in enumerate(roles):
        c.text(x0 + first_w + i * col_w + col_w / 2, y0 + 21, r, 8, C["text"], True, "mm")
    yy = y0 + 42
    matrix = [
        ("查看报表", [1, 0, 1, 1, 1, 1]),
        ("修改价格", [0, 0, 1, 0, 1, 0]),
        ("关房/停售", [0, 0, 1, 0, 1, 0]),
        ("退款审批", [0, 0, 1, 0, 1, 0]),
        ("配置权限", [0, 0, 0, 0, 1, 0]),
        ("查看日志", [0, 0, 0, 1, 1, 0]),
    ]
    for ri, (perm, marks) in enumerate(matrix):
        if ri % 2 == 1:
            c.rect(x0, yy, 728, 52, "#FAFBFD")
        c.text(x0 + 12, yy + 26, perm, 9, C["text"], False, "lm")
        for ci, m in enumerate(marks):
            cx = x0 + first_w + ci * col_w + col_w / 2
            if m:
                c.circle(cx, yy + 26, 8, fill=C["green_bg"])
                c.d.line([c.px(cx - 3.5), c.px(yy + 26), c.px(cx - 1), c.px(yy + 29),
                          c.px(cx + 4), c.px(yy + 22)], fill=C["green"], width=c.px(1.8))
            else:
                c.line(cx - 4, yy + 26, cx + 4, yy + 26, C["border"], 1.2)
        yy += 52
    c.text(x0, 620, "✓ 允许　— 拒绝；城市经理仅报表，按所属城市过滤", 9, C["faint"])

    # 说明
    c.rrect(1024, 134, 392, 520, 14, C["card"], shadow=True)
    c.text(1044, 152, "角色说明", 14, C["text"], True)
    c.text(1044, 184, "城市经理", 12, C["primary"], True)
    c.text(1044, 204, "只读角色，仅可查看所属城市报表；", 9, C["muted"])
    c.text(1044, 220, "无新增、修改、删除、审核权限。", 9, C["muted"])
    c.pill(1044, 242, "仅报表 · 按城市过滤", 8, C["primary"], C["blue_bg"], 8, 22)
    c.line(1044, 284, 1396, 284, C["line"], 1)

    notes = [("前台", "入住/退房、订单检索、现场改退；退款 > 500 需店长审批"),
             ("店长", "前台权限的超集，另含价格、关房、锁房、退款审批"),
             ("财务", "全集团订单与对账，可导出，不可改单"),
             ("运营", "规则、权限、异常处置；库存校正需审批")]
    yy = 302
    for role, desc in notes:
        c.text(1044, yy, role, 10, C["text"], True)
        c.lines(1044, yy + 18, desc, 8, C["muted"], spacing=3)
        yy += 60

    # 日志
    c.rrect(244, 670, 1172, 200, 14, C["card"], shadow=True)
    c.text(264, 688, "最近操作日志", 14, C["text"], True)
    c.text(1396, 694, "全部日志 >", 9, C["muted"], False, "ra")
    cols = [("时间", 180), ("操作人", 140), ("角色", 110), ("动作", 260), ("对象", 240), ("结果", 100)]
    table_head(c, 260, 716, 1140, cols, 32)
    logs = [("11-10 15:42", "张敏", "运营管理员", "修改退款审批上限", "系统规则 / 500→800", "成功"),
            ("11-10 14:18", "小林", "门店前台", "办理入住", "订单 YQ202611100018 / 1208", "成功"),
            ("11-10 11:06", "王店长", "门店店长", "关房", "外滩店 / 行政套房 / 11-20", "成功")]
    yy = 748
    for i, row in enumerate(logs):
        if i % 2 == 1:
            c.rect(260, yy, 1140, 36, "#FAFBFD")
        for j, val in enumerate(row):
            xx = 260 + sum(cols[k][1] for k in range(j))
            c.text(xx + 4, yy + 18, val, 8, C["text"] if j != 5 else C["green"], False, "lm")
        yy += 36
    c.save(path)
