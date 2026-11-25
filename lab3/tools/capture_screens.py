"""Generate the screenshots used by the experiment report.

The guest client and the staff client are now two independent Tk programs, so
this development helper launches each one separately.

Usage:
    python tools/capture_screens.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import tkinter as tk

from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hotel_booking.services.app import create_services  # noqa: E402
from hotel_booking.ui.app import HotelBookingApp  # noqa: E402
from hotel_booking.ui.mobile_guest import GuestApplication  # noqa: E402

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


def grab(root: tk.Misc, name: str) -> Path:
    """Capture the client area of one Tk root."""
    root.update()
    time.sleep(0.35)
    root.update()
    x = root.winfo_rootx()
    y = root.winfo_rooty()
    width = root.winfo_width()
    height = root.winfo_height()
    path = OUTPUT / name
    ImageGrab.grab(bbox=(x, y, x + width, y + height)).save(path)
    print(f"saved {name} ({width}x{height})")
    return path


def build_guest_screens(db_path: Path) -> None:
    """Capture the portrait guest search and detail pages."""
    services = create_services(db_path, demo=True)
    app = GuestApplication(services)
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.7)
    app.update()
    search = grab(app, "02-guest-search.png")
    page = app.current_page
    page.app.show_detail(page.results[0])
    app.update()
    time.sleep(0.4)
    app.update()
    detail = grab(app, "03-room-detail.png")
    app.destroy()

    # A single composite keeps the report readable on one page.
    left = Image.open(search)
    right = Image.open(detail)
    gap = 18
    canvas = Image.new(
        "RGB", (left.width + right.width + gap, max(left.height, right.height)),
        "#E8EDF2",
    )
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + gap, 0))
    canvas.save(OUTPUT / "02-guest-flow.png")
    print("saved 02-guest-flow.png")


def build_staff_screens(db_path: Path) -> None:
    """Capture the staff and group pages."""
    services = create_services(db_path, demo=True)
    app = HotelBookingApp(services)
    app.geometry("1360x860+20+20")
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    grab(app, "01-login.png")

    app.login("manager", "Manager@123")
    app.update()
    time.sleep(3.3)  # welcome toast
    shell = app.current_portal
    shell.navigate("workbench")
    grab(app, "04-staff-workbench.png")
    shell.navigate("inventory")
    grab(app, "05-inventory.png")
    shell.navigate("orders")
    grab(app, "06-orders.png")
    shell.navigate("refunds")
    grab(app, "07-refund-approval.png")

    app.logout()
    app.login("admin", "Admin@123")
    app.update()
    time.sleep(3.3)
    admin = app.current_portal
    admin.navigate("overview")
    grab(app, "08-admin-overview.png")
    admin.navigate("reports")
    grab(app, "09-operation-report.png")
    admin.navigate("logs")
    grab(app, "10-audit-log.png")
    app.destroy()


def main() -> None:
    """Run both clients through their pages and save PNGs."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    db_path = ROOT / "data" / "demo.db"
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(db_path) + suffix)
        if path.exists():
            path.unlink()
    build_guest_screens(db_path)
    build_staff_screens(db_path)
    print(f"all screenshots saved to {OUTPUT}")


if __name__ == "__main__":
    main()
