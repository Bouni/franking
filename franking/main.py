import logging
import os
import sqlite3
from pathlib import Path

import pycountry
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request, Response, status
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
    orders = [dict(order) for order in cursor.fetchall()]
    for order in orders:
        order["purchased"] = im.is_purchased(order["invoice_id"])
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"orders": orders, "balance": im.get_balance()},
    )


@app.post("/purchase/{invoice_id}")
def purchase_internetmarke(
    request: Request,
    invoice_id: str,
    product_code: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
):
    # fetch invoice data from db
    im = Internetmarke()
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
            return Response(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Invalid country code {invoice['country_code']}"},
            )

        # create address from data
        address = Address(
            name=invoice["name"],
            address=invoice["address"],
            city=invoice["city"],
            postcode=invoice["postal_code"],
            country=invoice["country_code"],
        )

        if not Path(LABEL_PATH).is_dir():
            logging.error(f"Label path {LABEL_PATH} is not a directory")
            return Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Label path ({LABEL_PATH}) does not exist! "},
            )

        im = Internetmarke()
        if DEBUG:
            logging.info("DEBUG active, Internetmarke dryrun")
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"detail": "Debug mode active, no Internetmarke purchased"},
            )
        im.order(
            Path(LABEL_PATH), invoice["invoice_id"], address, product_code, dryrun=DEBUG
        )

    invoice["purchased"] = im.is_purchased(invoice["invoice_id"])

    return templates.TemplateResponse(
        "partials/buttons.html", {"request": request, "order": invoice}
    )


@app.post("/print/{invoice_id}")
def print_label(invoice_id: str):
    ql = BrotherQL()
    lp = Path(LABEL_PATH) / f"{invoice_id}.png"
    if not lp.is_file():
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Label file ({lp}) does not exist! "},
        )
    if DEBUG:
        logging.info("DEBUG active, printing label is skipped")
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            content={"detail": "Debug mode active, no label printed"},
        )
    else:
        result = ql.print_label(lp)
        if result:
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"detail": "Label printed"},
            )
        else:
            return Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Label print failed"},
            )
