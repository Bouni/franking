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
    def __init__(self, token: str):
        self.base_url = INVIO_URL
        # Initialize the client with the token already in the headers
        self.client = httpx.AsyncClient(
            base_url=self.base_url, headers={"Authorization": f"Bearer {token}"}
        )

    @classmethod
    async def create(cls):
        """Custom factory to handle async setup"""
        async with httpx.AsyncClient() as auth_client:
            response = await auth_client.post(
                f"{INVIO_URL}/auth/login",
                json={"username": INVIO_USER, "password": INVIO_PASSWORD},
            )
            response.raise_for_status()
            token = response.json()["token"]

        return cls(token)

    # def __init__(self):
    #     self.client = httpx.Client(base_url=INVIO_URL)
    #     self.client.headers.update({"Authorization": f"Bearer {self._get_token()}"})
    #
    # async def _get_token(self) -> str:
    #     async with httpx.AsyncClient() as auth_client:
    #         response = await auth_client.post(
    #             f"{INVIO_URL}/auth/login",
    #             json={"username": INVIO_USER, "password": INVIO_PASSWORD},
    #         )
    #         response.raise_for_status()
    #         return response.json()["token"]

    async def get_invoice_data(self, invoice_id: str) -> dict:
        response = await self.client.get(f"/invoices/{invoice_id}")
        response.raise_for_status()
        return response.json()

    async def get_invoices(self) -> list:
        response = await self.client.get("/invoices")
        response.raise_for_status()
        return response.json()

    async def set_status_sent(self, invoice_id: str) -> dict:
        response = await self.client.put(
            f"/invoices/{invoice_id}", json={"status": "sent"}
        )
        response.raise_for_status()
        return response.json()

    async def set_status_complete(self, invoice_id: str) -> dict:
        response = await self.client.put(
            f"/invoices/{invoice_id}", json={"status": "complete"}
        )
        response.raise_for_status()
        return response.json()

    async def set_status_paid(self, invoice_id: str, method: str) -> dict:
        response = await self.client.put(
            f"/invoices/{invoice_id}", json={"status": "paid", "paymentMethod": method}
        )
        response.raise_for_status()
        return response.json()

    async def get_customer_data(self, customer_id: str) -> dict:
        response = await self.client.get(f"/customers/{customer_id}")
        response.raise_for_status()
        return response.json()

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        response = await self.client.get(f"/invoices/{invoice_id}/pdf")
        response.raise_for_status()
        return response.content

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
