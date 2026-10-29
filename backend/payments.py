"""Match PayPal and Sparkasse payments to sent invoices, mark them as paid and
send a ntfy notification for each one. Runs on "Update payments" and every
PAYMENT_CHECK_INTERVAL seconds in the background."""

import asyncio
import logging
import os
import unicodedata
from datetime import datetime, timezone

import anyio
from dotenv import load_dotenv

from invio import Invio
from ntfy import send_notification
from paypal import PayPal
from sparkasse import Sparkasse, TanRequired

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

# Off in DEBUG, so a dev instance doesn't mark invoices or notify as well
PAYMENT_CHECK_INTERVAL = int(
    os.getenv("PAYMENT_CHECK_INTERVAL", default="0" if DEBUG else "600")
)

# A manual and a background check must not run at the same time, both use
# the FinTS state file and change the invoice status
_lock = asyncio.Lock()

# Set when the bank wanted an S-pushTAN approval during a background check.
# Background checks then skip the Sparkasse until a manual check (where the
# approval can be given) worked, otherwise every run would push a new
# approval request to the phone.
_sparkasse_paused = False

# Goes up whenever invoices get marked as paid or a parcel's tracking status
# changes (tracking.py), open pages poll it and reload the invoice list
_changes = 0
_last_check: str | None = None


def mark_changed():
    global _changes
    _changes += 1


def status() -> dict:
    return {
        "changes": _changes,
        "last_check": _last_check,
        "sparkasse_paused": _sparkasse_paused,
    }


async def _notify(title: str, message: str, tags: list[str], priority: int):
    try:
        await send_notification(
            title=title, message=message, tags=tags, priority=priority
        )
    except Exception as e:  # noqa: BLE001 - the check itself already worked
        logging.error(f"ntfy notification failed: {e}")


async def _fetch_paypal(problems: list[str]) -> list[dict]:
    try:
        return await anyio.to_thread.run_sync(PayPal().fetch_transactions)
    except Exception as e:  # noqa: BLE001 - the Sparkasse is still checked
        logging.error(f"PayPal check failed: {e}")
        problems.append("PayPal could not be checked, see the log")
        return []


async def _fetch_sparkasse(interactive: bool, problems: list[str]) -> list[dict]:
    global _sparkasse_paused
    if not interactive and _sparkasse_paused:
        logging.info("Sparkasse check paused until the next manual check")
        return []
    try:
        transactions = await anyio.to_thread.run_sync(
            lambda: Sparkasse().fetch_transactions(wait_for_tan=interactive)
        )
    except TanRequired as e:
        logging.warning(f"Sparkasse check skipped: {e}")
        problems.append("Sparkasse not checked, the S-pushTAN approval is missing")
        if not interactive and not _sparkasse_paused:
            _sparkasse_paused = True
            await _notify(
                "Sparkasse needs approval",
                "Automatic bank transfer checks are paused. To resume, click "
                '"Update payments" in franking and approve the request in '
                "the S-pushTAN app.",
                ["warning"],
                4,
            )
        return []
    except Exception as e:  # noqa: BLE001 - PayPal is still checked
        logging.error(f"Sparkasse check failed: {e}")
        problems.append("Sparkasse could not be checked, see the log")
        return []
    if _sparkasse_paused:
        logging.info("Sparkasse check works again, resuming background checks")
    _sparkasse_paused = False
    return transactions


# Payments may be off by a cent from rounding
TOLERANCE = 0.01

# Underpaid invoices already notified about, with the amount received, so
# the next run doesn't send the same notification again
_partial_notified: dict[str, float] = {}

# Invoices already notified about an ambiguous name / email match
_ambiguous_notified: set[str] = set()


def evaluate_payments(transactions: list[dict], total: float) -> dict:
    """Add up the incoming payments for one invoice and compare them with the
    invoice total. Outgoing money (refunds) and empty amounts don't count."""
    incoming = [t for t in transactions if float(t.get("amount") or 0) > 0]
    received = round(sum(float(t["amount"]) for t in incoming), 2)
    methods = sorted({t["method"] for t in incoming})
    names = sorted({t["name"] for t in incoming if t.get("name")})
    return {
        "received": received,
        "total": total,
        "paid": bool(incoming) and received >= total - TOLERANCE,
        "difference": round(received - total, 2),
        "method": " + ".join(methods),
        "names": names,
    }


