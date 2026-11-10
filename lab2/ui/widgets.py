# -*- coding: utf-8 -*-
"""绘图组件：圆角卡片、阴影、渐变、文字、图标、图表。"""

from functools import lru_cache
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from theme import C, FONT_REG, FONT_BOLD


@lru_cache(maxsize=256)
def _font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


class Canvas:
    def __init__(self, w, h, scale=2, bg=C["bg"]):
        self.w, self.h, self.s = w, h, scale
        self.img = Image.new("RGB", (int(w * scale), int(h * scale)), bg)
        self.d = ImageDraw.Draw(self.img)

    # ---------- 基础 ----------
    def px(self, v):
        return int(round(v * self.s))

    def box(self, x, y, w, h):
        return [self.px(x), self.px(y), self.px(x + w), self.px(y + h)]

    def shadow(self, x, y, w, h, r=14, blur=10, alpha=26, dy=4):
        pad = blur * 2
        tile = Image.new("RGBA", (self.px(w + pad * 2), self.px(h + pad * 2)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.rounded_rectangle(
            [self.px(pad), self.px(pad), self.px(pad + w), self.px(pad + h)],
            radius=self.px(r), fill=(15, 23, 42, alpha),
        )
        tile = tile.filter(ImageFilter.GaussianBlur(self.px(blur)))
        self.img.paste((15, 23, 42), (self.px(x - pad), self.px(y - pad + dy)), tile.split()[3])

    def rrect(self, x, y, w, h, r=12, fill=C["card"], outline=None, width=1, shadow=False):
        if shadow:
            self.shadow(x, y, w, h, r)
        self.d.rounded_rectangle(
            self.box(x, y, w, h), radius=self.px(r), fill=fill,
            outline=outline, width=self.px(width) if outline else 0,
        )

    def rect(self, x, y, w, h, fill, outline=None, width=1):
        self.d.rectangle(self.box(x, y, w, h), fill=fill,
                         outline=outline, width=self.px(width) if outline else 0)

    def line(self, x1, y1, x2, y2, color=C["border"], width=1):
        self.d.line([self.px(x1), self.px(y1), self.px(x2), self.px(y2)],
                    fill=color, width=max(1, self.px(width)))

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse(
            [self.px(cx - r), self.px(cy - r), self.px(cx + r), self.px(cy + r)],
            fill=fill, outline=outline, width=self.px(width) if outline else 0,
        )

    def gradient(self, x, y, w, h, c1, c2, r=0, horizontal=False):
        n = max(2, self.px(w if horizontal else h))
        strip = Image.new("RGB", (n, 1) if horizontal else (1, n))
        a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
        for i in range(n):
            t = i / (n - 1)
            strip.putpixel((i, 0) if horizontal else (0, i),
                           tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3)))
        strip = strip.resize((self.px(w), self.px(h)))
        if r > 0:
            mask = Image.new("L", (self.px(w), self.px(h)), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, self.px(w) - 1, self.px(h) - 1], radius=self.px(r), fill=255)
            self.img.paste(strip, (self.px(x), self.px(y)), mask)
        else:
            self.img.paste(strip, (self.px(x), self.px(y)))

    # ---------- 文字 ----------
    def text(self, x, y, s, size=14, color=C["text"], bold=False, anchor="la", maxw=None):
        f = _font(self.px(size), bold)
        if maxw:
            s = self.fit(s, size, maxw, bold)
        self.d.text((self.px(x), self.px(y)), s, font=f, fill=color, anchor=anchor)

    def lines(self, x, y, s, size=13, color=C["text"], bold=False, spacing=4, anchor="la"):
        f = _font(self.px(size), bold)
        self.d.multiline_text((self.px(x), self.px(y)), s, font=f, fill=color,
                              spacing=self.px(spacing), anchor=anchor)

    def text_w(self, s, size, bold=False):
        return self.d.textlength(s, font=_font(self.px(size), bold)) / self.s

    def fit(self, s, size, maxw, bold=False):
        if self.text_w(s, size, bold) <= maxw:
            return s
        out = s
        while out and self.text_w(out + "…", size, bold) > maxw:
            out = out[:-1]
        return out + "…"

    def pill(self, x, y, s, size=11, fg=C["primary"], bg=C["blue_bg"], padx=8, h=22, bold=False, outline=None):
        w = self.text_w(s, size, bold) + padx * 2
        self.rrect(x, y, w, h, r=h / 2, fill=bg, outline=outline)
        self.text(x + w / 2, y + h / 2, s, size, fg, bold, "mm")
        return w

    # ---------- 图标 ----------
    def icon_search(self, x, y, s=18, color=C["muted"], w=1.8):
        r = s * 0.30
        cx, cy = x + s * 0.42, y + s * 0.42
        self.circle(cx, cy, r, outline=color, width=w)
        self.line(cx + r * 0.72, cy + r * 0.72, x + s * 0.92, y + s * 0.92, color, w)

    def icon_calendar(self, x, y, s=18, color=C["muted"], w=1.6):
        self.rrect(x, y + s * 0.12, s * 0.9, s * 0.8, r=2, fill=None, outline=color, width=w)
        self.line(x, y + s * 0.36, x + s * 0.9, y + s * 0.36, color, w)
        self.line(x + s * 0.25, y + s * 0.02, x + s * 0.25, y + s * 0.2, color, w)
        self.line(x + s * 0.65, y + s * 0.02, x + s * 0.65, y + s * 0.2, color, w)

    def icon_chart(self, x, y, s=18, color=C["muted"], w=1.8):
        base = y + s * 0.9
        for i, hh in enumerate([0.35, 0.6, 0.45]):
            bx = x + s * (0.08 + i * 0.3)
            self.rrect(bx, base - s * hh, s * 0.18, s * hh, r=1.5, fill=color)

    def icon_sliders(self, x, y, s=18, color=C["muted"], w=1.8):
        for i, yy in enumerate([0.2, 0.5, 0.8]):
            self.line(x, y + s * yy, x + s, y + s * yy, color, w)
            cx = x + s * ([0.35, 0.65, 0.45][i])
            self.circle(cx, y + s * yy, s * 0.1, fill=C["card"], outline=color, width=w)

    def icon_user(self, x, y, s=18, color=C["muted"], w=1.8):
        self.circle(x + s * 0.5, y + s * 0.32, s * 0.18, outline=color, width=w)
        self.d.arc([self.px(x + s * 0.18), self.px(y + s * 0.52),
                    self.px(x + s * 0.82), self.px(y + s * 1.1)],
                   start=200, end=340, fill=color, width=self.px(w))

    def icon_home(self, x, y, s=18, color=C["muted"], w=1.8):
        self.d.line([self.px(x), self.px(y + s * 0.45), self.px(x + s * 0.5), self.px(y),
                     self.px(x + s), self.px(y + s * 0.45)], fill=color, width=self.px(w))
        self.d.line([self.px(x + s * 0.15), self.px(y + s * 0.42),
                     self.px(x + s * 0.15), self.px(y + s), self.px(x + s * 0.85), self.px(y + s),
                     self.px(x + s * 0.85), self.px(y + s * 0.42)], fill=color, width=self.px(w))

    def icon_bell(self, x, y, s=18, color=C["muted"], w=1.6):
        self.d.arc([self.px(x + s * 0.22), self.px(y + s * 0.15),
                    self.px(x + s * 0.78), self.px(y + s * 0.8)],
                   start=180, end=360, fill=color, width=self.px(w))
        self.line(x + s * 0.18, y + s * 0.68, x + s * 0.82, y + s * 0.68, color, w)
        self.circle(x + s * 0.5, y + s * 0.86, s * 0.06, fill=color)

    def icon_back(self, x, y, s=18, color=C["text"], w=2):
        self.d.line([self.px(x + s * 0.6), self.px(y + s * 0.2),
                     self.px(x + s * 0.25), self.px(y + s * 0.5),
                     self.px(x + s * 0.6), self.px(y + s * 0.8)], fill=color, width=self.px(w))

    def chevron_down(self, x, y, s=8, color=C["muted"], w=1.6):
        self.d.line([self.px(x), self.px(y), self.px(x + s / 2), self.px(y + s / 2),
                     self.px(x + s), self.px(y)], fill=color, width=self.px(w))

    def icon_star(self, x, y, s=12, color=C["gold"]):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = s * (0.5 if i % 2 == 0 else 0.21)
            pts.append((self.px(x + s / 2 + r * math.cos(ang)), self.px(y + s / 2 + r * math.sin(ang))))
        self.d.polygon(pts, fill=color)

    # ---------- 组件 ----------
    def avatar(self, x, y, s=36, name="林", bg=C["blue_bg"], fg=C["primary"]):
        self.circle(x + s / 2, y + s / 2, s / 2, fill=bg)
        self.text(x + s / 2, y + s / 2, name, s * 0.4, fg, True, "mm")

    def button(self, x, y, w, h, label, size=14, bg=C["primary"], fg="#FFFFFF", r=10, bold=True, outline=None):
        self.rrect(x, y, w, h, r=r, fill=bg, outline=outline)
        self.text(x + w / 2, y + h / 2, label, size, fg, bold, "mm")

    def status_bar(self, dark=False):
        fg = "#FFFFFF" if dark else C["text"]
        self.text(24, 22, "9:41", 13, fg, True, "lm")
        # 信号
        for i in range(4):
            hh = 4 + i * 2.4
            self.rrect(300 + i * 5, 28 - hh, 3, hh, r=1, fill=fg)
        # wifi
        for rr in (9, 6, 3):
            self.d.arc([self.px(326 - rr), self.px(29 - rr), self.px(326 + rr), self.px(29 + rr)],
                       start=225, end=315, fill=fg, width=self.px(1.6))
        # 电池
        self.rrect(340, 18, 24, 11, r=3, fill=None, outline=fg, width=1.2)
        self.rrect(342, 20, 17, 7, r=1.5, fill=fg)
        self.rrect(365, 21.5, 2, 4, r=1, fill=fg)

    def tab_bar(self, active=0):
        self.rect(0, 782, 390, 62, "#FFFFFF")
        self.line(0, 782, 390, 782, C["border"], 1)
        items = [("首页", "home"), ("订单", "list"), ("我的", "user")]
        for i, (label, icon) in enumerate(items):
            cx = 65 + i * 130
            col = C["primary"] if i == active else C["faint"]
            if icon == "home":
                self.icon_home(cx - 10, 797, 20, col)
            elif icon == "list":
                for k in range(3):
                    self.line(cx - 9, 800 + k * 6, cx + 9, 800 + k * 6, col, 1.8)
                    self.circle(cx - 12, 800 + k * 6, 1.2, fill=col)
            else:
                self.icon_user(cx - 10, 795, 20, col)
            self.text(cx, 825, label, 10, col, i == active, "mm")

    def bar_chart(self, x, y, w, h, values, labels, color=C["primary"], maxv=None, fmt="{:.0f}"):
        maxv = maxv or max(values) * 1.15
        self.line(x, y + h, x + w, y + h, C["border"], 1)
        for g in range(1, 4):
            gy = y + h - h * g / 4
            self.line(x, gy, x + w, gy, C["line"], 1)
        n = len(values)
        slot = w / n
        bw = slot * 0.46
        for i, v in enumerate(values):
            bh = h * v / maxv
            bx = x + slot * i + (slot - bw) / 2
            self.rrect(bx, y + h - bh, bw, bh, r=3, fill=color)
            self.text(bx + bw / 2, y + h - bh - 7, fmt.format(v), 9, C["muted"], False, "ms")
            self.text(bx + bw / 2, y + h + 8, labels[i], 9, C["faint"], False, "ma")

    def save(self, path):
        self.img.save(path, "PNG", optimize=True)
