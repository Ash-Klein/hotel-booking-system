"""Design tokens of the guest mini-program.

The values are copied one-to-one from the experiment-two UI specification
(``lab2/UI界面``): the palette, the 390 x 844 logical viewport, the 8px spacing
grid and the type scale. Keeping them in one module is what lets the Tkinter
screens be built against the same numbers as the mockups instead of inventing
a second, slightly different look.
"""

from __future__ import annotations

import tkinter as tk

FAMILY = "Microsoft YaHei UI"
WIDTH = 390
HEIGHT = 844
STATUS_BAR_HEIGHT = 44

COLORS = {
    # Brand and surfaces
    "primary": "#1F3A5F",
    "primary_deep": "#12263F",
    "primary_soft": "#2C5282",
    "gold": "#C9A227",
    "gold_soft": "#F7EBC8",
    "bg": "#F4F6FA",
    "card": "#FFFFFF",
    # Text
    "text": "#1B2430",
    "muted": "#6B7785",
    "faint": "#9AA5B1",
    # Lines and states
    "border": "#E3E8EF",
    "line": "#EDF1F6",
    "green": "#1E8E5A",
    "green_bg": "#E6F4EC",
    "amber": "#C77700",
    "amber_bg": "#FFF3DE",
    "red": "#C0392B",
    "red_bg": "#FDECEA",
    "blue_bg": "#E8F0FA",
    "purple": "#6B4FA1",
    "purple_bg": "#F0EAF9",
    "shadow": "#E6EAF1",
    "scrim": "#0F172A",
}

# Status colours of the seven order states, reused by every order widget.
STATUS_COLORS = {
    "PENDING_PAYMENT": COLORS["amber"],
    "CONFIRMED": COLORS["green"],
    "CHECKED_IN": COLORS["primary"],
    "CHECKED_OUT": COLORS["muted"],
    "CANCELLED": COLORS["muted"],
    "NO_SHOW": COLORS["red"],
    "EXCEPTION": COLORS["red"],
}


def setup_guest_root(root: tk.Tk) -> None:
    """Pin the point-to-pixel ratio so the 390 x 844 layout never drifts.

    Tk font sizes are expressed in points while canvas coordinates are pixels;
    the mockups are specified in pixels. Forcing 96 dpi makes one point equal
    to 4/3 px on every machine, so ``font_px`` below is exact.
    """
    root.tk.call("tk", "scaling", 96.0 / 72.0)
    root.option_add("*Font", (FAMILY, 10))


def font_px(size_px: int) -> int:
    """Convert a mockup font size in pixels to a Tk point size."""
    return max(1, int(round(size_px * 0.75)))


def blend(first: str, second: str, ratio: float) -> str:
    """Mix two ``#RRGGBB`` colours; used for hover and shadow tones."""
    a = tuple(int(first[index:index + 2], 16) for index in (1, 3, 5))
    b = tuple(int(second[index:index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(int(round(a[i] + (b[i] - a[i]) * ratio)) for i in range(3))
    return "#{:02X}{:02X}{:02X}".format(*mixed)
