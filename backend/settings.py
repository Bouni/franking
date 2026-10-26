import json
import os
import textwrap
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Stored next to the labels, that folder is already a persistent volume
SETTINGS_PATH = Path(
    os.getenv(
        "SETTINGS_PATH",
        default=os.path.join(
            os.getenv("LABEL_PATH", default="/opt/docker/invio/labels"),
            "settings.json",
        ),
    )
)

TRACKING_LINK = "{tracking_link}"

# Placeholders that can be used in the tracking email, with a description
TRACKING_PLACEHOLDERS = {
    TRACKING_LINK: "Tracking link of the parcel",
    "{tracking_number}": "Tracking number",
    "{name}": "Customer name",
    "{invoice_number}": "Invoice number",
}

DEFAULTS = {
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
    pass


def load() -> dict:
    stored = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.is_file() else {}
    return {k: stored.get(k, v) for k, v in DEFAULTS.items()}


def save(data: dict) -> dict:
    settings = load()
    for key, default in DEFAULTS.items():
        if key not in data:
            continue
        if not isinstance(data[key], type(default)):
            raise SettingsError(f"{key} has the wrong type")
        settings[key] = data[key]
    if TRACKING_LINK not in settings["tracking_email_body"]:
        raise SettingsError(f"The email text must contain {TRACKING_LINK}")
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    return settings


def render(template: str, values: dict) -> str:
    """Plain replacement instead of str.format, so stray braces in the text
    don't break anything"""
    for key, value in values.items():
        template = template.replace(f"{{{key}}}", str(value or ""))
    return template
