import base64
import logging
import math
import os
import re
from datetime import UTC, datetime

import httpx
import pycountry
from dotenv import load_dotenv

from models import Address

load_dotenv()

SENDCLOUD_URL = "https://panel.sendcloud.sc/api/v3"
# Invoices with their paid flag are only listed by the v2 API
SENDCLOUD_INVOICES_URL = "https://panel.sendcloud.sc/api/v2/user/invoices"
SENDCLOUD_PUBLIC_KEY = os.getenv("SENDCLOUD_PUBLIC_KEY", "")
SENDCLOUD_PRIVATE_KEY = os.getenv("SENDCLOUD_PRIVATE_KEY", "")
SENDCLOUD_SENDER_ADDRESS_ID = os.getenv("SENDCLOUD_SENDER_ADDRESS_ID", "")

# DHL Kleinpaket within Germany, DHL Warenpost International Premium otherwise
SENDCLOUD_OPTION_NATIONAL = os.getenv("SENDCLOUD_OPTION_NATIONAL", "dhl_de:warenpost")
SENDCLOUD_OPTION_INTERNATIONAL = os.getenv(
    "SENDCLOUD_OPTION_INTERNATIONAL", "dhl_de:warenpostinternational/premium"
)
# Envelope and bubble wrap: 6 boards, 12 3-pin and 6 4-pin connectors (54 g of
# goods according to Invio) weighed 73 g ready to ship
SENDCLOUD_PACKAGING_G = int(os.getenv("SENDCLOUD_PACKAGING_G", "19"))
# DHL Warenpost is priced in 100 g steps (0-100 g, 101-200 g, ... up to 1 kg)
SENDCLOUD_WEIGHT_STEP_G = int(os.getenv("SENDCLOUD_WEIGHT_STEP_G", "100"))

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


# French overseas territories have French postcodes, but DHL and Sendcloud
# treat them as countries of their own, and they are outside the EU VAT area
# (customs declaration needed). Saint-Barthélemy and Saint-Martin share the
# 971 prefix with Guadeloupe and have one postcode each.
FRENCH_OVERSEAS_POSTCODES = {"97133": "BL", "97150": "MF"}
FRENCH_OVERSEAS_PREFIXES = {
    "971": "GP", "972": "MQ", "973": "GF", "974": "RE", "975": "PM",
    "976": "YT", "986": "WF", "987": "PF", "988": "NC",
}  # fmt: skip


def destination(country_code: str, postcode: str = "") -> str:
    """Alpha-2 code of the country the parcel actually goes to, the overseas
    territory for French addresses with an overseas postcode"""
    country = alpha_2(country_code)
    if country != "FR":
        return country
    code = re.sub(r"\s", "", postcode or "")
    return FRENCH_OVERSEAS_POSTCODES.get(code) or FRENCH_OVERSEAS_PREFIXES.get(
        code[:3], country
    )


def shipping_option(country_code: str) -> str:
    if alpha_2(country_code) == "DE":
        return SENDCLOUD_OPTION_NATIONAL
    return SENDCLOUD_OPTION_INTERNATIONAL


CUSTOMS_FIELDS = ("hsCode", "countryOfOrigin", "weightG")
CUSTOMS_FIELD_NAMES = {
    "hsCode": "HS code",
    "countryOfOrigin": "country of origin",
    "weightG": "weight",
}


def apply_product_data(invoice_data: dict, products: list[dict]) -> dict:
    """Invio copies the customs data into the invoice items when the invoice
    is created, and issued invoices can't be changed any more. Customs data
    is product data, so the current product values win, the item copy is
    only the fallback (e.g. for products that no longer exist)."""
    by_id = {p.get("id"): p for p in products}
    for item in invoice_data.get("items", []):
        product = by_id.get(item.get("productId"))
        if not product:
            continue
        for field in CUSTOMS_FIELDS:
            if product.get(field):
                item[field] = product[field]
    return invoice_data


def label_weight(goods_g: float) -> tuple[float, int]:
    """Estimated parcel weight (goods plus packaging) and the weight the label
    is bought for: the estimate rounded up to the next price step, the price
    is the same within a step and the label covers the whole step."""
    estimate_g = goods_g + SENDCLOUD_PACKAGING_G
    steps = math.ceil(estimate_g / SENDCLOUD_WEIGHT_STEP_G)
    return estimate_g, max(steps, 1) * SENDCLOUD_WEIGHT_STEP_G


def parcel_weight(invoice_data: dict) -> tuple[float, int]:
    """label_weight of the invoice items. Items without a weight, like
    shipping costs, count as 0 g."""
    return label_weight(
        sum(
            (i.get("weightG") or 0) * (i.get("quantity") or 0)
            for i in invoice_data.get("items", [])
        )
    )


def needs_customs(country_code: str) -> bool:
    return alpha_2(country_code) not in EU_COUNTRIES


def invoice_date(value: str | None) -> datetime | None:
    """The v2 API uses "28-10-2026 19:26:16", taken as UTC"""
    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    if value:
        logging.error(f"Unknown Sendcloud invoice date {value!r}")
    return None


