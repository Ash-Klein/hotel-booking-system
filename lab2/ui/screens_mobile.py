# -*- coding: utf-8 -*-
"""客人端 5 屏（390×844，2x）。"""

from theme import C
from widgets import Canvas

# 一单一房型：本流程演示同房型 2 间、2 晚，总价 = 单价 × 晚数 × 间数
NIGHTS = 2
ROOMS = 2
RATE = 568
TOTAL = RATE * NIGHTS * ROOMS


def photo(c, x, y, w, h, r=12, c1="#8FA9C9", c2="#D9E4F2"):
    c.gradient(x, y, w, h, c1, c2, r=r)
    c.circle(x + w * 0.72, y + h * 0.28, h * 0.16, fill="#FFFFFF")
    c.circle(x + w * 0.72, y + h * 0.28, h * 0.16, outline="#FFFFFF", width=1)
    c.rrect(x + w * 0.12, y + h * 0.62, w * 0.5, h * 0.1, r=3, fill="#FFFFFF")
    c.rrect(x + w * 0.12, y + h * 0.76, w * 0.34, h * 0.08, r=3, fill="#FFFFFF")


def header(c, h=300, title=""):
    c.gradient(0, 0, 390, h, C["primary"], C["primary_soft"])
    c.status_bar(dark=True)


def screen01(path):
    c = Canvas(390, 844, 2)
    header(c, 280)
    c.text(24, 60, "云栖酒店 · YUNQI", 11, "#C9D6E7", True)
    c.text(24, 82, "挑一家", 27, "#FFFFFF", True)
    c.text(24, 116, "想住的酒店", 27, "#FFFFFF", True)
    c.text(24, 158, "上海 · 6 家门店 · 实时房态", 11, "#B9C9DC")

    # 选店卡
    x, y, w = 20, 180, 350
    c.rrect(x, y, w, 224, 16, C["card"], shadow=True)
    c.text(38, 198, "上海", 18, C["text"], True)
    c.d.line([c.px(82), c.px(207), c.px(88), c.px(213), c.px(94), c.px(207)],
             fill=C["muted"], width=c.px(1.6))
    c.text(332, 200, "2 晚 · 2 位", 10, C["muted"], False, "ra")

    c.line(38, 232, 352, 232, C["line"], 1)
    c.text(38, 246, "入住门店", 9, C["faint"])
    c.text(38, 262, "云栖酒店 · 外滩店", 14, C["text"], True)
    c.text(352, 264, "更换", 10, C["primary"], False, "ra")

    c.line(38, 292, 352, 292, C["line"], 1)
    c.text(38, 306, "入住", 9, C["faint"])
    c.text(38, 320, "11月14日", 14, C["text"], True)
    c.text(38, 340, "周六", 9, C["muted"])
    c.text(176, 318, "→", 14, C["faint"])
    c.text(204, 306, "离店", 9, C["faint"])
    c.text(204, 320, "11月16日", 14, C["text"], True)
    c.text(204, 340, "周一", 9, C["muted"])

    c.button(38, 356, 314, 40, "查看房型", 14, C["primary"], "#FFFFFF", 10)

    # 该店房型推荐
    c.text(20, 430, "外滩店 · 房型推荐", 15, C["text"], True)
    c.text(370, 434, "共 5 种房型", 9, C["muted"], False, "ra")

    rooms = [
        ("高级大床房", "28㎡ · 1.8m 大床 · 含早", "568", "仅剩 3 间", "#8FA9C9", "#D9E4F2"),
        ("高级双床房", "30㎡ · 1.2m 双床 · 含早", "528", "仅剩 5 间", "#A9B8C9", "#E6EEF7"),
        ("行政套房", "46㎡ · 1.8m 大床 · 含双早", "898", "仅剩 1 间", "#9BB0C9", "#DCE6F2"),
    ]
    yy = 456
    for name, desc, price, left, c1, c2 in rooms:
        c.rrect(20, yy, 350, 96, 12, C["card"], shadow=True)
        photo(c, 20, yy, 76, 96, 12, c1, c2)
        c.text(108, yy + 16, name, 13, C["text"], True)
        c.text(108, yy + 38, desc, 9, C["muted"], maxw=180)
        c.pill(108, yy + 62, left, 9, C["amber"], C["amber_bg"], 6, 18)
        c.text(344, yy + 20, "¥" + price, 15, C["red"], True, "ra")
        c.text(344, yy + 42, "起 / 晚", 8, C["muted"], False, "ra")
        yy += 106

    c.tab_bar(0)
    c.save(path)