def _payment_message(result: dict) -> str:
    message = f"{result['received']:.2f} EUR via {result['method']}"
    if result["names"]:
        message += f" from {', '.join(result['names'])}"
    if result["difference"] > TOLERANCE:
        message += (
            f"\nOverpaid by {result['difference']:.2f} EUR "
            f"(invoice total {result['total']:.2f} EUR)"
        )
    return message


def _partial_message(result: dict) -> str:
    message = (
        f"{result['received']:.2f} of {result['total']:.2f} EUR received via "
        f"{result['method']}"
    )
    if result["names"]:
        message += f" from {', '.join(result['names'])}"
    return message + (
        f", {-result['difference']:.2f} EUR missing. The invoice stays open."
    )


# Words that say nothing about who paid
_NAME_NOISE = {"dr", "herr", "frau", "mr", "mrs", "ms", "und", "and", "u"}
_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def name_words(name: str | None) -> set[str]:
    """Words of a name, lowercase, umlauts written out, accents and
    punctuation removed: "MUELLER, Hans" and "Hans Müller" give the same"""
    text = unicodedata.normalize("NFKD", (name or "").lower().translate(_UMLAUTS))
    text = "".join(
        c if c.isalnum() else " " for c in text if not unicodedata.combining(c)
    )
    return {w for w in text.split() if len(w) > 1 and w not in _NAME_NOISE}


def names_match(customer_name: str | None, payer_name: str | None) -> bool:
    """All words of the shorter name appear in the other one, and at least two
    words: first and last name, a surname alone is not enough"""
    a, b = name_words(customer_name), name_words(payer_name)
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 2 and shorter <= longer


def _matched_by(invoice: dict, payment: dict) -> str | None:
    customer = invoice["customer"]
    email = (customer.get("email") or "").strip().lower()
    if email and email == (payment.get("email") or "").strip().lower():
        return "email"
    for name in (customer.get("name"), customer.get("contactName")):
        if names_match(name, payment.get("name")):
            return "name"
    return None


def match_by_customer(invoices: list[dict], payments: list[dict]) -> tuple:
    """Pair open invoices with payments that carry no invoice number. A pair
    needs the customer's email or name, exactly the invoice total and a
    payment date on or after the invoice date. It must be unambiguous: the
    payment fits no other invoice (open or already paid) and the invoice no
    other payment. Returns the matches as (invoice, payment, "email" |
    "name") and the open invoices that fit, but not unambiguously."""
    candidates = []
    for invoice in invoices:
        for payment in payments:
            if abs(float(payment.get("amount") or 0) - invoice["total"]) >= TOLERANCE:
                continue
            if (payment.get("date") or "")[:10] < invoice["issue_date"][:10]:
                continue
            if how := _matched_by(invoice, payment):
                candidates.append((invoice, payment, how))

    def count(key, obj):
        return sum(1 for c in candidates if c[key] is obj)

    matches = [
        c
        for c in candidates
        if c[0]["open"] and count(0, c[0]) == 1 and count(1, c[1]) == 1
    ]
    ambiguous = []
    for invoice, _, _ in candidates:
        if (
            invoice["open"]
            and not any(m[0] is invoice for m in matches)
            and invoice not in ambiguous
        ):
            ambiguous.append(invoice)
    return matches, ambiguous


