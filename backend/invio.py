import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

# Use constants for configuration
INVIO_URL = os.getenv("INVIO_URL", "")
INVIO_USER = os.getenv("INVIO_USER", "")
INVIO_PASSWORD = os.getenv("INVIO_PASSWORD", "")


class Invio:
    def __init__(self):
        self.client = httpx.Client(base_url=INVIO_URL)
        self.client.headers.update({"Authorization": f"Bearer {self._get_token()}"})

    def _get_token(self) -> str:
        response = httpx.post(
            f"{INVIO_URL}/auth/login",
            json={"username": INVIO_USER, "password": INVIO_PASSWORD},
        )
        response.raise_for_status()
        return response.json()["token"]

    def get_invoice_data(self, invoice_id: str) -> dict:
        response = self.client.get(f"/invoices/{invoice_id}")
        response.raise_for_status()
        return response.json()

    def get_invoices(self) -> list:
        response = self.client.get("/invoices")
        response.raise_for_status()
        return response.json()

    def set_status_sent(self, invoice_id: str) -> dict:
        response = self.client.put(f"/invoices/{invoice_id}", json={"status": "sent"})
        response.raise_for_status()
        logging.info(response.json())
        return response.json()
    
    def set_status_paid(self, invoice_id: str) -> dict:
        response = self.client.put(f"/invoices/{invoice_id}", json={"status": "paid"})
        response.raise_for_status()
        return response.json()

    def get_customer_data(self, customer_id: str) -> dict:
        response = self.client.get(f"/customers/{customer_id}")
        response.raise_for_status()
        return response.json()

    def get_invoice_pdf(self, invoice_id: str) -> bytes:
        response = self.client.get(f"/invoices/{invoice_id}/pdf")
        response.raise_for_status()
        return response.content

    def close(self):
        self.client.close()