def chevron(c, x, y, s=6, color=C["faint"], w=1.6):
    c.d.line([c.px(x), c.px(y), c.px(x + s), c.px(y + s), c.px(x), c.px(y + 2 * s)],
             fill=color, width=c.px(w))


def screen02(path):
    """房型列表：只选房型，不选间数、不显示总价。"""
    c = Canvas(390, 844, 2)
    header(c, 168)
    c.icon_back(20, 52, 20, "#FFFFFF")
    c.text(195, 62, "云栖酒店 · 外滩店", 17, "#FFFFFF", True, "ma")
    c.text(195, 88, "上海 · 黄浦区中山东一路 18 号", 10, "#C9D6E7", False, "ma")
    for i in range(5):
        c.icon_star(171 + i * 13, 108, 11, C["gold"])
    c.text(242, 108, "4.8 / 5", 10, "#E8D9A8")

    # 日期条：只确认日期，间数留到 02A
    c.rrect(16, 146, 358, 56, 12, C["card"], shadow=True)
    c.text(30, 160, "11月14日 周六", 12, C["text"], True)
    c.text(180, 164, "→", 14, C["faint"])
    c.text(206, 160, "11月16日 周一", 12, C["text"], True)
    c.text(30, 180, f"{NIGHTS} 晚", 10, C["muted"])
    c.text(344, 170, "修改", 11, C["primary"], False, "ra")

    chips = ["含早", "大床", "可取消"]
    xx = 16
    for i, s in enumerate(chips):
        ww = c.pill(xx, 218, s, 10, C["primary"], C["blue_bg"], 9, 24)
        xx += ww + 8
    c.text(370, 226, "3 种房型", 10, C["muted"], False, "ra")

    # 房型卡：整卡可点，进入 02A 详情
    rooms = [
        ("高级大床房", "28㎡ · 1.8m 大床 · 含早", "568", "仅剩 3 间", "可取消", "#8FA9C9", "#D9E4F2"),
        ("高级双床房", "30㎡ · 1.2m 双床 · 含早", "528", "仅剩 5 间", "可取消", "#A9B8C9", "#E6EEF7"),
        ("行政套房", "46㎡ · 1.8m 大床 · 含双早", "898", "仅剩 1 间", "可取消", "#9BB0C9", "#DCE6F2"),
    ]
    yy = 258
    for name, desc, price, left, tag, c1, c2 in rooms:
        c.rrect(16, yy, 358, 160, 14, C["card"], shadow=True)
        photo(c, 16, yy, 100, 160, 14, c1, c2)
        c.text(132, yy + 14, name, 16, C["text"], True)
        c.text(132, yy + 40, desc, 10, C["muted"], maxw=210)
        c.pill(132, yy + 60, left, 9, C["amber"], C["amber_bg"], 6, 18)
        c.pill(132 + c.text_w(left, 9) + 16, yy + 60, tag, 9, C["green"], C["green_bg"], 6, 18)
        c.text(132, yy + 94, "¥", 10, C["red"])
        c.text(142, yy + 86, price, 22, C["red"], True)
        c.text(142 + c.text_w(price, 22, True) + 4, yy + 97, "起/晚", 9, C["muted"])
        chevron(c, 350, yy + 74)
        yy += 176

    c.text(195, 796, "价格为每晚起价，点选房型查看详情", 9, C["faint"], False, "ma")
    c.save(path)