async def run_payment_check(interactive: bool) -> dict:
    """interactive: started from the app, may wait for an S-pushTAN approval"""
    async with _lock:
        problems: list[str] = []
        payments: dict[str, list[dict]] = {}
        # Incoming payments without invoice number, matched by email or name
        unassigned: list[dict] = []
        for method, transactions in (
            ("PayPal", await _fetch_paypal(problems)),
            ("Bank Transfer", await _fetch_sparkasse(interactive, problems)),
        ):
            for t in transactions:
                if inv := t.get("invoice"):
                    payments.setdefault(str(inv), []).append({**t, "method": method})
                else:
                    unassigned.append({**t, "method": method})

        paid_invoices = []
        partial_invoices = []
        async with await Invio.create() as invio:

            async def mark_paid(invoice_id, inv_num, result, matched_by=None):
                logging.info(
                    f"Payment found: {inv_num} via {result['method']}"
                    + (f", matched by {matched_by}" if matched_by else "")
                )
                await invio.set_status_paid(invoice_id, result["method"])
                _partial_notified.pop(inv_num, None)
                invoice_data = await invio.get_invoice_data(invoice_id)
                invoice_data["customer"] = await invio.get_customer_data(
                    invoice_data.get("customerId")
                )
                paid_invoices.append(
                    {
                        "id": invoice_id,
                        "invoiceNumber": inv_num,
                        "method": result["method"],
                        "matched_by": matched_by or "invoice number",
                        "invoice_data": invoice_data,
                    }
                )
                message = _payment_message(result)
                if matched_by:
                    message += (
                        f"\nNo invoice number in the payment, matched by "
                        f"{matched_by}. Please check."
                    )
                await _notify(
                    f"Payment received: {inv_num}"
                    + (f" (matched by {matched_by})" if matched_by else ""),
                    message,
                    ["moneybag"],
                    4,
                )

            raw_invoices = await invio.get_invoices()
            for i in raw_invoices:
                inv_num = str(i.get("invoiceNumber"))
                if i.get("status") != "sent" or inv_num not in payments:
                    continue
                invoice_data = await invio.get_invoice_data(i.get("id"))
                if invoice_data.get("total") is None:
                    logging.error(f"{inv_num} has no total, payment not checked")
                    problems.append(f"{inv_num} has no total, payment not checked")
                    continue
                result = evaluate_payments(
                    payments[inv_num], float(invoice_data["total"])
                )
                if not result["received"]:
                    continue

                if not result["paid"]:
                    logging.info(
                        f"Partial payment for {inv_num}: {result['received']:.2f} "
                        f"of {result['total']:.2f} EUR, invoice stays open"
                    )
                    partial_invoices.append({"invoiceNumber": inv_num, **result})
                    if _partial_notified.get(inv_num) != result["received"]:
                        _partial_notified[inv_num] = result["received"]
                        await _notify(
                            f"Partial payment: {inv_num}",
                            _partial_message(result),
                            ["warning"],
                            4,
                        )
                    continue

                await mark_paid(i.get("id"), inv_num, result)

            # Second pass: open invoices without any invoice number payment,
            # matched by the customer's email or name. Paid and completed
            # invoices take part too, without being changed: a payment that
            # also fits one of them (e.g. marked paid by hand) is ambiguous.
            if unassigned:
                customers = {c.get("id"): c for c in await invio.get_customers()}
                paid_now = {p["invoiceNumber"] for p in paid_invoices}
                candidates = []
                for i in raw_invoices:
                    inv_num = str(i.get("invoiceNumber"))
                    customer = customers.get(i.get("customerId"))
                    if i.get("total") is None or not customer:
                        continue
                    if i.get("status") not in ("sent", "paid", "complete"):
                        continue
                    candidates.append(
                        {
                            "id": i.get("id"),
                            "number": inv_num,
                            "total": float(i["total"]),
                            "issue_date": i.get("issueDate") or "",
                            "customer": customer,
                            "open": i.get("status") == "sent"
                            and inv_num not in payments
                            and inv_num not in paid_now,
                        }
                    )
                matches, ambiguous = match_by_customer(candidates, unassigned)
                for invoice, payment, how in matches:
                    result = evaluate_payments([payment], invoice["total"])
                    await mark_paid(invoice["id"], invoice["number"], result, how)
                for invoice in ambiguous:
                    problems.append(
                        f"{invoice['number']}: more than one payment or invoice "
                        "fits by name or email, please check"
                    )
                    if invoice["number"] not in _ambiguous_notified:
                        _ambiguous_notified.add(invoice["number"])
                        await _notify(
                            f"Please check: {invoice['number']}",
                            "A payment without invoice number fits this "
                            "invoice by name or email, but not unambiguously "
                            "(several payments or invoices). It stays open.",
                            ["warning"],
                            3,
                        )

    global _last_check
    _last_check = datetime.now(timezone.utc).isoformat()
    if paid_invoices:
        mark_changed()

    return {
        "status": "success",
        "processed": len(raw_invoices),
        "paid": len(paid_invoices),
        "paid_invoices": paid_invoices,
        # Received less than the total, these stay open
        "partial_invoices": partial_invoices,
        # Shown in the app, the paid invoices above are still valid
        "problems": problems,
    }


async def payment_check_loop():
    """Background task, started with the app"""
    if PAYMENT_CHECK_INTERVAL <= 0:
        logging.info("Automatic payment check disabled")
        return
    logging.info(f"Automatic payment check every {PAYMENT_CHECK_INTERVAL} s")
    while True:
        await asyncio.sleep(PAYMENT_CHECK_INTERVAL)
        try:
            result = await run_payment_check(interactive=False)
            logging.info(f"Automatic payment check: {result['paid']} newly paid")
        except Exception as e:  # noqa: BLE001 - keep checking next time
            logging.error(f"Automatic payment check failed: {e}")
