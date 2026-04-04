import json
import logging
import os
import sqlite3
import textwrap
from pathlib import Path

import pycountry
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from franking.internetmarke import Internetmarke
from franking.invio import Invio
from franking.mail import Mail
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
            i.invoice_number,
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
        WHERE ii.description LIKE '%Versand%' AND (i.status = 'sent' OR i.status = 'paid')
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


@app.post("/internetmarke/balance")
def internetmarke_balance(request: Request):
    im = Internetmarke()
    return templates.TemplateResponse(
        "partials/balance.html", {"request": request, "balance": im.get_balance()}
    )


@app.get("/material/reserved")
def reserved_material(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            ii.description AS Article,
            SUM(ii.quantity) || ' pcs' AS Total
        FROM invoice_items ii
        INNER JOIN invoices i ON ii.invoice_id = i.id
        WHERE i.status = 'sent' AND ii.description NOT LIKE '%Versand%'
        GROUP BY ii.description
        ORDER BY SUM(ii.quantity) DESC;
    """)
    material = [dict(mat) for mat in cursor.fetchall()]
    return templates.TemplateResponse(
        "partials/material.html", {"request": request, "material": material}
    )


@app.post("/purchase/{invoice_id}")
def purchase_internetmarke(
    request: Request,
    invoice_id: str,
    response: Response,
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
            payload = json.dumps(
                {
                    "showToast": {
                        "message": f"Invalid country code {invoice['country_code']}",
                        "type": "debug",
                    }
                }
            )
            response.headers["HX-Trigger"] = payload
            response.status_code = status.HTTP_400_BAD_REQUEST
            return response

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
            payload = json.dumps(
                {
                    "showToast": {
                        "message": f"Label path ({LABEL_PATH}) does not exist! ",
                        "type": "debug",
                    }
                }
            )
            response.headers["HX-Trigger"] = payload
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return response

        im = Internetmarke()
        if DEBUG:
            logging.info("DEBUG active, Internetmarke dryrun")
            payload = json.dumps(
                {
                    "showToast": {
                        "message": "Debug mode active, no Internetmarke purchased",
                        "type": "debug",
                    }
                }
            )
            response.headers["HX-Trigger"] = payload
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
        im.order(
            Path(LABEL_PATH), invoice["invoice_id"], address, product_code, dryrun=DEBUG
        )

    invoice["purchased"] = im.is_purchased(invoice["invoice_id"])

    return templates.TemplateResponse(
        "partials/buttons.html", {"request": request, "order": invoice}
    )


@app.post("/print/{invoice_id}")
def print_label(invoice_id: str, response: Response):
    ql = BrotherQL()
    lp = Path(LABEL_PATH) / f"{invoice_id}.png"
    if not lp.is_file():
        payload = json.dumps(
            {
                "showToast": {
                    "message": f"Label file ({lp}) does not exist!",
                    "type": "failure",
                }
            }
        )
        response.headers["HX-Trigger"] = payload
        response.status_code = status.HTTP_404_NOT_FOUND
        return response
    if DEBUG:
        logging.info("DEBUG active, printing label is skipped")
        payload = json.dumps(
            {
                "showToast": {
                    "message": "Debug mode active, no label printed",
                    "type": "debug",
                }
            }
        )
        response.headers["HX-Trigger"] = payload
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    else:
        result = ql.print_label(lp)
        if result:
            payload = json.dumps(
                {
                    "showToast": {
                        "message": "Label sucessfully printed!",
                        "type": "success",
                    }
                }
            )
            response.headers["HX-Trigger"] = payload
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
        else:
            payload = json.dumps(
                {
                    "showToast": {
                        "message": "Label print failed!",
                        "type": "failure",
                    }
                }
            )
            response.headers["HX-Trigger"] = payload
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return response


@app.post("/send/{invoice_id}")
def send_invoice_email(invoice_id: str, response: Response):
    invio = Invio()
    invoice_data = invio.get_invoice_data(invoice_id)
    subject = f"Invoice {invoice_data.get('invoiceNumber')} (BSH-Board)"
    body = textwrap.dedent(f"""
        Hi {invoice_data.get("customer", {}).get("name")},

        Im Anhang findest du die Rechnung für deine Bestellung.
        Diese beinhaltet Zahlungsinformationen für Banküberweisungen und PayPal.

        Sobald ich die Zahlung erhalten habe versende ich in aller Regel am nächsten Werktag.

        Wichtiger Hinweis: Ich bin bis zum 5. April im Urlaub, der Versand startet erst nach diesem Datum!

        Vielen Dank für die Bestellung!

        -------------------------------------------------------------------------------------

        Attached you find the invoice for your order.
        It contains payment info for bank transfer as well as for PayPal.

        As soon as I recieved the payment, I'll pack your oder and send it usually by the next work day.
        
        Important note: I'm on vaccation until April 5th, shipping will start after that date!

        Thank you very much for your Order!

        -------------------------------------------------------------------------------------


        Bouni

        P.S. Sorry to those of you who are non german speakers for the german invoice, my invoicing software does not yet allow localized invoices 😅
        """).strip()
    m = Mail(subject, body)
    m.send_invoice(invoice_id)
    payload = json.dumps(
        {"showToast": {"message": "Invoice successfully sent!", "type": "success"}}
    )
    response.headers["HX-Trigger"] = payload
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
