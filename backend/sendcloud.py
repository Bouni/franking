import base64
import logging
import os

import httpx
import pycountry
from dotenv import load_dotenv

from models import Address

load_dotenv()

SENDCLOUD_URL = "https://panel.sendcloud.sc/api/v3"
SENDCLOUD_PUBLIC_KEY = os.getenv("SENDCLOUD_PUBLIC_KEY", "")
SENDCLOUD_PRIVATE_KEY = os.getenv("SENDCLOUD_PRIVATE_KEY", "")
SENDCLOUD_SENDER_ADDRESS_ID = os.getenv("SENDCLOUD_SENDER_ADDRESS_ID", "")

# DHL Kleinpaket within Germany, DHL Warenpost International Premium otherwise
SENDCLOUD_OPTION_NATIONAL = os.getenv("SENDCLOUD_OPTION_NATIONAL", "dhl_de:warenpost")
SENDCLOUD_OPTION_INTERNATIONAL = os.getenv(
    "SENDCLOUD_OPTION_INTERNATIONAL", "dhl_de:warenpostinternational/premium"
)
SENDCLOUD_DEFAULT_WEIGHT_G = int(os.getenv("SENDCLOUD_DEFAULT_WEIGHT_G", "300"))

SENDER_NAME = os.getenv("SENDER_NAME", "")
SENDER_ADDRESS = os.getenv("SENDER_ADDRESS", "")
SENDER_POSTCODE = os.getenv("SENDER_POSTCODE", "")
SENDER_CITY = os.getenv("SENDER_CITY", "")
SENDER_COUNTRY = os.getenv("SENDER_COUNTRY", "DEU")
# Required for commercial exports out of the EU
SENDER_VAT_ID = os.getenv("SENDER_VAT_ID", "")
SENDER_EORI = os.getenv("SENDER_EORI", "")

EU_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
    "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI",
    "SK",
}  # fmt: skip


def alpha_2(country: str) -> str:
    """Sendcloud wants ISO 3166-1 alpha-2 country codes"""
    if len(country) == 2:
        return country.upper()
    if c := pycountry.countries.get(alpha_3=country.upper()):
        return c.alpha_2
    raise ValueError(f"Unknown country code {country}")


def shipping_option(country_code: str) -> str:
    if alpha_2(country_code) == "DE":
        return SENDCLOUD_OPTION_NATIONAL
    return SENDCLOUD_OPTION_INTERNATIONAL


def needs_customs(country_code: str) -> bool:
    return alpha_2(country_code) not in EU_COUNTRIES


class SendcloudError(Exception):
    def __init__(self, msg: str, status_code: int | None = None):
        super().__init__(msg)
        self.status_code = status_code


