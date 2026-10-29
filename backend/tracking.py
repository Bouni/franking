"""Shipment status of the Sendcloud parcels. Every TRACKING_CHECK_INTERVAL
seconds the tracking of all parcels that are not delivered yet is fetched,
the latest status is stored in the label metadata (shown in the app) and a
ntfy notification is sent when it changed."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import payments
from ntfy import send_notification
from sendcloud import Sendcloud

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

# Off in DEBUG, a dev instance would notify about the real parcels as well
TRACKING_CHECK_INTERVAL = int(
    os.getenv("TRACKING_CHECK_INTERVAL", default="0" if DEBUG else "300")
)

LABEL_DIR = Path(os.getenv("LABEL_PATH", default="/opt/docker/invio/labels"))

# Parcels in these phases don't change any more
FINAL_PHASES = {"delivered", "cancelled", "returned_to_sender"}

# Older parcels are not checked any more, even if never delivered
MAX_AGE_DAYS = 60


def latest_status(tracking: dict) -> dict | None:
    """The most recent event, the parcel's current status"""
    events = tracking.get("events") or []
    if not events:
        return None
    event = max(events, key=lambda e: e.get("event_at") or "")
    return {
        "description": event.get("description") or "",
        "phase": event.get("phase") or "none",
        "status_type": event.get("status_type") or "success",
        "event_at": event.get("event_at"),
        "expected_delivery_date": (tracking.get("details") or {}).get(
            "expected_delivery_date"
        ),
    }


def _open_parcels() -> list[tuple[Path, dict]]:
    """Label metadata of the Sendcloud parcels that may still change"""
    parcels = []
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    for meta_file in LABEL_DIR.glob("*.json"):
        label_png = meta_file.with_suffix(".png")
        # Only labels: not settings.json, not cancelled ones (renamed to
        # INV-….cancelled.json / .png)
        if meta_file.name.endswith(".cancelled.json") or not label_png.is_file():
            continue
        if label_png.stat().st_mtime < cutoff:
            continue
        try:
            meta = json.loads(meta_file.read_text())
        except (OSError, ValueError):
            continue
        if not meta.get("tracking_number") or meta.get("carrier") == "debug":
            continue
        if (meta.get("tracking") or {}).get("phase") in FINAL_PHASES:
            continue
        parcels.append((meta_file, meta))
    return parcels


def _notification(invoice_number: str, status: dict, meta: dict) -> dict:
    lines = [status["description"]]
    if status.get("expected_delivery_date"):
        lines.append(f"Expected delivery: {status['expected_delivery_date']}")
    if meta.get("tracking_url"):
        lines.append(meta["tracking_url"])
    if status["phase"] == "delivered":
        tags, priority = ["white_check_mark"], 4
    elif status["status_type"] == "error":
        tags, priority = ["rotating_light"], 5
    elif status["status_type"] == "warning":
        tags, priority = ["warning"], 4
    else:
        tags, priority = ["truck"], 3
    return {
        "title": f"{invoice_number}: {status['description']}",
        "message": "\n".join(lines),
        "tags": tags,
        "priority": priority,
    }


async def check_parcels() -> int:
    """Fetch the tracking of all open parcels, returns how many changed"""
    changed = 0
    parcels = _open_parcels()
    if not parcels:
        return 0
    async with Sendcloud() as sc:
        for meta_file, meta in parcels:
            invoice_number = meta_file.stem
            try:
                status = latest_status(await sc.tracking(meta["tracking_number"]))
            except Exception as e:  # noqa: BLE001 - check the other parcels
                logging.warning(f"Tracking of {invoice_number} failed: {e}")
                continue
            if status is None:
                continue
            previous = meta.get("tracking")
            status["checked_at"] = datetime.now(timezone.utc).isoformat()
            # The label may have been changed meanwhile (cancelled, printed)
            try:
                current = json.loads(meta_file.read_text())
            except (OSError, ValueError):
                continue
            current["tracking"] = status
            meta_file.write_text(json.dumps(current))

            # Carriers repeat events, only a new description is a change. The
            # first status of a parcel is stored without a notification, so
            # existing parcels don't all notify at once.
            if previous is None or previous.get("description") == status["description"]:
                continue
            changed += 1
            logging.info(f"Tracking of {invoice_number}: {status['description']}")
            try:
                await send_notification(
                    **_notification(invoice_number, status, current)
                )
            except Exception as e:  # noqa: BLE001 - the status is stored anyway
                logging.error(f"ntfy notification failed: {e}")
    if changed:
        payments.mark_changed()
    return changed


async def tracking_check_loop():
    """Background task, started with the app"""
    if TRACKING_CHECK_INTERVAL <= 0:
        logging.info("Automatic tracking check disabled")
        return
    logging.info(f"Automatic tracking check every {TRACKING_CHECK_INTERVAL} s")
    # First check right away, so the app shows the statuses after a restart
    while True:
        try:
            changed = await check_parcels()
            if changed:
                logging.info(f"Tracking check: {changed} parcels changed")
        except Exception as e:  # noqa: BLE001 - keep checking next time
            logging.error(f"Tracking check failed: {e}")
        await asyncio.sleep(TRACKING_CHECK_INTERVAL)
