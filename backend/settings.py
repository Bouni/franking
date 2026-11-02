"""Settings from the Settings tab, in the SQLite database (see db.py)"""

import json
import logging
import os
import textwrap
from pathlib import Path

from dotenv import load_dotenv

import db

load_dotenv()

# Before the database, the settings were stored in this file. It is imported
# on the first start and deleted afterwards
LEGACY_SETTINGS_FILE = Path(
    os.getenv("LABEL_PATH", default="/opt/docker/invio/labels"), "settings.json"
)

# One row per setting, the value is JSON encoded to keep its type
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

TRACKING_LINK = "{tracking_link}"

# Placeholders that can be used in the emails, with a description
INVOICE_PLACEHOLDERS = {
    "{name}": "Customer name",
    "{invoice_number}": "Invoice number",
}
TRACKING_PLACEHOLDERS = {
    TRACKING_LINK: "Tracking link of the parcel",
    "{tracking_number}": "Tracking number",
    **INVOICE_PLACEHOLDERS,
}

DEFAULTS = {
    "invoice_email_subject": "Invoice {invoice_number} (BSH-Board)",
    "invoice_email_body": textwrap.dedent("""
        Hi {name},

        Im Anhang findest du die Rechnung für deine Bestellung.
        Diese beinhaltet Zahlungsinformationen für Banküberweisungen und PayPal.

        Sobald ich die Zahlung erhalten habe versende ich in aller Regel am nächsten Werktag.

        Vielen Dank für die Bestellung!

        -------------------------------------------------------------------------------------

        Attached you find the invoice for your order.
        It contains payment info for bank transfer as well as for PayPal.

        As soon as I recieved the payment, I'll pack your oder and send it usually by the next work day.

        Thank you very much for your Order!

        -------------------------------------------------------------------------------------

        Bouni

        P.S. Sorry to those of you who are non german speakers, my invoicing software is limited when it comes to localization and you might get the invoice not in yor language but in german or english 😅
        """).strip(),
    "tracking_email_enabled": True,
    "tracking_email_subject": "Your order {invoice_number} has been shipped (BSH-Board)",
    "tracking_email_body": textwrap.dedent("""
        Hi {name},

        deine Bestellung ist auf dem Weg zu dir!
        Du kannst die Sendung hier verfolgen: {tracking_link}

        -------------------------------------------------------------------------------------

        Your order is on its way!
        You can track the parcel here: {tracking_link}

        -------------------------------------------------------------------------------------

        Bouni
        """).strip(),
}


class SettingsError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        # Validation text that may be shown to the user
        self.user_message = msg


def _store(con, settings: dict):
    con.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        [(k, json.dumps(v)) for k, v in settings.items()],
    )


def migrate():
    """Import the old settings file into the database and delete it"""
    if not LEGACY_SETTINGS_FILE.is_file():
        return
    stored = json.loads(LEGACY_SETTINGS_FILE.read_text())
    with db.connect(SCHEMA) as con:
        # Settings already in the database are newer than the file
        if con.execute("SELECT 1 FROM settings LIMIT 1").fetchone() is None:
            _store(con, {k: v for k, v in stored.items() if k in DEFAULTS})
            logging.info(f"Imported the settings from {LEGACY_SETTINGS_FILE}")
    # Only after the commit, a failed import keeps the file
    LEGACY_SETTINGS_FILE.unlink()
    logging.info(f"Deleted {LEGACY_SETTINGS_FILE}")


def _load(con) -> dict:
    stored = {
        r["key"]: json.loads(r["value"])
        for r in con.execute("SELECT key, value FROM settings")
    }
    return {k: stored.get(k, v) for k, v in DEFAULTS.items()}


def load() -> dict:
    with db.connect(SCHEMA) as con:
        return _load(con)


def save(data: dict) -> dict:
    with db.connect(SCHEMA) as con:
        settings = _load(con)
        for key, default in DEFAULTS.items():
            if key not in data:
                continue
            if not isinstance(data[key], type(default)):
                raise SettingsError(f"{key} has the wrong type")
            settings[key] = data[key]
        if TRACKING_LINK not in settings["tracking_email_body"]:
            raise SettingsError(f"The email text must contain {TRACKING_LINK}")
        _store(con, settings)
    return settings


def render(template: str, values: dict) -> str:
    """Plain replacement instead of str.format, so stray braces in the text
    don't break anything"""
    for key, value in values.items():
        template = template.replace(f"{{{key}}}", str(value or ""))
    return template
