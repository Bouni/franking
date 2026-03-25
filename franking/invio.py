import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

INVIO_URL = os.getenv("INVIO_URL", "")
INVIO_USER = os.getenv("INVIO_USER", "")
INVIO_PASSWORD = os.getenv("INVIO_PASSWORD", "")


class Invio:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self._get_token()}"})

    def _get_token(self) -> str:
        r = requests.post(
            f"{INVIO_URL}/auth/login",
            json={"username": INVIO_USER, "password": INVIO_PASSWORD},
        )
        token = r.json()["token"]
        return token

    def get_invoice_data(self, invoice_id: str) -> dict:
        r = self.session.get(f"{INVIO_URL}/invoices/{invoice_id}")
        r.raise_for_status()
        return r.json()

    def get_invoice_pdf(self, invoice_id: str) -> bytes:
        r = self.session.get(f"{INVIO_URL}/invoices/{invoice_id}/pdf")
        r.raise_for_status()
        return r.content