def screen02a(path):
    """房型详情：定间数、看明细、确认下单。"""
    c = Canvas(390, 844, 2)
    c.gradient(0, 0, 390, 96, C["primary"], C["primary_soft"])
    c.status_bar(dark=True)
    c.icon_back(20, 52, 20, "#FFFFFF")
    c.text(195, 62, "房型详情", 17, "#FFFFFF", True, "ma")

    photo(c, 0, 96, 390, 180, 0, "#8FA9C9", "#D9E4F2")
    c.pill(308, 240, "28㎡", 9, C["text"], "#FFFFFF", 7, 20)

    c.rect(0, 276, 390, 506, "#FFFFFF")
    c.text(24, 288, "高级大床房", 22, C["text"], True)
    c.text(24, 322, "1.8m 大床 · 含早 · 可取消", 10, C["muted"])
    c.text(24, 346, "¥", 12, C["red"])
    c.text(34, 338, "568", 30, C["red"], True)
    c.text(34 + c.text_w("568", 30, True) + 4, 354, "/晚", 10, C["muted"])
    c.pill(300, 344, "仅剩 3 间", 9, C["amber"], C["amber_bg"], 6, 20)

    c.line(16, 384, 374, 384, C["line"], 1)
    c.text(24, 396, "入住日期", 9, C["faint"])
    c.text(24, 412, "11月14日 - 11月16日 · 2 晚", 13, C["text"], True)
    c.text(344, 398, "修改", 10, C["primary"], False, "ra")

    c.line(16, 446, 374, 446, C["line"], 1)
    c.text(24, 458, "间数", 13, C["text"], True)
    c.text(24, 480, "最多 3 间", 9, C["muted"])
    bx = 256
    for i, (lab, fill, fg) in enumerate(
        [("−", C["card"], C["primary"]), (str(ROOMS), C["card"], C["text"]), ("+", C["blue_bg"], C["primary"])]
    ):
        c.rrect(bx + i * 34, 454, 32, 32, 8, fill,
                outline=C["primary"] if i == 2 else C["border"], width=1.2)
        c.text(bx + i * 34 + 16, 470, lab, 14, fg, True, "mm")

    # 价格明细
    c.rrect(16, 520, 358, 118, 12, C["bg"])
    c.text(32, 534, "价格明细", 12, C["text"], True)
    c.text(32, 560, f"房费（¥{RATE} × {NIGHTS} 晚 × {ROOMS} 间）", 10, C["muted"])
    c.text(358, 560, f"¥{TOTAL}", 10, C["text"], False, "ra")
    c.text(32, 582, "服务费", 10, C["muted"])
    c.text(358, 582, "¥0", 10, C["text"], False, "ra")
    c.line(32, 600, 358, 600, C["border"], 1)
    c.text(32, 608, "合计", 11, C["text"], True)
    c.text(358, 604, f"¥{TOTAL}", 18, C["red"], True, "ra")

    # 预订须知
    c.rrect(16, 654, 358, 86, 12, C["blue_bg"])
    c.text(32, 668, "预订须知", 11, C["primary"], True)
    c.text(32, 686, "入住 14:00 后 · 退房次日 12:00 前", 9, C["muted"])
    c.text(32, 702, "入住前 24 小时可免费取消，之后扣首晚房费", 9, C["muted"])
    c.text(32, 720, "需要其他房型？请分开下单", 9, C["amber"])

    c.rect(0, 782, 390, 62, "#FFFFFF")
    c.line(0, 782, 390, 782, C["border"], 1)
    c.text(20, 790, "合计", 9, C["muted"])
    c.text(20, 804, f"¥{TOTAL}", 20, C["red"], True)
    c.button(220, 794, 150, 42, "确认下单", 14, C["primary"], "#FFFFFF", 10)
    c.save(path)


