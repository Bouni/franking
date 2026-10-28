"""Match PayPal and Sparkasse payments to sent invoices, mark them as paid and
send a ntfy notification for each one. Runs on "Update payments" and every
PAYMENT_CHECK_INTERVAL seconds in the background."""

import asyncio
import logging
import os
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

# Goes up whenever invoices get marked as paid, open pages poll it and reload
# the invoice list when it changed
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


async def run_payment_check(interactive: bool) -> dict:
    """interactive: started from the app, may wait for an S-pushTAN approval"""
    async with _lock:
        problems: list[str] = []
        payments: dict[str, list[dict]] = {}
        for t in await _fetch_paypal(problems):
            if inv := t.get("invoice"):
                payments.setdefault(str(inv), []).append({**t, "method": "PayPal"})
        for t in await _fetch_sparkasse(interactive, problems):
            if inv := t.get("invoice"):
                payments.setdefault(str(inv), []).append(
                    {**t, "method": "Bank Transfer"}
                )

        paid_invoices = []
        partial_invoices = []
        async with await Invio.create() as invio:
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

                logging.info(f"Payment found: {inv_num} via {result['method']}")
                await invio.set_status_paid(i.get("id"), result["method"])
                _partial_notified.pop(inv_num, None)
                invoice_data = await invio.get_invoice_data(i.get("id"))
                invoice_data["customer"] = await invio.get_customer_data(
                    invoice_data.get("customerId")
                )
                paid_invoices.append(
                    {
                        "id": i.get("id"),
                        "invoiceNumber": i.get("invoiceNumber"),
                        "method": result["method"],
                        "invoice_data": invoice_data,
                    }
                )
                await _notify(
                    f"Payment received: {inv_num}",
                    _payment_message(result),
                    ["moneybag"],
                    4,
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
