import logging
import math
import re
import time
from collections import defaultdict, deque

import pycountry

from sendcloud import SENDCLOUD_DEFAULT_WEIGHT_G, Sendcloud, alpha_2

# Public order form (order.bouni.de): limit how many orders one client can submit
RATE_LIMIT = 5
RATE_WINDOW_S = 3600
_orders_per_ip: dict[str, deque] = defaultdict(deque)

# Countries without a Sendcloud/DHL product: fixed shipping price, the label
# (DHL Paket 2 kg) is bought manually
MANUAL_SHIPPING = {
    "US": {"name": "DHL Paket International", "price": 30},
}

# Shipping prices are fetched from Sendcloud, cache them per country
QUOTE_CACHE_S = 3600
_quotes: dict[str, tuple[float, dict]] = {}

MAX_QUANTITY = 99

# Countries where carriers (DHL) need a state/province. Stored in Invio as
# "region" (ISO 3166-2 code without the country prefix, e.g. CA, NSW, ON)
REGION_COUNTRIES = {"US", "CA", "AU", "ZA"}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9 ()/-]{4,30}$")


class OrderError(Exception):
    pass


def regions(country_code: str) -> list:
    """States/provinces of a country, empty if the country doesn't need one"""
    country = country_code.upper()
    if country not in REGION_COUNTRIES:
        return []
    subdivisions = pycountry.subdivisions.get(country_code=country) or []
    return sorted(
        (
            {"code": s.code.split("-", 1)[1], "name": s.name}
            for s in subdivisions
            if not s.parent_code and s.type != "Outlying area"
        ),
        key=lambda r: r["name"],
    )


def rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    timestamps = _orders_per_ip[client_ip]
    while timestamps and now - timestamps[0] > RATE_WINDOW_S:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT:
        return True
    timestamps.append(now)
    return False


async def shipping_quote(country_code: str) -> dict:
    """Shipping price for the label weight, rounded up to the next full euro"""
    country = alpha_2(country_code)
    if manual := MANUAL_SHIPPING.get(country):
        return {**manual, "price_rounded": manual["price"], "manual": True}
    cached = _quotes.get(country)
    if cached and time.monotonic() - cached[0] < QUOTE_CACHE_S:
        return cached[1]
    async with Sendcloud() as sc:
        quote = await sc.quote(country, SENDCLOUD_DEFAULT_WEIGHT_G)
    quote["price_rounded"] = math.ceil(quote["price"])
    _quotes[country] = (time.monotonic(), quote)
    logging.info(f"Shipping quote {country}: {quote}")
    return quote


def validate(data: dict, products: list) -> tuple[dict, list]:
    """Check the submitted order, return the customer data and the ordered
    goods with name and price taken from Invio (never from the client)"""
    fields = {
        "firstname": "First name",
        "lastname": "Last name",
        "email": "Email address",
        "address": "Street and house number",
        "postalcode": "Postal code",
        "city": "City",
        "country": "Country",
    }
    values = {}
    for key, label in fields.items():
        value = str(data.get(key) or "").strip()
        if not value:
            raise OrderError(f"{label} is required")
        if len(value) > 200:
            raise OrderError(f"{label} is too long")
        values[key] = value
    if not EMAIL_RE.match(values["email"]):
        raise OrderError("Email address is invalid")
    if not pycountry.countries.get(alpha_2=values["country"].upper()):
        raise OrderError("Country is invalid")
    values["country"] = values["country"].upper()

    # State/province, only for countries that need it
    region_codes = {r["code"] for r in regions(values["country"])}
    values["region"] = str(data.get("region") or "").strip().upper()
    if region_codes:
        if not values["region"]:
            raise OrderError("State / Province is required")
        if values["region"] not in region_codes:
            raise OrderError("State / Province is invalid")
    else:
        values["region"] = ""

    # Optional fields
    values["contact"] = str(data.get("contact") or "").strip()
    if len(values["contact"]) > 200:
        raise OrderError("Contact person is too long")
    values["phone"] = str(data.get("phone") or "").strip()
    if values["phone"] and not PHONE_RE.match(values["phone"]):
        raise OrderError("Phone number is invalid")

    goods = {p["id"]: p for p in products if p.get("category") == "goods"}
    items = []
    for item in data.get("items") or []:
        product = goods.get(item.get("productId"))
        try:
            quantity = int(item.get("quantity") or 0)
        except (TypeError, ValueError):
            raise OrderError("Invalid quantity") from None
        if product is None or not 0 <= quantity <= MAX_QUANTITY:
            raise OrderError("Invalid item")
        if quantity:
            items.append(
                {
                    "productId": product["id"],
                    "description": product["name"],
                    "quantity": quantity,
                    "unitPrice": product["unitPrice"],
                }
            )
    if not items:
        raise OrderError("Please select at least one item")
    return values, items


def shipping_item(products: list, country: str, price: float) -> dict:
    """Invoice line for the shipping costs, using the matching Invio shipping
    product ("Versand national" / "Versand international") if there is one"""
    international = alpha_2(country) != "DE"
    for p in products:
        if p.get("category") != "shipping":
            continue
        if ("international" in p["name"].lower()) == international:
            return {
                "productId": p["id"],
                "description": p["name"],
                "quantity": 1,
                "unitPrice": price,
            }
    name = "Versand international" if international else "Versand national"
    return {"description": name, "quantity": 1, "unitPrice": price}


def find_customer(customers: list, customer: dict) -> dict | None:
    """Reuse an existing customer only if all address data is identical,
    so old invoices keep showing the address they were issued for"""

    def norm(value) -> str:
        return str(value or "").strip().lower()

    for c in customers:
        if all(
            norm(c.get(k)) == norm(customer.get(k))
            for k in (
                "name",
                "contactName",
                "email",
                "phone",
                "address",
                "postalCode",
                "city",
                "region",
                "countryCode",
            )
        ):
            return c
    return None