def screen03(path):
    c = Canvas(390, 844, 2)
    c.gradient(0, 0, 390, 108, C["primary"], C["primary_soft"])
    c.status_bar(dark=True)
    c.icon_back(20, 52, 20, "#FFFFFF")
    c.text(195, 62, "填写订单", 17, "#FFFFFF", True, "ma")
    c.pill(300, 50, "14:32", 11, "#FFFFFF", "#3A5A82", 10, 24, True, outline="#8FA6C4")

    c.rect(0, 108, 390, 46, C["gold_soft"])
    c.text(20, 121, "房源已为你锁定，14:32 后自动释放", 11, "#8A6A12")
    c.text(370, 121, "倒计时", 10, "#8A6A12", False, "ra")

    # 入住人
    c.rrect(16, 170, 358, 232, 14, C["card"], shadow=True)
    c.text(32, 188, "入住人信息", 14, C["text"], True)
    c.text(358, 190, f"{ROOMS} 间房", 10, C["muted"], False, "ra")
    fields = [("姓名", "黄若希"), ("手机号", "138****0053"), ("到店时间", "预计 18:00 前")]
    yy = 218
    for label, value in fields:
        c.text(32, yy, label, 10, C["faint"])
        c.text(32, yy + 16, value, 13, C["text"])
        c.line(32, yy + 44, 358, yy + 44, C["line"], 1)
        yy += 50
    c.text(32, 376, "+ 添加入住人（还需 1 位）", 11, C["primary"])

    # 订单信息
    c.rrect(16, 418, 358, 236, 14, C["card"], shadow=True)
    c.text(32, 436, "订单信息", 14, C["text"], True)
    c.gradient(32, 460, 56, 56, "#8FA9C9", "#D9E4F2", 8)
    c.text(100, 464, "高级大床房", 13, C["text"], True)
    c.text(100, 484, "11月14日 - 11月16日 · 2 晚", 10, C["muted"])
    c.text(100, 500, f"含早 · 可取消 · {ROOMS} 间", 10, C["muted"])
    c.line(32, 528, 358, 528, C["line"], 1)
    rows = [(f"房费（{NIGHTS} 晚 × {ROOMS} 间）", f"¥{TOTAL}"), ("服务费", "¥0"), ("优惠", "-¥0")]
    yy = 540
    for k, v in rows:
        c.text(32, yy, k, 11, C["muted"])
        c.text(358, yy, v, 11, C["text"], False, "ra")
        yy += 22
    c.line(32, 606, 358, 606, C["line"], 1)
    c.text(32, 620, "应付总额", 12, C["text"], True)
    c.text(358, 614, f"¥{TOTAL}", 18, C["red"], True, "ra")

    # 预订须知
    c.rrect(16, 670, 358, 84, 12, C["blue_bg"])
    c.text(32, 684, "预订须知", 11, C["primary"], True)
    c.text(32, 704, "入住 14:00 后 · 退房次日 12:00 前", 9, C["muted"])
    c.text(32, 720, "免费取消以订单取消规则为准", 9, C["muted"])
    c.text(32, 736, "到店请出示入住人身份证件", 9, C["muted"])

    # 底部
    c.rect(0, 770, 390, 74, "#FFFFFF")
    c.line(0, 770, 390, 770, C["border"], 1)
    c.text(20, 786, f"¥{TOTAL}", 20, C["red"], True)
    c.text(20, 810, "含税总价", 9, C["muted"])
    c.button(220, 784, 150, 44, "去支付", 15, C["primary"], "#FFFFFF", 10)
    c.save(path)


def screen04(path):
    c = Canvas(390, 844, 2)
    c.gradient(0, 0, 390, 110, C["primary"], C["primary_soft"])
    c.status_bar(dark=True)
    c.icon_back(20, 52, 20, "#FFFFFF")
    c.text(195, 62, "收银台", 17, "#FFFFFF", True, "ma")
    c.pill(300, 50, "14:06", 11, "#FFFFFF", "#3A5A82", 10, 24, True, outline="#8FA6C4")

    # 金额
    c.rrect(16, 128, 358, 104, 14, C["card"], shadow=True)
    c.text(32, 146, "待支付金额", 11, C["muted"])
    c.text(32, 164, f"¥{TOTAL}", 30, C["red"], True)
    c.text(32, 202, f"订单号 YQ202611100018 · {NIGHTS} 晚 {ROOMS} 间", 10, C["muted"])

    # 支付方式
    c.text(20, 254, "选择支付方式", 14, C["text"], True)
    methods = [("微信支付", "推荐使用", True), ("支付宝", "", False), ("银行卡", "储蓄卡 / 信用卡", False)]
    yy = 282
    for name, desc, active in methods:
        c.rrect(16, yy, 358, 64, 12, C["card"], outline=C["primary"] if active else C["border"], width=1.5)
        c.circle(42, yy + 32, 15, fill=C["green_bg"] if name == "微信支付" else C["blue_bg"])
        c.text(42, yy + 32, name[0], 13, C["green"] if name == "微信支付" else C["primary"], True, "mm")
        c.text(66, yy + 18, name, 13, C["text"], True)
        if desc:
            c.text(66, yy + 38, desc, 9, C["muted"])
        c.circle(342, yy + 32, 9, fill=None, outline=C["primary"] if active else C["border"], width=1.4)
        if active:
            c.circle(342, yy + 32, 4.5, fill=C["primary"])
        yy += 76

    c.rrect(16, 522, 358, 56, 12, C["blue_bg"])
    c.text(32, 536, "支付安全", 11, C["primary"], True)
    c.text(32, 552, "支付由持牌机构处理，云栖不留存银行卡信息", 9, C["muted"])

    # 订单摘要
    c.rrect(16, 594, 358, 150, 14, C["card"], shadow=True)
    c.text(32, 610, "订单摘要", 12, C["text"], True)
    c.text(358, 612, f"{NIGHTS} 晚 {ROOMS} 间", 9, C["muted"], False, "ra")
    c.text(32, 636, "高级大床房 · 含早", 11, C["text"])
    c.text(32, 658, "11月14日 - 11月16日", 10, C["muted"])
    c.text(32, 680, "入住人 黄若希", 10, C["muted"])
    c.line(32, 702, 358, 702, C["line"], 1)
    c.text(32, 714, "房费合计", 10, C["muted"])
    c.text(358, 712, f"¥{TOTAL}", 16, C["red"], True, "ra")

    c.rect(0, 770, 390, 74, "#FFFFFF")
    c.line(0, 770, 390, 770, C["border"], 1)
    c.text(20, 786, "实付", 10, C["muted"])
    c.text(20, 800, f"¥{TOTAL}", 20, C["red"], True)
    c.button(220, 784, 150, 44, "确认支付", 15, C["primary"], "#FFFFFF", 10)
    c.save(path)


