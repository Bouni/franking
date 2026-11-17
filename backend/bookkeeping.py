"""Bookkeeping: income and expenses per year, in the SQLite database (see
db.py), and a PDF report for the tax advisor.

Income is made of the paid invoices from Invio (read from its database, not
stored here) and manual income entries. Expenses are manual entries, each
can have a receipt (PDF or image) that's kept in the label folder.

Amounts are stored in cents, gross. An invoice counts in the year it was
paid (cash basis), falling back to when it got completed or was issued."""

import io
import json
import logging
import os
import re
from datetime import UTC, date, datetime
from pathlib import Path

import anyio
from dotenv import load_dotenv
from fpdf import FPDF, FontFace
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

import db
from invio import InvioDB

load_dotenv()

RECEIPT_DIR = os.path.realpath(os.path.join(db.LABEL_PATH, "receipts"))
# Stored receipts are named after their entry, e.g. 12.pdf
RECEIPT_NAME_RE = re.compile(r"^[0-9]{1,18}\.(pdf|png|jpg)$")
RECEIPT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
MAX_RECEIPT_BYTES = 20 * 1024 * 1024

KINDS = ("income", "expense")

# Invoices with these statuses brought in money, voided ones don't
INCOME_STATUSES = {"paid", "complete"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookkeeping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    party TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    amount INTEGER NOT NULL,
    vat INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    receipt TEXT,
    receipt_name TEXT,
    created_at TEXT NOT NULL
);
"""


class BookkeepingError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        # Text that may be shown to the user
        self.user_message = msg


def _db():
    return db.connect(SCHEMA)


def _receipt_file(name: str | None) -> Path | None:
    """Path of a stored receipt. Refuse anything that isn't a receipt name
    or would leave the receipt folder, None then"""
    if not name or not RECEIPT_NAME_RE.match(name):
        return None
    path = os.path.normpath(os.path.join(RECEIPT_DIR, name))
    if not path.startswith(RECEIPT_DIR + os.sep):
        return None
    return Path(path)


def _remove_receipt_file(name: str | None):
    path = _receipt_file(name)
    if path is not None:
        path.unlink(missing_ok=True)


def _cents(value, field: str) -> int:
    try:
        cents = round(float(value) * 100)
    except (TypeError, ValueError):
        raise BookkeepingError(f"Invalid {field}") from None
    if cents < 0:
        raise BookkeepingError(f"The {field} can't be negative")
    return cents


def _clean(data: dict) -> dict:
    """Validated entry fields from a request"""
    kind = data.get("kind")
    if kind not in KINDS:
        raise BookkeepingError("Invalid kind")
    try:
        day = date.fromisoformat(str(data.get("date"))).isoformat()
    except ValueError:
        raise BookkeepingError("Invalid date") from None
    description = str(data.get("description") or "").strip()[:200]
    if not description:
        raise BookkeepingError("The description is missing")
    amount = _cents(data.get("amount"), "amount")
    if amount == 0:
        raise BookkeepingError("The amount must be more than 0")
    vat = _cents(data.get("vat") or 0, "VAT")
    if vat > amount:
        raise BookkeepingError("The VAT can't be more than the amount")
    return {
        "kind": kind,
        "date": day,
        "description": description,
        "party": str(data.get("party") or "").strip()[:200],
        "category": str(data.get("category") or "").strip()[:100],
        "amount": amount,
        "vat": vat,
        "note": str(data.get("note") or "").strip()[:500],
    }


def _entry(row) -> dict:
    e = dict(row)
    e["amount"] /= 100
    e["vat"] /= 100
    e["has_receipt"] = bool(e.pop("receipt"))
    return e


def entries(year: int) -> list[dict]:
    with _db() as con:
        rows = con.execute(
            "SELECT * FROM bookkeeping WHERE date LIKE ? ORDER BY date, id",
            (f"{year:04d}-%",),
        )
        return [_entry(r) for r in rows]


def entry_years() -> set[int]:
    with _db() as con:
        rows = con.execute("SELECT DISTINCT substr(date, 1, 4) AS y FROM bookkeeping")
        return {int(r["y"]) for r in rows}


def create(data: dict) -> dict:
    fields = _clean(data)
    with _db() as con:
        cur = con.execute(
            "INSERT INTO bookkeeping (kind, date, description, party, category, "
            "amount, vat, note, created_at) VALUES (:kind, :date, :description, "
            ":party, :category, :amount, :vat, :note, :created_at)",
            {**fields, "created_at": datetime.now(UTC).isoformat()},
        )
        return _entry(
            con.execute(
                "SELECT * FROM bookkeeping WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        )


def update(entry_id: int, data: dict) -> dict:
    fields = _clean(data)
    with _db() as con:
        cur = con.execute(
            "UPDATE bookkeeping SET kind = :kind, date = :date, "
            "description = :description, party = :party, category = :category, "
            "amount = :amount, vat = :vat, note = :note WHERE id = :id",
            {**fields, "id": entry_id},
        )
        if cur.rowcount == 0:
            raise BookkeepingError("Unknown entry")
        return _entry(
            con.execute(
                "SELECT * FROM bookkeeping WHERE id = ?", (entry_id,)
            ).fetchone()
        )


def delete(entry_id: int):
    with _db() as con:
        row = con.execute(
            "SELECT receipt FROM bookkeeping WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise BookkeepingError("Unknown entry")
        con.execute("DELETE FROM bookkeeping WHERE id = ?", (entry_id,))
    _remove_receipt_file(row["receipt"])


def receipt(entry_id: int) -> tuple[Path, str, str] | None:
    """File, media type and original name of an entry's receipt"""
    with _db() as con:
        row = con.execute(
            "SELECT receipt, receipt_name FROM bookkeeping WHERE id = ?", (entry_id,)
        ).fetchone()
    if row is None:
        return None
    path = _receipt_file(row["receipt"])
    if path is None or not path.is_file():
        return None
    return path, RECEIPT_TYPES[path.suffix], row["receipt_name"] or path.name


