import sqlite3
from pathlib import Path

import pycountry
from fastapi import Depends, FastAPI, HTTPException

from franking.api import Internetmarke
from franking.models import Address, ItemList
from franking.printer import BrotherQL

BASE_PATH = Path(__file__).resolve().parent.parent


app = FastAPI()


def get_db():
    conn = sqlite3.connect(
        "file:/opt/docker/invio/data/invio.db?mode=ro&immutable=1", uri=True
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/profile")
def user_profile():
    im = Internetmarke()
    return {"profile": im.user_profile()}


@app.get("/check-health")
def check_health():
    im = Internetmarke()
    return {"health": im.check_health()}


@app.get("/balance")
def balance():
    im = Internetmarke()
    return {"balance": im.get_balance()}


@app.get("/formats")
def formats():
    im = Internetmarke()
    return {"formats": im.get_formats()}


@app.get("/products")
def products():
    im = Internetmarke()
    return {"products": im.get_products()}


@app.post("/internetmarke")
def internetmarke(address: Address, itemList: ItemList):
    try:
        address.country = pycountry.countries.get(
            alpha_2=address.country.upper()
        ).alpha_3
    except:
        raise HTTPException(status_code=400, detail="Invalid country code")
    im = Internetmarke()
    return {"result": im.order(address, 21)}


@app.get("/print")
def print_label(fn: str):
    ql = BrotherQL()
    ql.print_label(BASE_PATH / "labels/0.png")
    return {"result": "success"}


@app.get("/order")
def get_invio_order_data(id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        f"SELECT description,quantity,unit_price FROM invoice_items WHERE invoice_id = '{id}' AND description LIKE '%Versand%'"
    )
    shipping = cursor.fetchone()
    cursor.execute(
        f"SELECT name,address,postal_code,city,country_code FROM invoices INNER JOIN customers ON invoices.customer_id = customers.id WHERE invoices.id = '{id}'"
    )
    address = cursor.fetchone()
    return {"shipping": {**dict(shipping)}, "address": {**dict(address)}}
