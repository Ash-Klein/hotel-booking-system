"""Reusable Tkinter widgets used by all three portals."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .theme import COLORS


def clear_children(widget: tk.Misc) -> None:
    """Destroy every child of a container."""
    for child in widget.winfo_children():
        child.destroy()


def make_field(
    parent: tk.Misc,
    label: str,
    variable: tk.Variable,
    row: int,
    column: int = 0,
    *,
    width: int = 22,
    show: str | None = None,
    values: list[str] | None = None,
    background: str | None = None,
) -> tk.Widget:
    """Create a label + entry/combobox pair in a grid cell."""
    bg = background or COLORS["card"]
    holder = tk.Frame(parent, bg=bg)
    holder.grid(row=row, column=column, sticky="ew", padx=6, pady=5)
    tk.Label(
        holder,
        text=label,
        bg=bg,
        fg=COLORS["muted"],
        font=("Microsoft YaHei UI", 9),
        anchor="w",
    ).pack(fill="x")
    if values:
        widget: tk.Widget = ttk.Combobox(
            holder,
            textvariable=variable,
            values=values,
            state="readonly",
            width=width,
        )
    else:
        widget = ttk.Entry(holder, textvariable=variable, width=width)
        if show:
            widget.configure(show=show)  # type: ignore[call-arg]
    widget.pack(fill="x", pady=(3, 0))
    parent.grid_columnconfigure(column, weight=1)
    return widget


class Card(tk.Frame):
    """A white rounded-looking surface with a soft border."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        padding: int = 16,
        background: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=background or COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            bd=0,
        )
        self.inner = tk.Frame(self, bg=background or COLORS["card"])
        self.inner.pack(fill="both", expand=True, padx=padding, pady=padding)


class StatCard(Card):
    """Dashboard metric card."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        value: str,
        hint: str = "",
        color: str = COLORS["blue"],
    ) -> None:
        super().__init__(parent, padding=14)
        strip = tk.Frame(self.inner, bg=color, height=4)
        strip.pack(fill="x", pady=(0, 10))
        self.title_label = tk.Label(
            self.inner,
            text=title,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.title_label.pack(fill="x")
        self.value_label = tk.Label(
            self.inner,
            text=value,
            bg=COLORS["card"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 22, "bold"),
            anchor="w",
        )
        self.value_label.pack(fill="x", pady=(2, 2))
        self.hint_label = tk.Label(
            self.inner,
            text=hint,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        )
        self.hint_label.pack(fill="x")

    def update_value(self, value: str, hint: str | None = None) -> None:
        """Update the displayed metric without rebuilding the card."""
        self.value_label.configure(text=value)
        if hint is not None:
            self.hint_label.configure(text=hint)


class PageHeader(tk.Frame):
    """Consistent page title block with an optional right-side action area."""

    def __init__(
        self, parent: tk.Misc, title: str, subtitle: str = ""
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        text_holder = tk.Frame(self, bg=COLORS["bg"])
        text_holder.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_holder,
            text=title,
            bg=COLORS["bg"],
            fg=COLORS["navy"],
            font=("Microsoft YaHei UI", 20, "bold"),
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            tk.Label(
                text_holder,
                text=subtitle,
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 9),
                anchor="w",
            ).pack(fill="x", pady=(4, 0))
        self.actions = tk.Frame(self, bg=COLORS["bg"])
        self.actions.pack(side="right", anchor="e")


class DataTable(tk.Frame):
    """Treeview wrapper that keeps row dictionaries keyed by item id."""

    def __init__(
        self,
        parent: tk.Misc,
        columns: list[tuple[str, str, int]],
        *,
        height: int = 10,
        on_double: Callable[[dict[str, object]], None] | None = None,
        on_select: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=COLORS["card"])
        self.columns = columns
        self._rows: dict[str, dict[str, object]] = {}
        keys = [item[0] for item in columns]
        self.tree = ttk.Treeview(
            self,
            columns=keys,
            show="headings",
            height=height,
            selectmode="browse",
        )
        for key, label, width in columns:
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=width, minwidth=max(width // 2, 50),
                             anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.tree.yview
        )
        horizontal = ttk.Scrollbar(
            self, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=horizontal.set,
        )
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tree.tag_configure("ok", foreground=COLORS["green"])
        self.tree.tag_configure("warn", foreground=COLORS["orange"])
        self.tree.tag_configure("bad", foreground=COLORS["red"])
        self.tree.tag_configure("muted", foreground=COLORS["muted"])
        self.tree.tag_configure("alt", background="#FAFBFD")
        if on_double:
            self.tree.bind("<Double-1>", lambda _: self._invoke(on_double))
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _: self._invoke(on_select))

    def _invoke(
        self, callback: Callable[[dict[str, object]], None]
    ) -> None:
        row = self.selected_row()
        if row is not None:
            callback(row)

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        """Replace all rows."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows.clear()
        for index, row in enumerate(rows):
            values = [row.get(key, "") for key, _, _ in self.columns]
            tag = str(row.get("_tag", ""))
            tags = [tag] if tag else []
            if index % 2 == 1:
                tags.append("alt")
            item = self.tree.insert(
                "", "end", values=values, tags=tuple(tags)
            )
            self._rows[item] = row

    def selected_row(self) -> dict[str, object] | None:
        """Return the selected row dictionary, if any."""
        selection = self.tree.selection()
        if not selection:
            return None
        return self._rows.get(selection[0])

    def select_first(self) -> None:
        """Select the first row for keyboard-friendly screens."""
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])

    def clear(self) -> None:
        """Remove every row."""
        self.set_rows([])


