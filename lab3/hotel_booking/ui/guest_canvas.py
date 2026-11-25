"""Canvas toolkit for the guest mini-program.

Tkinter cannot render rounded cards, gradients or pills out of the box, so the
guest screens are drawn on a single 390 x 844 canvas with the primitives below.
Every primitive takes the pixel coordinates of the mockup and converts the font
size with :func:`guest_theme.font_px`, which keeps the implementation aligned
with the design file instead of approximating it.
"""

from __future__ import annotations

from typing import Callable, Iterable
import tkinter as tk
from tkinter import font as tkfont

from .guest_theme import COLORS, FAMILY, HEIGHT, WIDTH, blend, font_px


class MobileCanvas(tk.Canvas):
    """A canvas with the drawing vocabulary of the design system."""

    def __init__(
        self,
        master: tk.Misc,
        background: str = COLORS["bg"],
        height: int = HEIGHT,
    ) -> None:
        super().__init__(
            master,
            width=WIDTH,
            height=height,
            bg=background,
            highlightthickness=0,
            bd=0,
        )
        self.background = background
        self.min_height = height
        self._fonts: dict[tuple[int, bool], tkfont.Font] = {}
        self._click_seq = 0
        self._hover_seq = 0
        self._toast_job: str | None = None
        self.bind("<Destroy>", self._cancel_toast, add="+")

    # ------------------------------------------------------------------
    # Fonts and measuring
    # ------------------------------------------------------------------
    def font(self, size_px: int, bold: bool = False) -> tkfont.Font:
        """Return a cached Tk font for a mockup pixel size."""
        key = (size_px, bold)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(
                family=FAMILY,
                size=font_px(size_px),
                weight="bold" if bold else "normal",
            )
        return self._fonts[key]

    def measure(self, text: str, size_px: int, bold: bool = False) -> int:
        """Pixel width of a string in the design font."""
        return self.font(size_px, bold).measure(text)

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------
    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: int = 13,
        color: str = COLORS["text"],
        bold: bool = False,
        anchor: str = "nw",
        tags: tuple[str, ...] = (),
        width: int | None = None,
    ) -> int:
        """Draw one text run."""
        return self.create_text(
            x,
            y,
            text=content,
            anchor=anchor,
            fill=color,
            font=self.font(size, bold),
            tags=tags,
            width=width,
        )

    def text_right(
        self,
        right: float,
        y: float,
        content: str,
        size: int = 13,
        color: str = COLORS["text"],
        bold: bool = False,
        tags: tuple[str, ...] = (),
    ) -> int:
        """Draw one text run right-aligned to ``right``."""
        return self.text(right, y, content, size, color, bold, "ne", tags)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str = COLORS["border"],
        width: int = 1,
        tags: tuple[str, ...] = (),
        dash: tuple[int, int] | None = None,
    ) -> int:
        """Draw a straight line."""
        return self.create_line(
            x1, y1, x2, y2, fill=color, width=width, tags=tags, dash=dash
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        outline: str | None = None,
        width: int = 1,
        tags: tuple[str, ...] = (),
    ) -> int:
        """Draw a rectangle."""
        return self.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill=fill,
            outline=outline or fill,
            width=width,
            tags=tags,
        )

    def round_fill(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float,
        color: str,
        tags: tuple[str, ...] = (),
    ) -> list[int]:
        """Fill a rounded rectangle using two bars and four corner discs."""
        r = max(0.0, min(r, w / 2, h / 2))
        if r <= 0:
            return [self.rect(x, y, w, h, color, tags=tags)]
        items = [
            self.rect(x + r, y, w - 2 * r, h, color, tags=tags),
            self.rect(x, y + r, w, h - 2 * r, color, tags=tags),
        ]
        d = 2 * r
        for cx, cy in (
            (x, y),
            (x + w - d, y),
            (x, y + h - d),
            (x + w - d, y + h - d),
        ):
            items.append(
                self.create_oval(
                    cx,
                    cy,
                    cx + d,
                    cy + d,
                    fill=color,
                    outline=color,
                    width=0,
                    tags=tags,
                )
            )
        return items

    def card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float = 14,
        fill: str = COLORS["card"],
        *,
        shadow: bool = True,
        outline: str | None = None,
        width: int = 1,
        tags: tuple[str, ...] = (),
    ) -> None:
        """Draw a white card with the soft shadow of the design."""
        if shadow:
            self.round_fill(x + 1, y + 3, w - 2, h, r, COLORS["shadow"])
            self.round_fill(x, y + 1, w, h, r, blend(COLORS["shadow"], fill, 0.55))
        if outline:
            self.round_fill(x, y, w, h, r, outline, tags=tags)
            self.round_fill(
                x + width,
                y + width,
                w - 2 * width,
                h - 2 * width,
                r - width,
                fill,
                tags=tags,
            )
            return
        self.round_fill(x, y, w, h, r, fill, tags=tags)

    def gradient(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        start: str,
        end: str,
        tags: tuple[str, ...] = (),
    ) -> None:
        """Vertical gradient drawn as one-pixel rows."""
        steps = max(1, int(h))
        begin = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
        finish = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            color = "#{:02X}{:02X}{:02X}".format(
                *(
                    int(round(begin[channel] + (finish[channel] - begin[channel]) * ratio))
                    for channel in range(3)
                )
            )
            self.rect(x, y + index, w, 1.02, color, tags=tags)

    def _mask_corner(
        self,
        x: float,
        y: float,
        r: float,
        start: float,
        color: str,
        tags: tuple[str, ...] = (),
    ) -> None:
        """Round one corner of an already painted block."""
        if r <= 0:
            return
        self.create_arc(
            x,
            y,
            x + 2 * r,
            y + 2 * r,
            start=start,
            extent=90,
            style="pieslice",
            fill=color,
            outline=color,
            tags=tags,
        )

    def round_gradient(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float,
        start: str,
        end: str,
        mask: str = COLORS["card"],
        corners: str = "all",
    ) -> None:
        """Vertical gradient clipped to a rounded rectangle.

        Each row is shortened by the circle inset of the corners, which is the
        only way to get a clean rounded gradient on a Tk canvas: painting a
        rectangle and masking the corners would leave visible notches.
        """
        del mask
        radius = max(0.0, min(r, w / 2, h / 2))
        left_round = "l" in corners or corners == "all"
        right_round = "r" in corners or corners == "all"
        begin = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
        finish = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
        steps = max(1, int(round(h)))
        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            color = "#{:02X}{:02X}{:02X}".format(
                *(
                    int(round(begin[channel] + (finish[channel] - begin[channel]) * ratio))
                    for channel in range(3)
                )
            )
            dy = index + 0.5
            inset = 0.0
            if radius > 0:
                if dy < radius:
                    inset = radius - (radius * radius - (radius - dy) ** 2) ** 0.5
                elif dy > h - radius:
                    inset = radius - (radius * radius - (dy - (h - radius)) ** 2) ** 0.5
            x0 = x + (inset if left_round else 0)
            x1 = x + w - (inset if right_round else 0)
            self.create_rectangle(
                x0, y + index, x1, y + index + 1.15, fill=color, outline=color
            )

    def photo(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float = 12,
        start: str = "#8FA9C9",
        end: str = "#D9E4F2",
        mask: str = COLORS["card"],
        corners: str = "all",
        decor: bool = True,
    ) -> None:
        """Draw the placeholder room photo of the design.

        Large hero images carry the circle and two white bars; the small
        thumbnails of screens 03 and 05 are plain gradient tiles.
        """
        self.round_gradient(x, y, w, h, r, start, end, mask=mask, corners=corners)
        if not decor:
            return
        self.create_oval(
            x + w * 0.72 - h * 0.16,
            y + h * 0.28 - h * 0.16,
            x + w * 0.72 + h * 0.16,
            y + h * 0.28 + h * 0.16,
            fill="#FFFFFF",
            outline="#FFFFFF",
        )
        self.round_fill(x + w * 0.12, y + h * 0.62, w * 0.5, h * 0.1, 3, "#FFFFFF")
        self.round_fill(x + w * 0.12, y + h * 0.76, w * 0.34, h * 0.08, 3, "#FFFFFF")

    def pill(
        self,
        x: float,
        y: float,
        content: str,
        size: int = 9,
        fg: str = COLORS["primary"],
        bg: str = COLORS["blue_bg"],
        padx: float = 8,
        h: float = 18,
        bold: bool = False,
        outline: str | None = None,
    ) -> float:
        """Draw a capsule label and return its width."""
        width = self.measure(content, size, bold) + padx * 2
        if outline:
            self.round_fill(x, y, width, h, h / 2, outline)
            self.round_fill(x + 1, y + 1, width - 2, h - 2, (h - 2) / 2, bg)
        else:
            self.round_fill(x, y, width, h, h / 2, bg)
        self.text(x + width / 2, y + h / 2 + 0.5, content, size, fg, bold, "center")
        return width

    def pill_right(
        self,
        right: float,
        y: float,
        content: str,
        size: int = 9,
        fg: str = COLORS["primary"],
        bg: str = COLORS["blue_bg"],
        padx: float = 8,
        h: float = 18,
        bold: bool = False,
        outline: str | None = None,
    ) -> float:
        """Draw a capsule whose right edge is anchored at ``right``."""
        width = self.measure(content, size, bold) + padx * 2
        self.pill(right - width, y, content, size, fg, bg, padx, h, bold, outline)
        return width

    def chevron(
        self,
        x: float,
        y: float,
        size: float = 6,
        color: str = COLORS["faint"],
        width: float = 1.6,
    ) -> None:
        """Right-pointing chevron used by list rows."""
        self.create_line(
            x, y, x + size, y + size, x, y + 2 * size,
            fill=color, width=width, capstyle="round", joinstyle="round",
        )

    def star(self, x: float, y: float, size: int = 11, color: str = COLORS["gold"]) -> None:
        """Draw one rating star glyph."""
        self.text(x, y, "★", size, color)

    def button(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        command: Callable[[], None],
        *,
        size: int = 14,
        fill: str = COLORS["primary"],
        fg: str = "#FFFFFF",
        r: float = 10,
        bold: bool = True,
        enabled: bool = True,
        outline: str | None = None,
        outline_width: int = 1,
        normal_fill: str | None = None,
    ) -> None:
        """Draw a clickable button."""
        base = fill if enabled else "#AEB9C4"
        if outline:
            shape = self.round_fill(x, y, w, h, r, outline)
            inner = self.round_fill(
                x + outline_width,
                y + outline_width,
                w - 2 * outline_width,
                h - 2 * outline_width,
                r - outline_width,
                base,
            )
            items = shape + inner
        else:
            items = self.round_fill(x, y, w, h, r, base)
        label_color = fg if enabled else "#F2F4F7"
        self.text(x + w / 2, y + h / 2, label, size, label_color, bold, "center")
        if not enabled:
            return
        hover = blend(normal_fill or base, "#FFFFFF", 0.12)
        self._hover_seq += 1
        hover_tag = f"hover{self._hover_seq}"
        for item in items:
            self.addtag_withtag(hover_tag, item)
        self.tag_bind(hover_tag, "<Enter>", lambda _e: self._recolor(items, hover))
        self.tag_bind(
            hover_tag, "<Leave>", lambda _e: self._recolor(items, base)
        )
        self._click_seq += 1
        click_tag = f"click{self._click_seq}"
        for item in items:
            self.addtag_withtag(click_tag, item)
        self.tag_bind(click_tag, "<Button-1>", lambda _e: command())
        self.tag_bind(click_tag, "<Enter>", lambda _e: self.configure(cursor="hand2"))
        self.tag_bind(click_tag, "<Leave>", lambda _e: self.configure(cursor=""))

    def _recolor(self, items: Iterable[int], color: str) -> None:
        for item in items:
            self.itemconfigure(item, fill=color, outline=color)

    def link(self, items: Iterable[int], command: Callable[[], None]) -> None:
        """Make already drawn items clickable."""
        self._click_seq += 1
        tag = f"click{self._click_seq}"
        for item in items:
            self.addtag_withtag(tag, item)
        self.tag_bind(tag, "<Button-1>", lambda _e: command())
        self.tag_bind(tag, "<Enter>", lambda _e: self.configure(cursor="hand2"))
        self.tag_bind(tag, "<Leave>", lambda _e: self.configure(cursor=""))

    def bind_area(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        command: Callable[[], None],
    ) -> None:
        """Bind a transparent rectangle (used for whole-card taps)."""
        item = self.create_rectangle(
            x, y, x + w, y + h, fill="", outline="", tags=("tap",)
        )
        self.link([item], command)

    def status_bar(
        self,
        time_text: str,
        color: str = "#FFFFFF",
    ) -> None:
        """Draw the phone status bar of the mockups."""
        self.text(24, 22, time_text, 13, color, True, "w")
        for index in range(4):
            height = 4 + index * 2.4
            self.round_fill(
                300 + index * 5, 28 - height, 3, height, 1, color
            )
        for radius in (8, 5.5, 3):
            self.create_arc(
                326 - radius,
                28 - radius,
                326 + radius,
                28 + radius,
                start=225,
                extent=90,
                style="arc",
                outline=color,
                width=1.3,
            )
        self.round_fill(340, 18, 24, 11, 3, color)
        self.round_fill(365, 21.5, 2, 4, 1, color)

    def toast(self, message: str, kind: str = "info") -> None:
        """Show a transient message in the middle of the screen."""
        colors = {
            "info": COLORS["primary_deep"],
            "success": COLORS["green"],
            "error": COLORS["red"],
        }
        width = min(self.measure(message, 11) + 40, WIDTH - 40)
        x = (WIDTH - width) / 2
        y = 400.0
        group = "toast"
        self.delete(group)
        self.round_fill(
            x, y, width, 38, 19, colors.get(kind, COLORS["primary_deep"]), tags=(group,)
        )
        self.text(
            WIDTH / 2, y + 19, message, 11, "#FFFFFF", False, "center", tags=(group,)
        )
        if self._toast_job is not None:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(2400, self._clear_toast)

    def _clear_toast(self) -> None:
        """Remove the toast when its time is up; the canvas may be gone."""
        self._toast_job = None
        try:
            self.delete("toast")
        except tk.TclError:
            pass

    def _cancel_toast(self, _event: object = None) -> None:
        """Drop the pending toast timer when the canvas is destroyed."""
        if self._toast_job is not None:
            try:
                self.after_cancel(self._toast_job)
            except (tk.TclError, ValueError):
                pass
            self._toast_job = None

    def enable_scroll(self, content_height: int) -> None:
        """Allow vertical wheel scrolling for long pages."""
        region = (0, 0, WIDTH, max(content_height, self.min_height))
        self.configure(scrollregion=region)

        def on_wheel(event: tk.Event) -> None:
            self.yview_scroll(-1 * (event.delta // 120 or 1), "units")

        self.bind("<MouseWheel>", on_wheel)


class Sheet(tk.Frame):
    """Bottom panel that rises over the page without dimming it.

    The panel covers only its own area, so the screen behind stays fully
    visible. Tk canvases cannot be transparent, which is why a full-screen
    overlay was replaced by a panel anchored to the bottom edge.
    """

    def __init__(self, page: tk.Frame, title: str, height: float) -> None:
        super().__init__(page, bg=COLORS["card"])
        self.page = page
        self.title = title
        self.panel_height = height
        self.c = MobileCanvas(self, background=COLORS["card"], height=int(height))
        self.c.pack()
        self.place(x=0, y=HEIGHT - height, width=WIDTH, height=height)
        self.lift()
        self.y = 70
        self.build()

    def build(self) -> None:
        """Draw the sheet chrome; subclasses extend it."""
        self.chrome()

    def chrome(self) -> None:
        """Top border, grab handle, title and close glyph."""
        self.c.delete("all")
        self.c.line(0, 0, WIDTH, 0, COLORS["border"])
        self.c.round_fill(171, 10, 48, 4, 2, COLORS["border"])
        self.c.text(24, 30, self.title, 16, COLORS["text"], True)
        close = self.c.text(
            WIDTH - 24, 30, "✕", 15, COLORS["faint"], False, "ne"
        )
        self.c.link([close], self.close)
        self.y = 70

    def row(self, height: float = 52) -> float:
        """Reserve the next row and return its top coordinate."""
        top = self.y
        self.y += height
        return top

    def close(self) -> None:
        """Dismiss the sheet."""
        self.destroy()

    def option(
        self,
        label: str,
        command: Callable[[], None],
        *,
        detail: str = "",
        selected: bool = False,
        height: float = 52,
    ) -> None:
        """Draw one tappable option row."""
        top = self.row(height)
        if selected:
            self.c.round_fill(12, top - 2, WIDTH - 24, height - 6, 10, COLORS["blue_bg"])
        self.c.text(24, top + 8, label, 13, COLORS["text"], selected)
        if detail:
            self.c.text(24, top + 28, detail, 9, COLORS["muted"])
        if selected:
            self.c.text(WIDTH - 28, top + 14, "✓", 14, COLORS["primary"], True, "ne")
        elif detail:
            self.c.chevron(WIDTH - 32, top + 16, 6, COLORS["faint"], 1.4)
        self.c.bind_area(12, top - 2, WIDTH - 24, height - 6, command)

    def note(self, message: str, *, color: str = COLORS["muted"], height: float = 40) -> None:
        """Draw a wrapped explanatory line."""
        top = self.row(height)
        self.c.text(24, top + 4, message, 10, color, width=WIDTH - 48, anchor="nw")

    def primary(self, label: str, command: Callable[[], None], *, danger: bool = False) -> None:
        """Draw the sheet's main action at the bottom safe area."""
        y = self.panel_height - 76
        self.c.button(
            24,
            y,
            WIDTH - 48,
            44,
            label,
            command,
            size=15,
            fill=COLORS["red"] if danger else COLORS["primary"],
        )
        self.y = max(self.y, y)

    def cancel(self) -> None:
        """Draw a plain cancel action at the bottom."""
        self.primary("取消", self.close)


def show_options(
    page: tk.Frame,
    title: str,
    options: list[tuple[str, str, Callable[[], None]]],
    *,
    current: str = "",
) -> Sheet:
    """Bottom sheet listing labelled options.

    ``options`` items are ``(label, detail, command)``.
    """
    height = 70 + len(options) * 52 + 90
    sheet = Sheet(page, title, height)
    for label, detail, command in options:
        sheet.option(
            label,
            command,
            detail=detail,
            selected=label == current,
        )
    sheet.cancel()
    return sheet


def show_confirm(
    page: tk.Frame,
    title: str,
    lines: list[str],
    confirm_label: str,
    command: Callable[[], None],
    *,
    danger: bool = True,
) -> Sheet:
    """Bottom sheet with one explanatory block and a confirm action."""
    height = 70 + 28 * len(lines) + 40 + 90
    sheet = Sheet(page, title, height)
    for line in lines:
        sheet.note(line, height=28)
    sheet.primary(confirm_label, command, danger=danger)
    return sheet


class InfoPopover(tk.Frame):
    """Compact bottom panel with one value and an optional action.

    Used by "联系酒店" and "在线客服": the current screen stays visible and
    only a short panel with the phone number rises from the bottom edge.
    """

    def __init__(
        self,
        page: tk.Frame,
        title: str,
        value: str,
        subtitle: str = "",
        *,
        action_label: str = "",
        on_action: Callable[[], None] | None = None,
        value_size: int = 22,
    ) -> None:
        super().__init__(page, bg=COLORS["card"])
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.action_label = action_label
        self.on_action = on_action
        self.value_size = value_size
        self.height = 176 if action_label else 120
        self.c = MobileCanvas(self, background=COLORS["card"], height=self.height)
        self.c.pack()
        self.place(x=0, y=HEIGHT - self.height, width=WIDTH, height=self.height)
        self.lift()
        self.build()

    def build(self) -> None:
        """Draw the compact panel."""
        canvas = self.c
        canvas.line(0, 0, WIDTH, 0, COLORS["border"])
        canvas.text(24, 18, self.title, 13, COLORS["text"], True)
        close = canvas.text(WIDTH - 24, 16, "✕", 14, COLORS["faint"], False, "ne")
        canvas.link([close], self.close)
        canvas.text(24, 46, self.value, self.value_size, COLORS["primary"], True)
        if self.subtitle:
            canvas.text(24, 88, self.subtitle, 10, COLORS["muted"])
        if self.action_label and self.on_action is not None:
            canvas.button(
                24, 114, WIDTH - 48, 38,
                self.action_label, self._run, size=13,
                fill=COLORS["blue_bg"], fg=COLORS["primary"],
            )

    def _run(self) -> None:
        if self.on_action is not None:
            self.on_action()
        self.close()

    def close(self) -> None:
        """Dismiss the panel; the page underneath is untouched."""
        self.destroy()
