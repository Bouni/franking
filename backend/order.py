import logging
import math
import re
import time
from collections import defaultdict, deque

import pycountry

from sendcloud import Sendcloud, alpha_2, label_weight

# Public order form (order.bouni.de): limit how many orders one client can submit
RATE_LIMIT = 5
RATE_WINDOW_S = 3600
_orders_per_ip: dict[str, deque] = defaultdict(deque)

# Countries without a Sendcloud/DHL product: fixed shipping price, the label
# (DHL Paket 2 kg) is bought manually
MANUAL_SHIPPING = {
    "US": {"name": "DHL Paket International", "price": 30},
}

# Shipping prices are fetched from Sendcloud, cache them per country and
# label weight
QUOTE_CACHE_S = 3600
_quotes: dict[tuple[str, int], tuple[float, dict]] = {}

MAX_QUANTITY = 99
# Sanity limit for the weight sent by the order form, Warenpost ends at 1 kg
MAX_GOODS_G = 100_000

# Countries where carriers (DHL) need a state/province. Stored in Invio as
# "region" (ISO 3166-2 code without the country prefix, e.g. CA, NSW, ON)
REGION_COUNTRIES = {"US", "CA", "AU", "ZA"}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9 ()/-]{4,30}$")


class OrderError(Exception):
    """Validation error, its message is meant to be shown to the user"""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.user_message = msg


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


def valid_country(country_code: str) -> bool:
    return (
        len(country_code) == 2
        and pycountry.countries.get(alpha_2=country_code.upper()) is not None
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


def goods_weight(items: list, products: list) -> float:
    """Weight of the ordered goods in grams, from the product data in Invio"""
    weights = {p["id"]: p.get("weightG") or 0 for p in products}
    return sum(weights.get(i["productId"], 0) * i["quantity"] for i in items)


async def shipping_quote(country_code: str, goods_g: float) -> dict:
    """Shipping price for the label weight of the goods (see label_weight),
    rounded up to the next full euro"""
    country = alpha_2(country_code)
    if manual := MANUAL_SHIPPING.get(country):
        return {**manual, "price_rounded": manual["price"], "manual": True}
    _, weight_g = label_weight(goods_g)
    cached = _quotes.get((country, weight_g))
    if cached and time.monotonic() - cached[0] < QUOTE_CACHE_S:
        return cached[1]
    async with Sendcloud() as sc:
        quote = await sc.quote(country, weight_g)
    quote["price_rounded"] = math.ceil(quote["price"])
    _quotes[(country, weight_g)] = (time.monotonic(), quote)
    logging.info(f"Shipping quote {country} {weight_g}g: {quote}")
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


def shipping_item(products: list, country: str, quote: dict) -> dict:
    """Invoice line for the shipping costs, using the matching Invio shipping
    product ("Versand national" / "Versand international") if there is one.
    The shipping method from the order form is added in brackets, e.g.
    "Versand national (DHL Kleinpaket)"."""
    international = alpha_2(country) != "DE"
    item = {
        "description": "Versand international" if international else "Versand national",
        "quantity": 1,
        "unitPrice": quote["price_rounded"],
    }
    for p in products:
        if p.get("category") != "shipping":
            continue
        if ("international" in p["name"].lower()) == international:
            item["productId"] = p["id"]
            item["description"] = p["name"]
            break
    if quote.get("name"):
        item["description"] += f" ({quote['name']})"
    return item


def find_customer(customers: list, customer: dict) -> dict | None:
    """Reuse an existing customer if name and address match (ignoring case),
    so old invoices keep showing the address they were issued for. Email,
    phone and contact person don't matter for recognising a customer."""

    def norm(value) -> str:
        return str(value or "").strip().lower()

    for c in customers:
        keys = ["name", "address", "postalCode", "city", "countryCode"]
        # Only compare the state/province once Invio knows the field
        if "region" in c:
            keys.append("region")
        if all(norm(c.get(k)) == norm(customer.get(k)) for k in keys):
            return c
    return None
