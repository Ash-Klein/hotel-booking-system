"""Application shell and portal routing."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from .. import config
from ..domain.enums import Role
from ..domain.models import Staff
from ..services.app import Services
from .theme import COLORS, configure_styles
from .widgets import Toast


class HotelBookingApp(tk.Tk):
    """Top-level window; owns the session and swaps portals."""

    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
        self.current_staff: Staff | None = None
        self.current_portal: object | None = None
        self.font_family = configure_styles(self)
        self.title(config.APP_NAME)
        self.geometry(config.WINDOW_SIZE)
        self.minsize(*config.MIN_WINDOW_SIZE)
        self.configure(bg=COLORS["bg"])
        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)
        self.toast = Toast(self)
        self.status_var = tk.StringVar()
        status = tk.Label(
            self,
            textvariable=self.status_var,
            bg=COLORS["line"],
            fg=COLORS["muted"],
            anchor="e",
            padx=12,
            pady=3,
            font=(self.font_family, 8),
        )
        status.pack(side="bottom", fill="x")
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_login()

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def _clear(self) -> None:
        if self.current_portal and hasattr(self.current_portal, "destroy"):
            try:
                self.current_portal.destroy()  # type: ignore[attr-defined]
            except tk.TclError:
                pass
        self.current_portal = None

    def show_login(self) -> None:
        """Display the staff login screen."""
        from .login_view import LoginView

        self._clear()
        self.current_staff = None
        self.current_portal = LoginView(self.container, self)
        self.current_portal.pack(fill="both", expand=True)

    def show_guest(self, tab: str = "search") -> None:
        """Display the guest-facing portal."""
        from .guest_view import GuestPortal

        self._clear()
        self.current_staff = None
        self.current_portal = GuestPortal(self.container, self, tab)
        self.current_portal.pack(fill="both", expand=True)

    def login(self, username: str, password: str) -> Staff:
        """Authenticate and route to the correct back-office portal."""
        staff = self.services.auth.login(username, password)
        self.current_staff = staff
        self._clear()
        if staff.role.is_group_level:
            from .admin_view import AdminShell

            self.current_portal = AdminShell(self.container, self)
        else:
            from .staff_view import StaffShell

            self.current_portal = StaffShell(self.container, self)
        self.current_portal.pack(fill="both", expand=True)  # type: ignore[union-attr]
        self.toast.show(f"欢迎回来，{staff.name}", "success")
        return staff

    def logout(self) -> None:
        """End the session and return to login."""
        self.current_staff = None
        self.show_login()

    def notify(self, message: str, kind: str = "info") -> None:
        """Show a transient notification from any child view."""
        self.toast.show(message, kind)

    def open_guest_orders(self, phone: str = "") -> None:
        """Switch the guest portal to the order lookup tab."""
        if self.current_portal and hasattr(self.current_portal, "show_orders"):
            self.current_portal.show_orders(phone)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        now = datetime.now()
        weekdays = "一二三四五六日"
        self.status_var.set(
            f"{now:%Y-%m-%d %H:%M:%S}  星期{weekdays[now.weekday()]}  ·  "
            f"云栖酒店集团 · v{config.APP_VERSION}"
        )
        self.after(1000, self._tick)


def main() -> None:
    """Create the service graph and start the Tk main loop."""
    services = build_services()
    app = HotelBookingApp(services)
    app.mainloop()


def build_services():  # type: ignore[no-untyped-def]
    """Import the composition root lazily to keep module import cheap."""
    from ..services.app import create_services

    return create_services()


__all__ = ["HotelBookingApp", "main"]
