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


def _payment_message(payment: dict, invoice_data: dict) -> str:
    amount = float(payment.get("amount") or 0)
    message = f"{amount:.2f} EUR via {payment['method']}"
    if payment.get("name"):
        message += f" from {payment['name']}"
    total = invoice_data.get("total")
    if total is not None and abs(float(total) - amount) >= 0.01:
        message += f"\nInvoice total is {float(total):.2f} EUR"
    return message


async def run_payment_check(interactive: bool) -> dict:
    """interactive: started from the app, may wait for an S-pushTAN approval"""
    async with _lock:
        problems: list[str] = []
        payments = {}
        for t in await _fetch_paypal(problems):
            if inv := t.get("invoice"):
                payments[str(inv)] = {**t, "method": "PayPal"}
        for t in await _fetch_sparkasse(interactive, problems):
            if inv := t.get("invoice"):
                payments[str(inv)] = {**t, "method": "Bank Transfer"}

        paid_invoices = []
        async with await Invio.create() as invio:
            raw_invoices = await invio.get_invoices()
            for i in raw_invoices:
                inv_num = str(i.get("invoiceNumber"))
                if i.get("status") != "sent" or inv_num not in payments:
                    continue
                payment = payments[inv_num]
                logging.info(f"Payment found: {inv_num} via {payment['method']}")
                await invio.set_status_paid(i.get("id"), payment["method"])
                invoice_data = await invio.get_invoice_data(i.get("id"))
                invoice_data["customer"] = await invio.get_customer_data(
                    invoice_data.get("customerId")
                )
                paid_invoices.append(
                    {
                        "id": i.get("id"),
                        "invoiceNumber": i.get("invoiceNumber"),
                        "method": payment["method"],
                        "invoice_data": invoice_data,
                    }
                )
                await _notify(
                    f"Payment received: {inv_num}",
                    _payment_message(payment, invoice_data),
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
