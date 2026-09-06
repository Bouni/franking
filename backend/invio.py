import logging
import os

import aiosqlite
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

# Use constants for configuration
INVIO_URL = os.getenv("INVIO_URL", "")
INVIO_USER = os.getenv("INVIO_USER", "")
INVIO_PASSWORD = os.getenv("INVIO_PASSWORD", "")


# @app.get("/api/invoices")
# async def invoices():
#     async with await Invio.create() as invio:
#         raw_invoices = await invio.get_invoices()
#         invoice_ids = [
#             (i.get("id"), i.get("customerId"))
#             for i in raw_invoices
#             if i.get("status") in ("draft", "sent", "paid", "complete")
#         ]
#
#         async def fetch_full_invoice(inv_id, cust_id):
#             inv_data, cust_data = await asyncio.gather(
#                 invio.get_invoice_data(inv_id), invio.get_customer_data(cust_id)
#             )
#             inv_data["customer"] = cust_data
#
#             im = Path(LABEL_PATH) / f"{inv_data.get('invoiceNumber')}.png"
#             inv_data["internetmarke"] = im.is_file()
#             return inv_data
#
#         invoices = await asyncio.gather(
#             *[fetch_full_invoice(iid, cid) for iid, cid in invoice_ids]
#         )
#
#         invoices.sort(key=lambda x: x.get("invoiceNumber", 0), reverse=True)
#         return {"invoices": invoices}
class InvioDB:
    def __init__(self, db_path: str = "/app/invio.db"):
        self.uri = f"file:{db_path}?mode=ro"
        self._conn: aiosqlite.Connection | None = None

    async def __aenter__(self) -> "InvioDB":
        self._conn = await aiosqlite.connect(self.uri, uri=True)
        self._conn.row_factory = aiosqlite.Row
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def query_invoices(self):
        sql = """
            SELECT json_object(
           'id', i.id,
          'invoiceNumber', i.invoice_number,
          'customerId', i.customer_id,
          'issueDate', i.issue_date,
          'currency', i.currency,
          'status', i.status,
          'subtotal', i.subtotal,
          'discountAmount', i.discount_amount,
          'discountPercentage', i.discount_percentage,
          'taxRate', i.tax_rate,
          'taxAmount', i.tax_amount,
          'total', i.total,
          'paymentTerms', i.payment_terms,
          'notes', i.notes,
          'shareToken', i.share_token,
          'createdAt', i.created_at,
          'updatedAt', i.updated_at,
          'pricesIncludeTax', i.prices_include_tax,
          'roundingMode', i.rounding_mode,
          'customer', (
            SELECT json_object(
              'id', c.id,
              'name', c.name,
              'email', c.email,
              'address', c.address,
              'countryCode', c.country_code,
              'createdAt', c.created_at,
              'city', c.city,
              'postalCode', c.postal_code,
              'customerNumber', c.customer_number
            )
            FROM customers c WHERE c.id = i.customer_id
          ),
          'items', (
            SELECT json_group_array(json_object(
              'id', it.id,
              'invoiceId', it.invoice_id,
              'productId', it.product_id,
              'description', it.description,
              'quantity', it.quantity,
              'unit', it.unit,
              'unitPrice', it.unit_price,
              'lineTotal', it.line_total,
              'notes', it.notes,
              'sortOrder', it.sort_order
            ))
            FROM invoice_items it WHERE it.invoice_id = i.id
            ORDER BY it.sort_order
          ),
          'taxes', (
            SELECT json_group_array(json_object(
              'id', t.id,
              'invoiceId', t.invoice_id,
              'taxDefinitionId', t.tax_definition_id,
              'percent', t.percent,
              'taxableAmount', t.taxable_amount,
              'taxAmount', t.tax_amount
            ))
            FROM invoice_taxes t WHERE t.invoice_id = i.id
          ),
          'statusHistory', (
            SELECT json_group_array(json_object(
              'id', h.id,
              'invoiceId', h.invoice_id,
              'status', h.status,
              'changedAt', h.changed_at,
              'paymentMethod', h.payment_method
            ))
            FROM invoice_status_history h WHERE h.invoice_id = i.id
            ORDER BY h.changed_at
          )
        ) AS invoice_json
        FROM invoices i
        ORDER BY i.created_at DESC;
        """
        if self._conn is None:
            raise RuntimeError("InvioDB must be used inside 'async with'")
        async with self._conn.execute(sql) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


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

    async def get_products(self) -> dict:
        response = await self.client.get("/products")
        response.raise_for_status()
        return response.content

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