def _sniff(content: bytes) -> str | None:
    """File type from the content, the name and type of an upload can lie"""
    if content.startswith(b"%PDF-"):
        return ".pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    return None


def attach_receipt(entry_id: int, filename: str, content: bytes) -> dict:
    if len(content) > MAX_RECEIPT_BYTES:
        raise BookkeepingError("The receipt is larger than 20 MB")
    suffix = _sniff(content)
    if suffix is None:
        raise BookkeepingError("Receipts must be PDF, PNG or JPEG files")
    name = Path(filename or f"receipt{suffix}").name[:200]
    stored = f"{int(entry_id)}{suffix}"
    path = _receipt_file(stored)
    if path is None:
        raise BookkeepingError("Unknown entry")
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    with _db() as con:
        row = con.execute(
            "SELECT receipt FROM bookkeeping WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise BookkeepingError("Unknown entry")
        path.write_bytes(content)
        if row["receipt"] != stored:
            _remove_receipt_file(row["receipt"])
        con.execute(
            "UPDATE bookkeeping SET receipt = ?, receipt_name = ? WHERE id = ?",
            (stored, name, entry_id),
        )
        return _entry(
            con.execute(
                "SELECT * FROM bookkeeping WHERE id = ?", (entry_id,)
            ).fetchone()
        )


def remove_receipt(entry_id: int) -> dict:
    with _db() as con:
        row = con.execute(
            "SELECT receipt FROM bookkeeping WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise BookkeepingError("Unknown entry")
        con.execute(
            "UPDATE bookkeeping SET receipt = NULL, receipt_name = NULL WHERE id = ?",
            (entry_id,),
        )
        _remove_receipt_file(row["receipt"])
        return _entry(
            con.execute(
                "SELECT * FROM bookkeeping WHERE id = ?", (entry_id,)
            ).fetchone()
        )


def _nested(value):
    """Invio's nested JSON objects may come back as JSON text"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def _paid_on(invoice: dict) -> str | None:
    """Day the money came in, YYYY-MM-DD"""
    history = _nested(invoice.get("statusHistory")) or []
    for status in ("paid", "complete"):
        days = sorted(
            h["changedAt"]
            for h in history
            if h.get("status") == status and h.get("changedAt")
        )
        if days:
            return days[0][:10]
    return (invoice.get("issueDate") or "")[:10] or None


async def invoice_income() -> list[dict]:
    """Paid invoices from Invio, all years"""
    async with InvioDB() as invio_db:
        rows = await invio_db.query_invoices()
    income = []
    for r in rows:
        i = json.loads(r["invoice_json"])
        if i.get("status") not in INCOME_STATUSES:
            continue
        # Free invoices (e.g. replacements) brought in nothing
        if round(float(i.get("total") or 0), 2) == 0:
            continue
        paid_on = _paid_on(i)
        if not paid_on:
            continue
        customer = _nested(i.get("customer")) or {}
        paid = [
            h
            for h in _nested(i.get("statusHistory")) or []
            if h.get("status") == "paid" and h.get("paymentMethod")
        ]
        income.append(
            {
                "id": i.get("id"),
                "date": paid_on,
                "number": str(i.get("invoiceNumber") or ""),
                "customer": customer.get("name") or customer.get("contactName") or "",
                "amount": round(float(i.get("total") or 0), 2),
                "vat": round(float(i.get("taxAmount") or 0), 2),
                "method": paid[0]["paymentMethod"] if paid else "",
            }
        )
    income.sort(key=lambda x: (x["date"], x["number"]))
    return income


async def overview(year: int) -> dict:
    invoices = await invoice_income()
    years = entry_years() | {int(i["date"][:4]) for i in invoices}
    years.add(date.today().year)
    invoices = [i for i in invoices if i["date"].startswith(f"{year:04d}-")]
    booked = entries(year)
    income = [e for e in booked if e["kind"] == "income"]
    expenses = [e for e in booked if e["kind"] == "expense"]
    return {
        "year": year,
        "years": sorted(years, reverse=True),
        "invoices": invoices,
        "income": income,
        "expenses": expenses,
        "totals": _totals(invoices, income, expenses),
    }


def _totals(invoices, income, expenses) -> dict:
    def total(items):
        return round(sum(i["amount"] for i in items), 2)

    categories: dict[str, float] = {}
    for e in expenses:
        key = e["category"] or "Sonstiges"
        categories[key] = round(categories.get(key, 0) + e["amount"], 2)
    income_total = round(total(invoices) + total(income), 2)
    expense_total = total(expenses)
    return {
        "invoices": total(invoices),
        "other_income": total(income),
        "income": income_total,
        "expenses": expense_total,
        "expense_vat": round(sum(e["vat"] for e in expenses), 2),
        "categories": dict(sorted(categories.items())),
        "result": round(income_total - expense_total, 2),
    }


# --- PDF report ---------------------------------------------------------

# The core PDF fonts only know Latin-1
_UNSUPPORTED = re.compile(r"[^\x00-\xff]")


def _t(value) -> str:
    text = str(value or "").replace("€", "EUR").replace("–", "-").replace("—", "-")
    text = text.replace("„", '"').replace("“", '"').replace("”", '"').replace("’", "'")
    return _UNSUPPORTED.sub("?", text)


def _money(value: float) -> str:
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{text} EUR"


def _day(value: str) -> str:
    return date.fromisoformat(value).strftime("%d.%m.%Y")


class _Report(FPDF):
    def __init__(self, title: str):
        super().__init__(format="A4")
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)

    def header(self):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110)
        self.cell(0, 5, _t(self.report_title), align="L")
        self.ln(8)
        self.set_text_color(0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110)
        self.cell(0, 5, f"Seite {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0)

    def heading(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, _t(text), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)

    def grid(self, headings, rows, widths, align, total=None):
        """Table with a bold heading row and an optional bold total row"""
        bold = FontFace(emphasis="BOLD")
        self.set_font("Helvetica", "", 8.5)
        with self.table(
            col_widths=widths,
            text_align=align,
            line_height=5,
            first_row_as_headings=False,
            borders_layout="HORIZONTAL_LINES",
        ) as table:
            for cells, style in (
                [(headings, bold)]
                + [(r, None) for r in rows]
                + ([(total, bold)] if total else [])
            ):
                row = table.row()
                for c in cells:
                    row.cell(_t(c), style=style)
        self.set_font("Helvetica", "", 9)


def _report_pages(data: dict, owner: str, receipts: bool) -> bytes:
    year, totals = data["year"], data["totals"]
    title = f"Einnahmen und Ausgaben {year}" + (f" - {owner}" if owner else "")
    pdf = _Report(title)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _t(f"Einnahmen und Ausgaben {year}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if owner:
        pdf.cell(0, 6, _t(owner), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        6,
        f"Zeitraum 01.01.{year} - 31.12.{year}, erstellt am "
        f"{date.today().strftime('%d.%m.%Y')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(90)
    pdf.multi_cell(
        0,
        4.5,
        "Alle Beträge brutto. Rechnungen sind dem Jahr der Zahlung "
        "zugeordnet (Zuflussprinzip).",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(0)

    pdf.heading("Zusammenfassung")
    summary = [
        ["Einnahmen aus Rechnungen", _money(totals["invoices"])],
        ["Sonstige Einnahmen", _money(totals["other_income"])],
        ["Einnahmen gesamt", _money(totals["income"])],
    ]
    summary += [
        [f"Ausgaben: {name}", _money(amount)]
        for name, amount in totals["categories"].items()
    ]
    summary += [
        ["Ausgaben gesamt", _money(totals["expenses"])],
        [
            "Überschuss" if totals["result"] >= 0 else "Verlust",
            _money(totals["result"]),
        ],
    ]
    pdf.grid(["Position", "Betrag"], summary, (110, 70), ("LEFT", "RIGHT"))

    pdf.heading(f"Einnahmen aus Rechnungen ({len(data['invoices'])})")
    pdf.grid(
        ["Bezahlt", "Rechnung", "Kunde", "Zahlungsart", "Betrag"],
        [
            [
                _day(i["date"]),
                i["number"],
                i["customer"],
                i["method"],
                _money(i["amount"]),
            ]
            for i in data["invoices"]
        ]
        or [["", "", "Keine", "", ""]],
        (22, 25, 75, 28, 30),
        ("LEFT", "LEFT", "LEFT", "LEFT", "RIGHT"),
        total=["", "", "Summe", "", _money(totals["invoices"])],
    )

    if data["income"]:
        pdf.heading(f"Sonstige Einnahmen ({len(data['income'])})")
        pdf.grid(
            ["Datum", "Von", "Beschreibung", "Kategorie", "Betrag"],
            [
                [
                    _day(e["date"]),
                    e["party"],
                    e["description"],
                    e["category"],
                    _money(e["amount"]),
                ]
                for e in data["income"]
            ],
            (22, 40, 63, 25, 30),
            ("LEFT", "LEFT", "LEFT", "LEFT", "RIGHT"),
            total=["", "", "Summe", "", _money(totals["other_income"])],
        )

    pdf.heading(f"Ausgaben ({len(data['expenses'])})")
    pdf.grid(
        ["Beleg", "Datum", "Empfänger", "Beschreibung", "Kategorie", "USt", "Betrag"],
        [
            [
                f"A{n}" if e["has_receipt"] else "fehlt",
                _day(e["date"]),
                e["party"],
                e["description"],
                e["category"],
                _money(e["vat"]) if e["vat"] else "",
                _money(e["amount"]),
            ]
            for n, e in enumerate(data["expenses"], 1)
        ]
        or [["", "", "", "Keine", "", "", ""]],
        (12, 20, 32, 46, 24, 20, 26),
        ("LEFT", "LEFT", "LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT"),
        total=[
            "",
            "",
            "",
            "Summe",
            "",
            _money(totals["expense_vat"]),
            _money(totals["expenses"]),
        ],
    )
    if receipts and any(e["has_receipt"] for e in data["expenses"]):
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(90)
        pdf.cell(0, 5, "Die Belege A1, A2, ... folgen im Anhang.")
        pdf.set_text_color(0)
    return bytes(pdf.output())


def _stamp(label: str, width: float, height: float) -> PdfReader:
    """Page of the given size with the receipt number in the top right"""
    pdf = FPDF(unit="pt", format=(width, height))
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    w = pdf.get_string_width(label) + 12
    pdf.set_fill_color(255, 230, 120)
    pdf.set_xy(width - w - 12, 12)
    pdf.cell(w, 18, label, align="C", fill=True)
    return PdfReader(io.BytesIO(bytes(pdf.output())))


def _image_page(path: Path) -> bytes:
    """A4 page with the image, turned upright like phones show it"""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    with Image.open(path) as img:
        upright = ImageOps.exif_transpose(img)
        pdf.image(upright, x=10, y=15, w=190, h=272, keep_aspect_ratio=True)
    return bytes(pdf.output())


def _append_receipts(writer: PdfWriter, expenses: list[dict]):
    for n, e in enumerate(expenses, 1):
        found = receipt(e["id"]) if e["has_receipt"] else None
        if found is None:
            continue
        path = found[0]
        label = f"Beleg A{n}"
        try:
            if path.suffix == ".pdf":
                source = PdfReader(path)
                if source.is_encrypted:
                    source.decrypt("")
                pages = source.pages
            else:
                pages = PdfReader(io.BytesIO(_image_page(path))).pages
            for page in pages:
                added = writer.add_page(page)
                box = added.mediabox
                stamp = _stamp(label, float(box.width), float(box.height))
                added.merge_translated_page(
                    stamp.pages[0], float(box.left), float(box.bottom)
                )
        except Exception as ex:  # noqa: BLE001 - a broken receipt shouldn't stop the report
            logging.error(f"Receipt of bookkeeping entry {e['id']} skipped: {ex}")
            note = _Report(label)
            note.add_page()
            note.set_font("Helvetica", "", 11)
            note.multi_cell(
                0,
                6,
                _t(f"{label}: die Datei {found[2]} konnte nicht eingebunden werden."),
            )
            writer.append(PdfReader(io.BytesIO(bytes(note.output()))))


def _build(data: dict, receipts: bool) -> bytes:
    owner = os.getenv("SENDER_NAME", "")
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(_report_pages(data, owner, receipts))))
    if receipts:
        _append_receipts(writer, data["expenses"])
    writer.add_metadata({"/Title": f"Einnahmen und Ausgaben {data['year']}"})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


async def report(year: int, receipts: bool = True) -> bytes:
    """PDF report of a year, the receipts appended if wanted"""
    data = await overview(year)
    # Rendering and merging the receipts takes a while, keep the loop free
    return await anyio.to_thread.run_sync(_build, data, receipts)