def screen05(path):
    c = Canvas(390, 844, 2)
    c.gradient(0, 0, 390, 160, C["primary"], C["primary_soft"])
    c.status_bar(dark=True)
    c.icon_back(20, 52, 20, "#FFFFFF")
    c.text(195, 62, "订单详情", 17, "#FFFFFF", True, "ma")

    c.rrect(16, 120, 358, 132, 14, C["card"], shadow=True)
    c.text(32, 138, "已确认待入住", 16, C["green"], True)
    c.pill(260, 136, f"{NIGHTS} 晚 {ROOMS} 间", 9, C["primary"], C["blue_bg"], 7, 20)
    c.text(32, 168, "订单号 YQ202611100018", 10, C["muted"])
    c.text(32, 190, "11月14日 - 11月16日", 14, C["text"], True)
    c.text(32, 216, "云栖酒店 · 外滩店", 11, C["muted"])

    c.rrect(16, 268, 358, 142, 14, C["card"], shadow=True)
    c.gradient(32, 286, 72, 72, "#8FA9C9", "#D9E4F2", 8)
    c.text(116, 288, f"高级大床房 · {ROOMS} 间", 13, C["text"], True)
    c.text(116, 310, "28㎡ · 1.8m 大床 · 含早", 10, C["muted"])
    c.text(116, 330, "入住人：黄若希", 10, C["muted"])
    c.text(116, 348, "到店时间：预计 18:00 前", 10, C["muted"])
    c.text(32, 380, f"¥{TOTAL}", 16, C["red"], True)
    c.text(88, 386, "已支付", 9, C["green"])

    # 时间轴
    c.text(20, 432, "订单进度", 13, C["text"], True)
    steps = [("提交订单", "11-10 14:20", True), ("支付成功", "11-10 14:22", True), ("等待入住", "11-14 14:00 后", False)]
    yy = 462
    for i, (name, time, done) in enumerate(steps):
        c.circle(32, yy + 6, 5, fill=C["green"] if done else C["border"])
        if i < len(steps) - 1:
            c.line(32, yy + 12, 32, yy + 40, C["border"], 1.5)
        c.text(48, yy, name, 11, C["text"], done)
        c.text(48, yy + 18, time, 9, C["muted"])
        yy += 44

    c.rrect(16, 594, 358, 104, 14, C["amber_bg"])
    c.text(32, 610, "取消规则", 11, C["amber"], True)
    c.text(32, 630, "入住前 24 小时可免费取消；", 10, "#7A5A10")
    c.text(32, 648, f"24 小时内取消扣首晚房费 ¥{RATE * ROOMS}（{ROOMS} 间）。", 10, "#7A5A10")
    c.text(32, 668, "特殊日期（节假日/展会）按专属规则。", 9, "#8A6A12")

    c.rrect(16, 714, 172, 42, 10, "#FFFFFF", outline=C["border"])
    c.text(102, 735, "修改订单", 13, C["primary"], True, "mm")
    c.rrect(202, 714, 172, 42, 10, "#FFFFFF", outline=C["red"])
    c.text(288, 735, "取消订单", 13, C["red"], True, "mm")

    c.rrect(16, 772, 172, 40, 10, C["blue_bg"])
    c.text(102, 792, "联系酒店", 12, C["primary"], True, "mm")
    c.rrect(202, 772, 172, 40, 10, C["blue_bg"])
    c.text(288, 792, "在线客服", 12, C["primary"], True, "mm")
    c.save(path)