class Sendcloud:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=SENDCLOUD_URL,
            auth=(SENDCLOUD_PUBLIC_KEY, SENDCLOUD_PRIVATE_KEY),
            timeout=60,
        )

    async def _post(self, path: str, payload: dict | None = None) -> dict:
        response = await self.client.post(path, json=payload)
        if response.is_error:
            logging.error(f"Sendcloud {path} failed: {response.text}")
            try:
                errors = response.json().get("errors") or []
                msg = (
                    "; ".join(
                        f"{e.get('detail', '')} ({pointer})"
                        if (pointer := (e.get("source") or {}).get("pointer"))
                        else e.get("detail", "")
                        for e in errors
                    )
                    or response.text
                )
            except ValueError:
                msg = response.text
            raise SendcloudError(msg, response.status_code)
        return response.json()

    async def quote(self, to_country: str, weight_g: int) -> dict:
        """Price of the shipping option for a country, including surcharges.
        The weight has to be passed per parcel, a top level weight is ignored
        for the price calculation."""
        code = shipping_option(to_country)
        data = await self._post(
            "/shipping-options",
            {
                "from_country_code": alpha_2(SENDER_COUNTRY),
                "to_country_code": alpha_2(to_country),
                "parcels": [{"weight": {"value": weight_g, "unit": "g"}}],
                "calculate_quotes": True,
            },
        )
        for option in data.get("data") or []:
            if option.get("code") == code and option.get("quotes"):
                total = option["quotes"][0]["price"]["total"]
                return {
                    "code": code,
                    "name": option.get("name"),
                    "price": float(total["value"]),
                    "currency": total["currency"],
                }
        raise SendcloudError(f"No price for {code} to {alpha_2(to_country)}")

    def _from_address(self) -> dict:
        if SENDCLOUD_SENDER_ADDRESS_ID:
            return {"sender_address_id": int(SENDCLOUD_SENDER_ADDRESS_ID)}
        return {
            "name": SENDER_NAME,
            "address_line_1": SENDER_ADDRESS,
            "postal_code": SENDER_POSTCODE,
            "city": SENDER_CITY,
            "country_code": alpha_2(SENDER_COUNTRY),
        }

    def _customs(self, invoice_data: dict) -> tuple[dict, list]:
        """Customs lines from the invoice items, using the product data Invio
        provides (hsCode, countryOfOrigin, weightG). Only items that have all
        of it are declared, everything else (e.g. shipping costs) is ignored."""
        fields = ("hsCode", "countryOfOrigin", "weightG")
        items = []
        for i in invoice_data.get("items", []):
            if not all(i.get(f) for f in fields):
                continue
            # Sendcloud works with whole grams, anything below ends up as 0
            if i["weightG"] < 1:
                raise SendcloudError(
                    f"Weight of '{i.get('description')}' is {i['weightG']:g} g, "
                    "set the real weight per piece in grams in Invio"
                )
            items.append(
                {
                    "description": i.get("description", "")[:50],
                    "quantity": int(i.get("quantity", 1)),
                    # Per unit, like the price
                    "weight": {"value": i["weightG"], "unit": "g"},
                    "price": {
                        "value": str(i.get("unitPrice", 0)),
                        "currency": invoice_data.get("currency", "EUR"),
                    },
                    "hs_code": str(i["hsCode"]),
                    "origin_country": alpha_2(i["countryOfOrigin"]),
                }
            )
        if not items:
            raise SendcloudError("No items with customs data on this invoice")
        if not SENDER_VAT_ID:
            raise SendcloudError("SENDER_VAT_ID is not set, required for exports")
        sender_tax = [
            {"name": "VAT", "country_code": SENDER_VAT_ID[:2], "value": SENDER_VAT_ID}
        ]
        if SENDER_EORI:
            sender_tax.append(
                {"name": "EORI", "country_code": SENDER_EORI[:2], "value": SENDER_EORI}
            )
        return {
            "invoice_number": invoice_data.get("invoiceNumber"),
            "export_reason": "commercial_goods",
            "export_type": "commercial_b2c",
            "tax_numbers": {
                "sender": sender_tax,
                "receiver": [],
                "importer_of_record": [],
            },
        }, items

    async def announce(
        self,
        invoice_data: dict,
        receiver: Address,
        shipping_option_code: str,
        weight_g: int,
    ) -> dict:
        parcel = {"weight": {"value": weight_g, "unit": "g"}}
        payload = {
            "order_number": invoice_data.get("invoiceNumber"),
            "from_address": self._from_address(),
            "to_address": {
                "name": receiver.name,
                "address_line_1": receiver.address,
                "postal_code": receiver.postcode,
                "city": receiver.city,
                "country_code": alpha_2(receiver.country),
            },
            "ship_with": {
                "type": "shipping_option_code",
                "properties": {"shipping_option_code": shipping_option_code},
            },
            "label_details": {"mime_type": "image/png", "dpi": 300},
        }
        if receiver.region:
            payload["to_address"]["state_province_code"] = receiver.region
        if receiver.phone:
            payload["to_address"]["phone_number"] = receiver.phone
        if receiver.email:
            payload["to_address"]["email"] = receiver.email
        if needs_customs(receiver.country):
            customs, items = self._customs(invoice_data)
            payload["customs_information"] = customs
            parcel["parcel_items"] = items
        payload["parcels"] = [parcel]

        data = (await self._post("/shipments/announce", payload)).get("data", {})
        p = data["parcels"][0]
        if not p.get("label_file"):
            raise SendcloudError(f"No label returned: {data.get('errors')}")
        return {
            "label": base64.b64decode(p["label_file"]),
            "shipment_id": data.get("id"),
            "parcel_id": p.get("id"),
            "carrier": (data.get("carrier") or {}).get("code"),
            "tracking_number": p.get("tracking_number"),
            "tracking_url": p.get("tracking_url"),
        }

    async def cancel(self, shipment_id: str) -> dict:
        """Returns {"status": "cancelled" | "queued", "message": ...}"""
        data = await self._post(f"/shipments/{shipment_id}/cancel")
        return data.get("data", {})

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
