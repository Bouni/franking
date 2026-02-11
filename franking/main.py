import logging
import os
import sqlite3
from pathlib import Path

import pycountry
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from franking.internetmarke import Internetmarke
from franking.models import Address
from franking.printer import BrotherQL

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

print(f"DEBUG = {DEBUG}")

DB_PATH = os.getenv("DB_PATH", default="/opt/docker/invio/data/invio.db")
LABEL_PATH = os.getenv("LABEL_PATH", default="/opt/docker/invio/labels")

BASE_PATH = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


def get_db():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
):
    im = Internetmarke()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            ii.invoice_id,
            ii.description,
            ii.quantity,
            ii.unit_price,
            c.name,
            c.contact_name,
            c.address,
            c.postal_code,
            c.city,
            c.country_code
        FROM invoice_items ii
        INNER JOIN invoices i ON ii.invoice_id = i.id
        INNER JOIN customers c ON i.customer_id = c.id
        WHERE ii.description LIKE '%Versand%'
        ORDER BY i.created_at DESC
    """)
    orders = cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"orders": orders, "balance": im.get_balance()},
    )


@app.post("/print/{invoice_id}")
def print_label(invoice_id: str, db: sqlite3.Connection = Depends(get_db)):
    # fetch invoice data from db
    cursor = db.cursor()
    cursor.execute(f"""
        SELECT 
            ii.invoice_id,
            ii.description,
            ii.quantity,
            ii.unit_price,
            c.name,
            c.contact_name,
            c.address,
            c.postal_code,
            c.city,
            c.country_code
        FROM invoice_items ii
        INNER JOIN invoices i ON ii.invoice_id = i.id
        INNER JOIN customers c ON i.customer_id = c.id
        WHERE ii.description LIKE '%Versand%' AND
        i.id = '{invoice_id}'
    """)
    invoice = cursor.fetchone()

    if invoice:
        invoice = dict(invoice)

        # try converting 2-letter country code into 3-letter country code
        if code := pycountry.countries.get(alpha_2=invoice["country_code"].upper()):
            invoice["country_code"] = code.alpha_3
        else:
            return Response(status_code=status.HTTP_400_BAD_REQUEST)

        # create address from data
        address = Address(
            name=invoice["name"],
            address=invoice["address"],
            city=invoice["city"],
            postcode=invoice["postal_code"],
            country=invoice["country_code"],
        )

        # Figure out the right product code
        product_code = 21 if invoice["country_code"] == "DEU" else 10051

        if not Path(LABEL_PATH).is_dir():
            logging.error(f"Label path {LABEL_PATH} is not a directory")
            return

        if (Path(LABEL_PATH) / f"{invoice['invoice_id']}.png").is_file():
            logging.info(
                f"Internetmarke for order '{invoice['invoice_id']}' already exists, continue with printing"
            )
        else:
            # get Internetmarke
            im = Internetmarke()
            if DEBUG:
                logging.info("DEBUG active, Internetmarke dryrun")
            # im.order(Path(LABEL_PATH), invoice["invoice_id"], address, product_code, dryrun=DEBUG)

        # ToDo: catch errors when fetching Internetmarke (balance to low, etc.)

        # Print label
        ql = BrotherQL()
        if DEBUG:
            logging.info("DEBUG active, printing label is skipped")
            # ql.print_label(BASE_PATH / "labels" / "label.png")
        else:
            if not (Path(LABEL_PATH) / f"{invoice['invoice_id']}.png").is_file():
                logging.error("No label file found!")
            else :
                ql.print_label(Path(LABEL_PATH) / f"{invoice['invoice_id']}.png")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
