"""Generate the screenshots used by the experiment report.

Development helper only. It needs Pillow, which the course's bundled Python
environment provides; the application itself has no third-party dependency.

Usage:
    python tools/capture_screens.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import tkinter as tk

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hotel_booking.services.app import create_services  # noqa: E402
from hotel_booking.ui.app import HotelBookingApp  # noqa: E402

OUTPUT = ROOT / "report" / "screenshots"


def toplevels(widget: tk.Misc) -> list[tk.Toplevel]:
    """Find Toplevel dialogs recursively."""
    result: list[tk.Toplevel] = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Toplevel):
            result.append(child)
        else:
            result.extend(toplevels(child))
    return result


def main() -> None:
    """Run the app through its main pages and save one PNG per page."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    db_path = ROOT / "data" / "demo.db"
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(db_path) + suffix)
        if path.exists():
            path.unlink()
    services = create_services(db_path, demo=True)
    app = HotelBookingApp(services)
    app.geometry("1360x860+20+20")
    app.attributes("-topmost", True)
    app.lift()
    app.update()

    def settle(seconds: float = 0.45) -> None:
        app.update()
        time.sleep(seconds)
        app.update()

    def grab(name: str) -> None:
        settle(0.35)
        x = app.winfo_rootx()
        y = app.winfo_rooty()
        width = app.winfo_width()
        height = app.winfo_height()
        image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        image.save(OUTPUT / name)
        print(f"saved {name}")

    settle(0.5)
    grab("01-login.png")

    app.show_guest()
    settle(0.9)
    grab("02-guest-search.png")
    view = app.current_portal.search_view
    view.table.select_first()
    view.open_detail()
    settle(0.4)
    grab("03-room-detail.png")
    for dialog in toplevels(app):
        dialog.destroy()
    app.update()

    app.login("manager", "Manager@123")
    settle(3.5)  # allow the welcome toast to disappear
    shell = app.current_portal
    shell.navigate("workbench")
    settle()
    grab("04-staff-workbench.png")
    shell.navigate("inventory")
    settle()
    grab("05-inventory.png")
    shell.navigate("orders")
    settle()
    grab("06-orders.png")
    shell.navigate("refunds")
    settle()
    grab("07-refund-approval.png")

    app.logout()
    app.login("admin", "Admin@123")
    settle(3.5)
    admin = app.current_portal
    admin.navigate("overview")
    settle()
    grab("08-admin-overview.png")
    admin.navigate("reports")
    settle()
    grab("09-operation-report.png")
    admin.navigate("logs")
    settle()
    grab("10-audit-log.png")
    app.destroy()
    print(f"all screenshots saved to {OUTPUT}")


if __name__ == "__main__":
    main()
