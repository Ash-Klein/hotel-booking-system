"""Start the hotel staff/group desktop client.

The guest client is a separate program; run ``python run_guest.py`` for the
portrait mobile-style booking application.

Usage:
    python run.py
    python run.py --db data/hotel.db
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="云栖酒店运营工作台")
    parser.add_argument(
        "--db",
        default="",
        help="SQLite 数据库路径（默认 data/hotel.db）",
    )
    return parser.parse_args()


def main() -> None:
    """Configure the database path and start Tk."""
    args = parse_args()
    if args.db:
        os.environ["HOTEL_DB_PATH"] = str(Path(args.db).resolve())
    from hotel_booking.ui.app import HotelBookingApp
    from hotel_booking.services.app import create_services

    services = create_services(demo=True)
    app = HotelBookingApp(services)
    app.mainloop()


if __name__ == "__main__":
    main()