class SendcloudError(Exception):
    def __init__(self, msg: str, status_code: int | None = None, pointers: tuple = ()):
        super().__init__(msg)
        # Text that may be shown to the user (Sendcloud's error detail)
        self.user_message = msg
        self.status_code = status_code
        # Fields Sendcloud complained about, e.g. "house_number"
        self.pointers = pointers


# House number in front ("338 rue des Flamboyants", "12 bis rue X") or at
# the end ("Hauptstr. 12a", "Cotta B 18")
_NUMBER = r"\d+(?:\s?(?:bis|ter|quater)\b|\s?[a-z]\b)?(?:\s?[-/]\s?\d+[a-z]?)?"
_NUMBER_FIRST = re.compile(rf"^({_NUMBER})\s*,?\s+(\D.*)$", re.IGNORECASE)
_NUMBER_LAST = re.compile(rf"^(.*\D)\s+({_NUMBER})$", re.IGNORECASE)


def split_house_number(address: str) -> tuple[str, str] | None:
    """Street and house number of an address line, None if there's no
    number to split off"""
    address = address.strip()
    if m := _NUMBER_FIRST.match(address):
        return m.group(2).strip(), m.group(1)
    if m := _NUMBER_LAST.match(address):
        return m.group(1).strip(" ,"), m.group(2)
    return None


class Sendcloud:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=SENDCLOUD_URL,
            auth=(SENDCLOUD_PUBLIC_KEY, SENDCLOUD_PRIVATE_KEY),
            timeout=60,
        )

    async def _post(self, path: str, payload: dict | None = None) -> dict:
        return self._check(path, await self.client.post(path, json=payload))

    async def _get(self, path: str) -> dict:
        return self._check(path, await self.client.get(path))

    def _check(self, path: str, response: httpx.Response) -> dict:
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
                pointers = tuple(
                    (e.get("source") or {}).get("pointer") or "" for e in errors
                )
            except ValueError:
                msg = response.text
                pointers = ()
            raise SendcloudError(msg, response.status_code, pointers)
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

    def _customs(self, invoice_data: dict, gift: bool = False) -> tuple[dict, list]:
        """Customs lines from the invoice items, using the product data
        (hsCode, countryOfOrigin, weightG, see apply_product_data). Items
        without a product, like shipping costs, are not declared. Products
        without customs data stop the label, a declaration missing goods
        would not match the parcel. A gift is declared as a private export
        instead of a sale."""
        items = []
        for i in invoice_data.get("items", []):
            missing = [f for f in CUSTOMS_FIELDS if not i.get(f)]
            if missing and not i.get("productId"):
                continue
            if missing:
                raise SendcloudError(
                    f"'{i.get('description')}' has no "
                    f"{', '.join(CUSTOMS_FIELD_NAMES[f] for f in missing)}, "
                    "set it for the product in Invio"
                )
            # Sendcloud works with whole grams, anything below ends up as 0
            if i["weightG"] < 1:
                raise SendcloudError(
                    f"Weight of '{i.get('description')}' is {i['weightG']:g} g, "
                    "set the weight per piece in grams for the product in Invio "
                    "(a value below 1 was probably entered in kg)"
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
            "export_reason": "gift" if gift else "commercial_goods",
            "export_type": "private" if gift else "commercial_b2c",
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
        gift: bool = False,
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
            customs, items = self._customs(invoice_data, gift)
            payload["customs_information"] = customs
            parcel["parcel_items"] = items
        payload["parcels"] = [parcel]

        try:
            response = await self._post("/shipments/announce", payload)
        except SendcloudError as e:
            # Sendcloud splits the house number off the address line itself
            # for most countries, others (e.g. Réunion) need it separately
            split = split_house_number(receiver.address)
            if not any(p.endswith("house_number") for p in e.pointers) or not split:
                raise
            street, number = split
            logging.info(f"Retrying with street {street!r}, house number {number!r}")
            payload["to_address"]["address_line_1"] = street
            payload["to_address"]["house_number"] = number
            response = await self._post("/shipments/announce", payload)
        data = response.get("data", {})
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

    async def tracking(self, tracking_number: str) -> dict:
        """Tracking of a parcel: its events, newest first, and details like
        the expected delivery date"""
        data = await self._get(f"/parcels/tracking/{tracking_number}")
        return data.get("data", data)

    async def cancel(self, shipment_id: str) -> dict:
        """Returns {"status": "cancelled" | "queued", "message": ...}"""
        data = await self._post(f"/shipments/{shipment_id}/cancel")
        return data.get("data", {})

    async def invoices(self) -> dict:
        """Unpaid Sendcloud invoices and the date of the latest one. Shipping
        costs after that date are not invoiced yet."""
        data = await self._get(SENDCLOUD_INVOICES_URL)
        invoices = data.get("invoices", [])
        unpaid = [i for i in invoices if not i.get("isPayed")]
        dates = [d for i in invoices if (d := invoice_date(i.get("date")))]
        return {
            "unpaid": round(sum(float(i.get("price_incl") or 0) for i in unpaid), 2),
            "unpaid_count": len(unpaid),
            "last_invoice": max(dates, default=None),
        }

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