class ScrollableFrame(tk.Frame):
    """A vertically scrollable frame for long forms and report pages."""

    def __init__(self, parent: tk.Misc, bg: str | None = None) -> None:
        super().__init__(parent, bg=bg or COLORS["bg"])
        self.canvas = tk.Canvas(
            self,
            bg=bg or COLORS["bg"],
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=bg or COLORS["bg"])
        self._window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


class Toast:
    """Transient bottom-right notification."""

    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.label: tk.Label | None = None
        self._after_id: str | None = None

    def show(self, message: str, kind: str = "info") -> None:
        """Show a message for 3.2 seconds."""
        if self._after_id:
            self.root.after_cancel(self._after_id)
        if self.label:
            self.label.destroy()
        color = {
            "info": COLORS["navy"],
            "success": COLORS["green"],
            "error": COLORS["red"],
        }.get(kind, COLORS["navy"])
        self.label = tk.Label(
            self.root,
            text=message,
            bg=color,
            fg=COLORS["white"],
            font=("Microsoft YaHei UI", 10),
            padx=18,
            pady=10,
        )
        self.label.place(relx=0.98, rely=0.96, anchor="se")
        self.label.lift()
        self._after_id = self.root.after(3200, self._hide)

    def _hide(self) -> None:
        if self.label:
            self.label.destroy()
            self.label = None
        self._after_id = None


class ModalDialog(tk.Toplevel):
    """Base modal with a body, error line and action footer."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        *,
        width: int = 560,
        height: int = 560,
        submit_text: str = "确定",
        on_submit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.configure(bg=COLORS["card"])
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self._on_submit = on_submit
        self.error_var = tk.StringVar()
        header = tk.Frame(self, bg=COLORS["navy"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text=title,
            bg=COLORS["navy"],
            fg=COLORS["white"],
            font=("Microsoft YaHei UI", 15, "bold"),
            anchor="w",
        ).pack(side="left", padx=22, pady=16)
        self.body = tk.Frame(self, bg=COLORS["card"])
        self.body.pack(fill="both", expand=True, padx=22, pady=16)
        error_label = tk.Label(
            self.body,
            textvariable=self.error_var,
            bg=COLORS["card"],
            fg=COLORS["red"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            wraplength=width - 50,
        )
        error_label.pack(side="bottom", fill="x", pady=(8, 0))
        if on_submit:
            footer = tk.Frame(self, bg=COLORS["bg"], height=64)
            footer.pack(fill="x", side="bottom")
            footer.pack_propagate(False)
            ttk.Button(
                footer,
                text="取消",
                style="Secondary.TButton",
                command=self.destroy,
            ).pack(side="right", padx=(8, 20), pady=14)
            ttk.Button(
                footer,
                text=submit_text,
                command=self._submit,
            ).pack(side="right", pady=14)
        self.bind("<Escape>", lambda _: self.destroy())
        self.update_idletasks()
        self._center(parent)

    def _center(self, parent: tk.Misc) -> None:
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _submit(self) -> None:
        if self._on_submit:
            try:
                self._on_submit()
            except Exception as exc:  # noqa: BLE001 - user-facing boundary
                self.error_var.set(str(exc))

    def close(self) -> None:
        """Close dialog after a successful operation."""
        self.grab_release()
        self.destroy()


def confirm(parent: tk.Misc, title: str, message: str) -> bool:
    """Yes/no confirmation."""
    return messagebox.askyesno(title, message, parent=parent)


def show_error(parent: tk.Misc, message: str, title: str = "操作失败") -> None:
    """Uniform error dialog."""
    messagebox.showerror(title, message, parent=parent)


def show_info(parent: tk.Misc, message: str, title: str = "提示") -> None:
    """Uniform information dialog."""
    messagebox.showinfo(title, message, parent=parent)


def separator(parent: tk.Misc) -> tk.Frame:
    """Thin horizontal rule."""
    line = tk.Frame(parent, bg=COLORS["line"], height=1)
    line.pack(fill="x", pady=8)
    return line
