"""Start the standalone mobile-style guest client.

The guest client is a separate program from the staff/group desktop client.
Both share the same SQLite database file, but they have independent windows,
entry points and navigation.

Usage:
    python run_guest.py
    python run_guest.py --db data/hotel.db
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="云栖酒店手机预订客户端")
    parser.add_argument(
        "--db",
        default="",
        help="SQLite 数据库路径（默认 data/hotel.db）",
    )
    return parser.parse_args()


def main() -> None:
    """Configure the database path and start the guest Tk root."""
    args = parse_args()
    if args.db:
        os.environ["HOTEL_DB_PATH"] = str(Path(args.db).resolve())
    from hotel_booking.services.app import create_services
    from hotel_booking.ui.mobile_guest import GuestApplication

    services = create_services(demo=True)
    app = GuestApplication(services)
    app.mainloop()


if __name__ == "__main__":
    main()
