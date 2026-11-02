"""Stock of the goods, in the SQLite database stock.db next to the settings
(persistent volume). Only products with a stock entry are tracked,
everything else is unlimited, so stock tracking starts per product with its
first booking.

Stock goes down when an order is placed in the order form, and when an
invoice created in Invio leaves draft (background check). It goes back up
when such an invoice gets voided."""

import asyncio
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import payments
from invio import Invio
from ntfy import send_notification

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

# An empty STOCK_DB (as in .env.example) means the default
STOCK_DB = Path(
    os.getenv("STOCK_DB")
    or os.path.join(
        os.getenv("LABEL_PATH", default="/opt/docker/invio/labels"), "stock.db"
    )
)

# Off in DEBUG, a dev instance would book the real invoices into its stock
STOCK_CHECK_INTERVAL = int(
    os.getenv("STOCK_CHECK_INTERVAL", default="0" if DEBUG else "300")
)

# Invoice statuses that count as sold, draft doesn't
COUNTED_STATUSES = {"sent", "paid", "complete", "overdue"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Tracked products, a product without a row is unlimited
CREATE TABLE IF NOT EXISTS stock (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL
);
-- Invoices whose goods were subtracted, to count them only once and to
-- return the goods when they get voided
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    number TEXT,
    source TEXT NOT NULL,
    restored INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invoice_items (
    invoice_id TEXT NOT NULL REFERENCES invoices (invoice_id),
    product_id TEXT NOT NULL,
    name TEXT,
    quantity INTEGER NOT NULL,
    PRIMARY KEY (invoice_id, product_id)
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product TEXT,
    change INTEGER NOT NULL,
    quantity INTEGER,
    reason TEXT NOT NULL,
    invoice TEXT,
    note TEXT NOT NULL DEFAULT ''
);
"""

# Orders, bookings and the background check run in the same event loop,
# the lock keeps a check and the following booking together (e.g. two
# orders for the last piece)
lock = asyncio.Lock()


class StockError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        # Text that may be shown to the user
        self.user_message = msg


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db():
    """Connection with one transaction: committed at the end, rolled back on
    an exception"""
    con = sqlite3.connect(STOCK_DB)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


def levels() -> dict[str, int]:
    """Stock of the tracked products"""
    with _db() as con:
        return {
            r["product_id"]: r["quantity"]
            for r in con.execute("SELECT product_id, quantity FROM stock")
        }


def history(limit: int = 200) -> list[dict]:
    """Stock changes, newest first"""
    with _db() as con:
        rows = con.execute(
            "SELECT at, product_id, product, change, quantity, reason, invoice, "
            "note FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]


def _since(con) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key = 'since'").fetchone()
    return row["value"] if row else None


def _change(
    con,
    product_id: str,
    name: str,
    change: int,
    reason: str,
    invoice: str | None = None,
    note: str = "",
):
    # Invoices created in Invio before the first booking don't count
    con.execute("INSERT OR IGNORE INTO meta VALUES ('since', ?)", (_now(),))
    con.execute(
        "INSERT INTO stock VALUES (?, ?, ?) ON CONFLICT (product_id) DO UPDATE "
        "SET quantity = quantity + excluded.quantity, name = excluded.name",
        (product_id, name, change),
    )
    quantity = con.execute(
        "SELECT quantity FROM stock WHERE product_id = ?", (product_id,)
    ).fetchone()["quantity"]
    con.execute(
        "INSERT INTO history (at, product_id, product, change, quantity, reason, "
        "invoice, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (_now(), product_id, name, change, quantity, reason, invoice, note),
    )


def receive(product_id: str, name: str, quantity: int, note: str = ""):
    """Book in newly arrived goods"""
    if quantity < 1:
        raise StockError("The quantity must be at least 1")
    with _db() as con:
        _change(con, product_id, name, quantity, "received", note=note)


def correct(product_id: str, name: str, quantity: int | None, note: str = ""):
    """Set the stock after counting, None stops tracking the product"""
    if quantity is not None and quantity < 0:
        raise StockError("The stock can't be negative")
    with _db() as con:
        row = con.execute(
            "SELECT quantity FROM stock WHERE product_id = ?", (product_id,)
        ).fetchone()
        if quantity is None:
            if row is not None:
                con.execute("DELETE FROM stock WHERE product_id = ?", (product_id,))
                con.execute(
                    "INSERT INTO history (at, product_id, product, change, "
                    "quantity, reason, note) VALUES (?, ?, ?, 0, NULL, "
                    "'untracked', ?)",
                    (_now(), product_id, name, note),
                )
            return
        current = row["quantity"] if row else 0
        _change(con, product_id, name, quantity - current, "corrected", note=note)


def _tracked_items(con, items: list[dict]) -> dict[str, int]:
    """Quantities per tracked product of invoice items, items without a
    product (shipping costs) and untracked products are left out"""
    tracked = {r["product_id"] for r in con.execute("SELECT product_id FROM stock")}
    quantities: dict[str, int] = {}
    for item in items:
        product_id = item.get("productId")
        if product_id in tracked:
            quantities[product_id] = quantities.get(product_id, 0) + int(
                item.get("quantity") or 0
            )
    return quantities


def check_available(items: list[dict]):
    """Raise StockError when a tracked product of an order hasn't enough
    stock. Call under lock and book with book_order before releasing it."""
    names = {i.get("productId"): i.get("description") for i in items}
    with _db() as con:
        quantities = _tracked_items(con, items)
    stock = levels()
    for product_id, quantity in quantities.items():
        if stock[product_id] < quantity:
            name = names[product_id]
            raise StockError(
                f"{name} is out of stock"
                if stock[product_id] <= 0
                else f"Only {stock[product_id]} × {name} available"
            )


def _register(con, invoice_id, number, source, quantities, names):
    con.execute(
        "INSERT INTO invoices (invoice_id, number, source) VALUES (?, ?, ?)",
        (invoice_id, number, source),
    )
    con.executemany(
        "INSERT INTO invoice_items VALUES (?, ?, ?, ?)",
        [
            (invoice_id, product_id, names.get(product_id), quantity)
            for product_id, quantity in quantities.items()
        ],
    )


def book_order(invoice: dict, items: list[dict]) -> dict[str, int]:
    """Subtract the goods of an order form order once its invoice exists, and
    remember the invoice so the background check doesn't count it again and
    returns the goods when it's voided. Returns the stock before."""
    before = levels()
    number = invoice.get("invoiceNumber")
    names = {i.get("productId"): i.get("description") for i in items}
    with _db() as con:
        quantities = _tracked_items(con, items)
        for product_id, quantity in quantities.items():
            _change(con, product_id, names[product_id], -quantity, "ordered", number)
        _register(con, invoice["id"], number, "order form", quantities, names)
    return before


async def notify_out_of_stock(before: dict[str, int]):
    """ntfy notification for products that just ran out"""
    with _db() as con:
        names = {
            r["product_id"]: r["name"]
            for r in con.execute("SELECT product_id, name FROM stock")
        }
    for product_id, quantity in levels().items():
        if quantity <= 0 < before.get(product_id, 1):
            try:
                await send_notification(
                    title=f"Out of stock: {names[product_id]}",
                    message=f"Stock is {quantity}, book in new goods in franking. "
                    "The order form doesn't offer it any more.",
                    tags=["package", "warning"],
                    priority=4,
                )
            except Exception as e:  # noqa: BLE001 - the stock is booked anyway
                logging.error(f"ntfy notification failed: {e}")


async def check_invoices() -> int:
    """Count invoices created in Invio once they leave draft, and return the
    goods of voided invoices. Returns how many invoices were booked."""
    async with lock:
        before = levels()
        if not before:
            return 0
        with _db() as con:
            since = _since(con) or _now()
            known = {
                r["invoice_id"]: dict(r)
                for r in con.execute("SELECT * FROM invoices").fetchall()
            }
        booked = 0
        async with await Invio.create() as invio:
            for i in await invio.get_invoices():
                invoice_id, status = i.get("id"), i.get("status")
                number = str(i.get("invoiceNumber"))
                registered = known.get(invoice_id)

                if status == "voided" and registered and not registered["restored"]:
                    with _db() as con:
                        rows = con.execute(
                            "SELECT * FROM invoice_items WHERE invoice_id = ?",
                            (invoice_id,),
                        ).fetchall()
                        for item in rows:
                            # Untracked meanwhile: nothing to return to
                            if item["product_id"] in before:
                                _change(
                                    con,
                                    item["product_id"],
                                    item["name"] or item["product_id"],
                                    item["quantity"],
                                    "voided",
                                    number,
                                )
                        con.execute(
                            "UPDATE invoices SET restored = 1 WHERE invoice_id = ?",
                            (invoice_id,),
                        )
                    booked += 1
                    logging.info(f"Stock of voided {number} returned")
                    continue

                if registered or status not in COUNTED_STATUSES:
                    continue
                if (i.get("createdAt") or "") < since:
                    continue
                items = (await invio.get_invoice_data(invoice_id)).get("items") or []
                names = {it.get("productId"): it.get("description") for it in items}
                with _db() as con:
                    quantities = _tracked_items(con, items)
                    for product_id, quantity in quantities.items():
                        _change(
                            con,
                            product_id,
                            names.get(product_id) or product_id,
                            -quantity,
                            "invoiced",
                            number,
                        )
                    _register(con, invoice_id, number, "invio", quantities, names)
                booked += 1
                logging.info(f"Stock of {number} (created in Invio) subtracted")
        if booked:
            payments.mark_changed()
            await notify_out_of_stock(before)
        return booked


async def stock_check_loop():
    """Background task, started with the app"""
    if STOCK_CHECK_INTERVAL <= 0:
        logging.info("Automatic stock check disabled")
        return
    logging.info(f"Automatic stock check every {STOCK_CHECK_INTERVAL} s")
    while True:
        await asyncio.sleep(STOCK_CHECK_INTERVAL)
        try:
            await check_invoices()
        except Exception as e:  # noqa: BLE001 - keep checking next time
            logging.error(f"Stock check failed: {e}")
